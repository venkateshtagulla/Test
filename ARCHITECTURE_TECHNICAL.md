# ARKA Backend - Technical Architecture

**Target Audience**: Senior full-stack developer joining the project  
**Purpose**: Implementation-depth reference for serverless maritime inspection platform backend

---

## Table of Contents

1. [Runtime & Request Lifecycle](#1-runtime--request-lifecycle)
2. [Lambda Handler Design](#2-lambda-handler-design)
3. [Service Layer Contract](#3-service-layer-contract)
4. [Repository Layer & DynamoDB Strategy](#4-repository-layer--dynamodb-strategy)
5. [Authentication & Authorization Internals](#5-authentication--authorization-internals)
6. [S3 Document Handling](#6-s3-document-handling)
7. [Environment & Deployment Model](#7-environment--deployment-model)
8. [Extension & Modification Rules](#8-extension--modification-rules)
9. [Anti-Patterns & Failure Scenarios](#9-anti-patterns--failure-scenarios)

---

## 1. Runtime & Request Lifecycle

### 1.1 Execution Flow

```
React (localhost:3000)
    ↓ HTTP Request
API Gateway
    ↓ Lambda Proxy Integration Event
Lambda Handler (e.g., auth.py::register_handler)
    ↓ Parse & Validate
Service Layer (e.g., InspectorService)
    ↓ Business Logic
Repository Layer (e.g., InspectorRepository)
    ↓ boto3 SDK
DynamoDB / S3
    ↓ Response
Repository → Service → Handler
    ↓ JSON Response
API Gateway
    ↓ HTTP Response
React
```

### 1.2 Lambda Proxy Event Structure

Each handler receives an `event` dictionary from API Gateway containing:

- `body`: JSON string (may be base64-encoded if `isBase64Encoded: true`)
- `headers`: Dict of HTTP headers (case-insensitive keys: `Authorization` or `authorization`)
- `pathParameters`: Dict of path variables (e.g., `{inspector_id: "abc123"}`)
- `queryStringParameters`: Dict of query params (e.g., `{page: "1", limit: "20"}`)
- `httpMethod`: HTTP verb (`GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`)
- `requestContext`: Metadata about the request (not used for auth; JWT is extracted from headers)

### 1.3 Cold Start Implications

**What happens on cold start:**
- Lambda container initializes
- Python interpreter loads
- Module-level code executes (imports, global variable initialization)
- First request incurs 500ms-2s latency

**Module-level initialization (executed once per container):**
```python
# From routers/auth.py
repository = InspectorRepository()  # DynamoDB table resource created
service = InspectorService(repository=repository)
```

**Critical constraints:**
- No persistent state survives between invocations (even in warm containers, assume stateless)
- DynamoDB/S3 clients are reused across invocations in the same container (boto3 handles connection pooling)
- Environment variables are read once at module load via `get_settings()` (cached with `@lru_cache`)

### 1.4 Error Propagation & HTTP Status Mapping

**Error flow:**
1. Repository/Service raises `ApiError(message, status_code, error_code)`
2. Handler catches all exceptions in `try/except` block
3. `handle_error(exc)` converts exception to API Gateway response:
   - `ApiError` → `{statusCode: error.status_code, body: {...}}`
   - Other exceptions → `{statusCode: 500, body: {error: "internal_error"}}`
4. CORS headers added automatically by `handle_error()`

**Status code semantics:**
- `200`: Success (GET, list operations)
- `201`: Resource created (POST)
- `400`: Client error (validation failure, malformed JSON)
- `401`: Authentication failure (invalid/expired token)
- `404`: Resource not found
- `409`: Conflict (duplicate email, conditional check failed)
- `500`: Server error (DynamoDB failure, S3 failure, unexpected exception)

**Never return raw exceptions to client.** All errors must flow through `ApiError` or be caught by `handle_error()`.

---

## 2. Lambda Handler Design

### 2.1 Handler Entry Point Pattern

**Standard handler signature:**
```python
@cors_middleware()
def handler_name(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Brief description of endpoint.
    """
    try:
        # 1. Extract input
        # 2. Validate via Pydantic model
        # 3. Delegate to service
        # 4. Format response
        # 5. Return {statusCode, body}
    except Exception as exc:
        return handle_error(exc)
```

**Responsibilities of a handler (ONLY):**
1. Parse request body/params using `parse_json_body(event)` or `event.get("pathParameters")`
2. Validate input using Pydantic request models (e.g., `InspectorRegisterRequest(**body)`)
3. Extract authentication context (if protected endpoint) via `_get_admin_id_from_event(event)`
4. Call service method with validated payload
5. Format success response using `format_response(success=True, data=..., message=...)`
6. Return `{statusCode: int, body: json.dumps(response)}`

### 2.2 Input Validation Strategy

**Body parsing:**
```python
# From utility/body_parser.py
body = parse_json_body(event)  # Handles base64 decoding, JSON parsing, raises ApiError on failure
```

**Pydantic validation:**
```python
# From routers/auth.py
payload = InspectorRegisterRequest(**body)  # Raises ValidationError if schema mismatch
```

Pydantic `ValidationError` is NOT caught explicitly; it propagates to `handle_error()` which converts it to a 500 error. **This is acceptable** because malformed requests should fail loudly in development. In production, API Gateway should enforce request schemas.

### 2.3 Auth Context Extraction

**Protected endpoints extract user ID from JWT:**
```python
def _get_admin_id_from_event(event: Dict[str, Any]) -> str:
    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")
    
    token = auth_header.removeprefix("Bearer ").strip()
    return get_subject_from_access_token(token)  # Decodes JWT, validates signature/expiry
```

**This function is duplicated across handler files** (e.g., `vessel.py`, `inspection_assignment.py`). This is intentional to avoid shared state between Lambda functions (each handler is deployed as a separate Lambda).

### 2.4 What Logic is FORBIDDEN in Handlers

**Handlers must NOT:**
- Perform business logic (password hashing, validation beyond schema checks, data transformations)
- Directly call DynamoDB/S3 (always delegate to repository via service)
- Maintain state between invocations
- Perform cross-entity coordination (e.g., checking if vessel exists before creating assignment)
- Implement retry logic (DynamoDB SDK handles retries; application-level retries belong in services)

**Example of WRONG handler code:**
```python
# WRONG: Business logic in handler
def register_handler(event, context):
    body = parse_json_body(event)
    if body["password"] != body["confirm_password"]:  # WRONG: belongs in service
        return {"statusCode": 400, "body": "..."}
    hashed = hash_password(body["password"])  # WRONG: belongs in service
    table.put_item(Item={...})  # WRONG: belongs in repository
```

---

## 3. Service Layer Contract

### 3.1 Service Ownership

**Each service owns:**
- Business logic for a single domain entity (Inspector, Vessel, InspectionAssignment, etc.)
- Orchestration of repository calls (may call multiple repositories)
- Domain-specific validation (e.g., password matching, duplicate email checks)
- Data transformation (DB model → response model)

**Services do NOT:**
- Parse HTTP requests (handler responsibility)
- Format HTTP responses (handler responsibility, though services return dicts that handlers serialize)
- Directly instantiate boto3 clients (repository responsibility)

### 3.2 Cross-Entity Coordination

**Example: Creating an inspection assignment requires validating inspector, form, and vessel exist.**

```python
# From services/inspection_assignment_service.py
def bulk_create_assignments(self, admin_id: str, payload: BulkCreateInspectionAssignmentRequest) -> Dict:
    # Verify inspector exists
    inspector = self._inspector_repo.get_item(payload.assignee_id)
    if not inspector:
        raise ApiError("Inspector not found", 404, "inspector_not_found")
    
    # Verify all forms exist
    for form_id in payload.form_ids:
        form = self._form_repo.get_item(form_id)
        if not form:
            raise ApiError(f"Inspection form not found: {form_id}", 404, "form_not_found")
    
    # Create assignments
    assignments = [...]
    self._repository.batch_put_items(assignments)
```

**Services initialize related repositories as instance variables:**
```python
def __init__(self, repository: InspectionAssignmentRepository) -> None:
    self._repository = repository
    self._vessel_repo = VesselRepository()
    self._inspector_repo = InspectorRepository()
    self._form_repo = InspectionFormRepository()
```

### 3.3 Idempotency Handling

**DynamoDB conditional writes provide idempotency:**
```python
# From repository/inspector_repository.py
self._table.put_item(
    Item=item,
    ConditionExpression="attribute_not_exists(inspector_id)"  # Fails if item exists
)
```

If a client retries a registration request with the same `inspector_id` (UUID generated client-side or in service), the second request will fail with `ConditionalCheckFailedException` → `ApiError(409, "inspector_exists")`.

**UUIDs are generated in DB models, not handlers:**
```python
# From models/db/inspector.py
class InspectorDBModel(BaseModel):
    inspector_id: str = Field(default_factory=lambda: str(uuid4()))
```

This means retries will generate new UUIDs → no idempotency. **To achieve idempotency, clients must provide idempotency keys** (not currently implemented).

### 3.4 Transaction-Like Behavior Without ACID

**DynamoDB does not support multi-table transactions in this codebase.** Services use **compensating actions** for rollback:

**Example: If batch assignment creation partially fails:**
```python
# From repository/inspection_assignment_repository.py
def batch_put_items(self, items: List[Dict[str, Any]]) -> None:
    # DynamoDB batch_write_item handles up to 25 items at a time
    for i in range(0, len(items), 25):
        batch = items[i : i + 25]
        response = self._table.meta.client.batch_write_item(RequestItems=...)
        
        unprocessed = response.get("UnprocessedItems", {})
        if unprocessed:
            # Retry once
            retry_response = self._table.meta.client.batch_write_item(RequestItems=unprocessed)
            if retry_response.get("UnprocessedItems"):
                raise ApiError("Failed to create some assignments", 500, "batch_write_failed")
```

**If batch write fails midway, partial data is committed.** There is no rollback. Clients must handle partial failures by querying created assignments and retrying.

### 3.5 Business Rules Enforcement

**Example: Crew members can only have one active assignment at a time.**

```python
# From services/inspection_assignment_service.py
def create_crew_assignment(self, admin_id: str, payload: CreateCrewInspectionAssignmentRequest) -> Dict:
    has_pending = self._repository.has_pending_assignments(payload.crew_id)
    if has_pending:
        raise ApiError(
            "Crew member already has pending or incomplete assignments.",
            409,
            "crew_has_pending_assignments"
        )
```

**This is enforced at service level, not database level.** Race conditions are possible (two concurrent requests could both pass the check). To prevent this, use DynamoDB conditional writes with a status attribute.

### 3.6 Error Semantics

**Domain errors (expected failures):**
- `ApiError("Email already registered", 409, "email_exists")`
- `ApiError("Invalid credentials", 401, "invalid_credentials")`
- `ApiError("Vessel not found", 404, "vessel_not_found")`

**Infrastructure errors (unexpected failures):**
- `ApiError("Could not create inspector", 500, "dynamodb_error")`
- `ApiError("Could not generate upload URL", 500, "presign_failed")`

Services catch `ClientError` from boto3 and convert to `ApiError`. Generic exceptions are caught by handlers and converted to 500 errors.

---

## 4. Repository Layer & DynamoDB Strategy

### 4.1 Table Ownership Philosophy

**One repository per DynamoDB table:**
- `InspectorRepository` → `DYNAMODB_TABLE_INSPECTORS`
- `VesselRepository` → `DYNAMODB_TABLE_VESSELS`
- `InspectionAssignmentRepository` → `DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS`
- `InspectionFormRepository` → `DYNAMODB_TABLE_INSPECTION_FORMS`
- `CrewRepository` → `DYNAMODB_TABLE_CREW`
- `AdminRepository` → `DYNAMODB_TABLE_ADMINS`
- `DefectRepository` → `DYNAMODB_TABLE_DEFECTS`

**Repositories do NOT:**
- Call other repositories (services orchestrate cross-table operations)
- Perform business logic (e.g., password hashing)
- Format response models (return raw DynamoDB items as dicts)

### 4.2 PK/SK Access Patterns

**Primary Key (PK) structure:**
- Inspectors: `PK = inspector_id` (UUID)
- Vessels: `PK = vessel_id` (UUID)
- Assignments: `PK = assignment_id` (UUID)

**No Sort Key (SK) is used.** All tables use single-attribute primary keys.

**Global Secondary Indexes (GSI):**
- Inspectors: `email_index` (PK: `email`)
- Vessels: `admin_id_index` (PK: `admin_id`)
- Assignments: `admin_id_index` (PK: `created_by_admin_id`), `form_id_index` (PK: `form_id`), `assignee_id_index` (PK: `assignee_id`)

**Access patterns:**
```python
# Get by primary key
item = repository.get_item(inspector_id)

# Query by GSI
items, last_key = repository.list_by_admin(admin_id, limit=20)

# Query by email (GSI)
item = repository.get_by_email(email)
```

### 4.3 Query vs Scan Rules

**ALWAYS use Query when possible:**
- Query requires a partition key (PK or GSI PK)
- Query is efficient (reads only matching items)

**Scan is used ONLY for:**
- Dashboard aggregations (e.g., counting all vessels)
- Admin listing all inspectors (no filter)

```python
# From repository/vessel_repository.py
def list_items(self, limit: int = 1000, cursor: Optional[Dict] = None) -> Tuple[List[Dict], Optional[Dict]]:
    """List all vessels using scan (for dashboard aggregation)."""
    response = self._table.scan(Limit=limit, ExclusiveStartKey=cursor)
    return response.get("Items", []), response.get("LastEvaluatedKey")
```

**Scans are expensive.** Avoid in user-facing endpoints. Use GSIs instead.

### 4.4 Pagination Handling

**DynamoDB pagination uses `ExclusiveStartKey` (cursor-based):**
```python
response = table.query(Limit=20, ExclusiveStartKey=cursor)
items = response["Items"]
next_cursor = response.get("LastEvaluatedKey")  # None if no more results
```

**Application-level page-based pagination (used in services):**
```python
# From services/vessel_service.py
def list_vessels(self, admin_id: str, payload: ListVesselsRequest) -> Dict:
    fetch_limit = payload.limit + 1  # Fetch one extra to detect has_next
    cursor_dict = None
    
    # Walk through previous pages to reach target page
    for _ in range(1, payload.page):
        _, last_key = self._repository.list_by_admin(admin_id, limit=payload.limit, cursor=cursor_dict)
        if not last_key:
            return PaginatedVesselsResponse(items=[], page=payload.page, has_next=False)
        cursor_dict = last_key
    
    # Fetch current page
    items, _ = self._repository.list_by_admin(admin_id, limit=fetch_limit, cursor=cursor_dict)
    has_next = len(items) > payload.limit
    items = items[:payload.limit] if has_next else items
```

**This is inefficient for large page numbers** (e.g., page 100 requires 100 queries). Consider cursor-based pagination for production.

### 4.5 Consistency Expectations

**DynamoDB uses eventual consistency by default.**
- Writes are immediately consistent within the same partition key
- GSI queries are eventually consistent (may not reflect recent writes for ~1 second)

**Example race condition:**
1. User registers (writes to `INSPECTORS` table)
2. User immediately logs in (queries `email_index` GSI)
3. GSI may not yet reflect the new item → login fails

**Mitigation:** Use `ConsistentRead=True` for critical reads (not implemented in this codebase).

### 4.6 Why Joins Are Forbidden

**DynamoDB is a NoSQL database with no JOIN support.** Related data is fetched via multiple queries:

```python
# From services/inspection_assignment_service.py
def _item_to_response(self, item: Dict) -> InspectionAssignmentResponse:
    related_vessel = self._build_related_vessel(item.get("vessel_id"))  # Separate query
    related_assignee = self._build_related_assignee(item.get("assignee_id"), item.get("assignee_type"))  # Separate query
    related_form = self._build_related_form(item.get("form_id"))  # Separate query
    
    return InspectionAssignmentResponse(
        assignment_id=item["assignment_id"],
        vessel=related_vessel,
        assignee=related_assignee,
        forms=[related_form]
    )
```

**This results in N+1 queries** (1 query for assignments, N queries for related entities). For list endpoints, this is expensive. **Mitigation:** Denormalize data (store vessel name in assignment record) or use batch get operations.

### 4.7 Relation Modeling

**Foreign keys are stored as UUIDs:**
- `vessel_id` in `InspectionAssignment` references `Vessel.vessel_id`
- `assignee_id` in `InspectionAssignment` references `Inspector.inspector_id` or `Crew.crew_id`

**No referential integrity is enforced.** Deleting a vessel does not cascade delete assignments. Services must handle orphaned references:

```python
related_vessel = self._build_related_vessel(item.get("vessel_id"))
if not related_vessel:
    # Vessel was deleted; assignment still exists
    related_vessel = None  # Return null in response
```

---

## 5. Authentication & Authorization Internals

### 5.1 JWT Structure & Claims

**Token generation:**
```python
# From config/jwt_config.py
payload = {
    "sub": subject,  # User ID (inspector_id, admin_id, crew_id)
    "type": token_type,  # "access" or "refresh"
    "iat": datetime.now(tz=timezone.utc),  # Issued at
    "exp": datetime.now(tz=timezone.utc) + expires_delta,  # Expiration
    "email": email,  # Optional
    "role": role  # Optional (e.g., "inspector", "admin", "crew")
}
token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
```

**Token types:**
- **Access token**: Short-lived (15 minutes), used for API requests
- **Refresh token**: Long-lived (30 days), used to obtain new access tokens (refresh endpoint not implemented)

### 5.2 Token Verification Location

**Verification happens in handlers, not middleware:**
```python
# From routers/vessel.py
def _get_admin_id_from_event(event: Dict[str, Any]) -> str:
    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization")
    token = auth_header.removeprefix("Bearer ").strip()
    return get_subject_from_access_token(token)  # Verifies signature, expiry, type
```

**No global middleware** because each Lambda function is independent. Auth logic is duplicated across handlers.

### 5.3 Role Enforcement Boundaries

**Roles are stored in JWT claims but NOT enforced at the handler level.** Authorization is implicit based on which endpoint is called:

- `/admin/*` endpoints extract `admin_id` from token → only admins can call
- `/inspector/*` endpoints extract `inspector_id` from token → only inspectors can call
- `/crew/*` endpoints extract `crew_id` from token → only crew can call

**There is no role-based access control (RBAC) middleware.** If an inspector obtains an admin's JWT, they can call admin endpoints. **Mitigation:** Validate `role` claim in handlers:

```python
def _get_admin_id_from_event(event: Dict[str, Any]) -> str:
    token = ...
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    if payload.get("role") != "admin":
        raise ApiError("Forbidden", 403, "forbidden")
    return payload["sub"]
```

**This is NOT implemented.** Role enforcement relies on clients not sharing tokens.

### 5.4 Admin / Inspector / Crew Separation

**Separation is enforced by:**
1. Separate login endpoints (`/admin/login`, `/inspector/login`, `/crew/login`)
2. Separate JWT subjects (`admin_id`, `inspector_id`, `crew_id`)
3. Separate handler functions (e.g., `admin_auth.py`, `auth.py`, `crew.py`)

**Example:**
- Admin logs in → receives JWT with `sub: admin_id`, `role: "admin"`
- Admin calls `/vessels` → handler extracts `admin_id` from token → service filters vessels by `admin_id`
- Inspector logs in → receives JWT with `sub: inspector_id`, `role: "inspector"`
- Inspector calls `/assignments` → handler extracts `inspector_id` from token → service filters assignments by `assignee_id`

### 5.5 Common Auth Failure Modes

**1. Token expired:**
```python
except jwt.ExpiredSignatureError:
    raise ApiError("Token has expired", 401, "token_expired")
```

**2. Invalid signature (wrong secret key):**
```python
except jwt.InvalidTokenError:
    raise ApiError("Invalid token", 401, "invalid_token")
```

**3. Wrong token type (refresh token used for access):**
```python
if payload.get("type") != "access":
    raise ApiError("Invalid token type", 401, "invalid_token_type")
```

**4. Missing Authorization header:**
```python
if not auth_header or not auth_header.startswith("Bearer "):
    raise ValueError("Missing or invalid Authorization header")
```

**5. Case sensitivity (Authorization vs authorization):**
Handled by checking both:
```python
auth_header = headers.get("Authorization") or headers.get("authorization")
```

---

## 6. S3 Document Handling

### 6.1 Pre-Signed URL Generation

**Two types of pre-signed URLs:**

**1. PUT URL (for uploads):**
```python
# From utility/s3_utils.py
def generate_presigned_put_url(key: str, content_type: str, expires_in_seconds: int = 900) -> Dict[str, str]:
    url = _s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": settings.media_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in_seconds
    )
    return {"upload_url": url, "key": key, "bucket": settings.media_bucket}
```

**2. GET URL (for downloads):**
```python
def generate_presigned_get_url(key: str, expires_in_seconds: int = 900) -> str:
    return _s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.media_bucket, "Key": key},
        ExpiresIn=expires_in_seconds
    )
```

### 6.2 Upload Lifecycle

**Client-side upload flow:**
1. Client requests upload URL from backend (`POST /upload/presigned-url`)
2. Backend generates pre-signed PUT URL, returns to client
3. Client uploads file directly to S3 using PUT URL (bypasses backend)
4. Client sends S3 object URL to backend in subsequent request (e.g., `POST /inspectors` with `id_proof_url`)

**Server-side upload flow (used for multipart forms):**
```python
# From utility/s3_utils.py
def upload_file_to_s3(file_content: bytes, file_name: str, folder: Optional[str] = None, content_type: Optional[str] = None) -> str:
    safe_file_name = _sanitize_s3_filename(file_name)
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    unique_id = str(uuid4())[:8]
    key = f"{folder}/{timestamp}/{unique_id}_{safe_file_name}"
    
    _s3_client.put_object(Bucket=settings.media_bucket, Key=key, Body=file_content, ContentType=content_type)
    return f"https://{settings.media_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
```

### 6.3 Metadata Strategy

**S3 object metadata is NOT used.** File metadata (original filename, upload timestamp, uploader ID) is stored in DynamoDB:

```python
# From models/db/inspector.py
class InspectorDBModel(BaseModel):
    id_proof_url: Optional[str] = None  # S3 URL
    address_proof_url: Optional[str] = None
    additional_docs: Optional[list] = None  # List of S3 URLs
```

**S3 keys encode metadata:**
```
inspectors/20231215/a1b2c3d4_passport.pdf
^folder   ^date     ^uuid    ^filename
```

### 6.4 Security Boundaries

**1. Pre-signed URLs expire after 15 minutes (default).**
- Clients must use URLs immediately
- Expired URLs return 403 Forbidden from S3

**2. S3 bucket is private (no public read access).**
- All reads require pre-signed GET URLs
- Backend generates GET URLs on-demand when returning document URLs

**3. File uploads are NOT validated by backend.**
- Clients can upload any file type/size to pre-signed PUT URLs
- **Mitigation:** Enforce `ContentType` in pre-signed URL params (partially implemented)

**4. No virus scanning or content validation.**
- Uploaded files are assumed safe
- **Mitigation:** Implement S3 event trigger → Lambda → antivirus scan (not implemented)

### 6.5 Cleanup / Lifecycle Assumptions

**S3 objects are NEVER deleted by the application.**
- Deleting an inspector does not delete their uploaded documents
- Orphaned S3 objects accumulate over time

**Mitigation (not implemented):**
- S3 lifecycle policies to delete objects after 90 days
- Soft delete in DynamoDB (mark inspector as deleted, keep S3 URLs for audit)

---

## 7. Environment & Deployment Model

### 7.1 Local vs Deployed Behavior Differences

**Local development (not using Lambda):**
- FastAPI app runs via `uvicorn` (ASGI server)
- Handlers are NOT used; FastAPI routers are used instead
- **This codebase does NOT include FastAPI routers.** Handlers are designed for Lambda only.

**Deployed (AWS Lambda):**
- Each handler function is deployed as a separate Lambda
- API Gateway routes requests to Lambdas based on path/method
- No shared state between Lambdas (each has its own container)

### 7.2 API Gateway → Lambda Mapping

**Example mapping (inferred from handler structure):**

| HTTP Method | Path | Lambda Handler |
|-------------|------|----------------|
| POST | `/inspector/register` | `auth.register_handler` |
| POST | `/inspector/login` | `auth.login_handler` |
| GET | `/inspector/{inspector_id}` | `auth.profile_handler` |
| POST | `/admin/register` | `admin_auth.admin_register_handler` |
| POST | `/admin/login` | `admin_auth.admin_login_handler` |
| GET | `/admin/me` | `admin_auth.admin_me_handler` |
| POST | `/vessels` | `vessel.create_vessel_handler` |
| GET | `/vessels` | `vessel.list_vessels_handler` |
| GET | `/vessels/{vessel_id}` | `vessel.get_vessel_handler` |
| POST | `/assignments` | `inspection_assignment.create_inspection_assignment_handler` |
| GET | `/assignments/{assignment_id}` | `inspection_assignment.get_inspection_assignment_handler` |

**Each Lambda is configured with:**
- Handler: `routers/auth.register_handler`
- Runtime: Python 3.9+
- Memory: 512 MB (typical)
- Timeout: 30 seconds (typical)
- Environment variables (see below)

### 7.3 Environment Variables

**Required environment variables (from `config/settings.py`):**
```
AWS_REGION=us-east-1
DYNAMODB_TABLE_INSPECTORS=arka-inspectors-prod
DYNAMODB_TABLE_ADMINS=arka-admins-prod
DYNAMODB_TABLE_VESSELS=arka-vessels-prod
DYNAMODB_TABLE_INSPECTION_FORMS=arka-inspection-forms-prod
DYNAMODB_TABLE_INSPECTION_ASSIGNMENTS=arka-inspection-assignments-prod
DYNAMODB_TABLE_CREW=arka-crew-prod
DYNAMODB_TABLE_DEFECTS=arka-defects-prod
S3_MEDIA_BUCKET=arka-media-prod
JWT_SECRET_KEY=<random-256-bit-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=43200
```

**Optional (for local development):**
```
AWS_ACCESS_KEY_ID=<local-credentials>
AWS_SECRET_ACCESS_KEY=<local-credentials>
```

**In production, Lambdas use IAM roles (no access keys).**

### 7.4 IAM Role Boundaries

**Lambda execution role must have permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/arka-*",
        "arn:aws:dynamodb:us-east-1:*:table/arka-*/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::arka-media-prod/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

**Principle of least privilege:** Each Lambda should have a separate role with only the permissions it needs (not implemented; all Lambdas share one role).

### 7.5 Why No Persistent State Exists in Lambdas

**Lambda containers are ephemeral:**
- Containers are created/destroyed by AWS based on load
- No guarantee the same container handles subsequent requests
- Writing to `/tmp` is allowed but data is lost when container is destroyed

**Example of WRONG code:**
```python
# WRONG: In-memory cache
_cache = {}

def handler(event, context):
    if event["id"] in _cache:
        return _cache[event["id"]]
    data = fetch_from_db(event["id"])
    _cache[event["id"]] = data  # Lost when container is destroyed
    return data
```

**Correct approach:** Use DynamoDB or ElastiCache for caching.

---

## 8. Extension & Modification Rules

### 8.1 How to Add a New Module Safely

**Example: Adding a new entity `Notification`**

**Step 1: Create DynamoDB table**
- Table name: `arka-notifications-prod`
- Primary key: `notification_id` (String)
- GSI: `user_id_index` (PK: `user_id`)

**Step 2: Add table to `config/settings.py`**
```python
notifications_table: str = Field(..., env="DYNAMODB_TABLE_NOTIFICATIONS")
```

**Step 3: Add table getter to `config/aws.py`**
```python
def get_notifications_table():
    return dynamodb_resource.Table(settings.notifications_table)
```

**Step 4: Create DB model in `models/db/notification.py`**
```python
class NotificationDBModel(BaseModel):
    notification_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    message: str
    read: bool = False
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

**Step 5: Create repository in `repository/notification_repository.py`**
```python
class NotificationRepository:
    def __init__(self):
        self._table = get_notifications_table()
    
    def put_item(self, item: Dict[str, Any]) -> None:
        self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(notification_id)")
    
    def list_by_user(self, user_id: str, limit: int, cursor: Optional[Dict] = None) -> Tuple[List[Dict], Optional[Dict]]:
        response = self._table.query(
            IndexName="user_id_index",
            KeyConditionExpression="user_id = :user_id",
            ExpressionAttributeValues={":user_id": user_id},
            Limit=limit,
            ExclusiveStartKey=cursor
        )
        return response["Items"], response.get("LastEvaluatedKey")
```

**Step 6: Create service in `services/notification_service.py`**
```python
class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self._repository = repository
    
    def create_notification(self, user_id: str, message: str) -> Dict:
        notification = NotificationDBModel(user_id=user_id, message=message)
        self._repository.put_item(notification.dict())
        return notification.dict()
```

**Step 7: Create handler in `routers/notification.py`**
```python
repository = NotificationRepository()
service = NotificationService(repository)

@cors_middleware()
def create_notification_handler(event, context):
    try:
        user_id = _get_user_id_from_event(event)
        body = parse_json_body(event)
        data = service.create_notification(user_id, body["message"])
        response = format_response(True, data, "Notification created")
        return {"statusCode": 201, "body": json.dumps(response)}
    except Exception as exc:
        return handle_error(exc)
```

**Step 8: Deploy Lambda and configure API Gateway route**

### 8.2 Where New Business Logic Must Go

**Business logic belongs in services, NOT handlers or repositories.**

**Example: Sending email notification when inspector registers**

**WRONG (in handler):**
```python
def register_handler(event, context):
    data = service.register_inspector(payload)
    send_email(data["email"], "Welcome!")  # WRONG: side effect in handler
    return {"statusCode": 201, "body": ...}
```

**CORRECT (in service):**
```python
def register_inspector(self, payload: InspectorRegisterRequest) -> Dict:
    inspector = InspectorDBModel(...)
    self._repository.put_item(inspector.dict())
    self._send_welcome_email(inspector.email)  # Correct: side effect in service
    return response.dict()
```

### 8.3 Where Logic Must NOT Go

**Handlers must NOT:**
- Hash passwords
- Validate business rules (e.g., "crew can only have one assignment")
- Call multiple repositories
- Transform data (e.g., converting DynamoDB Decimal to float)

**Repositories must NOT:**
- Validate input (e.g., checking if email is valid format)
- Call other repositories
- Raise domain-specific errors (e.g., `ApiError("Email already exists")` should be raised by service, not repository)

### 8.4 Naming Conventions

**Files:**
- Handlers: `routers/<entity>.py` (e.g., `vessel.py`, `auth.py`)
- Services: `services/<entity>_service.py` (e.g., `vessel_service.py`)
- Repositories: `repository/<entity>_repository.py` (e.g., `vessel_repository.py`)
- DB models: `models/db/<entity>.py` (e.g., `vessel.py`)

**Functions:**
- Handlers: `<action>_handler` (e.g., `create_vessel_handler`, `login_handler`)
- Service methods: `<action>_<entity>` (e.g., `create_vessel`, `login_inspector`)
- Repository methods: `<crud_operation>` (e.g., `put_item`, `get_item`, `list_by_admin`)

**Classes:**
- Services: `<Entity>Service` (e.g., `VesselService`, `InspectorService`)
- Repositories: `<Entity>Repository` (e.g., `VesselRepository`)
- DB models: `<Entity>DBModel` (e.g., `VesselDBModel`)

### 8.5 How to Avoid Breaking Data Contracts

**DynamoDB schema changes are backward-compatible by default** (NoSQL allows missing attributes).

**Safe changes:**
- Adding new optional attributes (e.g., `vessel.flag_state`)
- Adding new GSIs

**Unsafe changes:**
- Renaming attributes (old code will not find data)
- Changing attribute types (e.g., `imo_number` from string to int)
- Removing attributes (old code may crash if it expects the attribute)

**Migration strategy:**
1. Add new attribute with default value in DB model
2. Deploy code that writes both old and new attributes
3. Backfill existing records (DynamoDB scan + update)
4. Deploy code that reads only new attribute
5. Remove old attribute from DB model

---

## 9. Anti-Patterns & Failure Scenarios

### 9.1 Common Mistakes New Developers Make

**1. Calling DynamoDB directly in handlers**
```python
# WRONG
def create_vessel_handler(event, context):
    table = boto3.resource("dynamodb").Table("vessels")
    table.put_item(Item={...})
```

**2. Not using Pydantic for validation**
```python
# WRONG
def register_handler(event, context):
    body = json.loads(event["body"])
    if "email" not in body:
        return {"statusCode": 400, "body": "Missing email"}
```

**3. Returning raw exceptions to client**
```python
# WRONG
def handler(event, context):
    try:
        ...
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}  # Leaks stack traces
```

**4. Storing secrets in code**
```python
# WRONG
JWT_SECRET = "my-secret-key"  # Should be in environment variables
```

**5. Not handling pagination**
```python
# WRONG
def list_vessels(admin_id):
    response = table.query(KeyConditionExpression=...)
    return response["Items"]  # Returns only first page (max 1 MB)
```

### 9.2 What Breaks Scalability

**1. Scanning large tables in user-facing endpoints**
```python
# WRONG: Scans entire table
def list_all_inspectors():
    response = table.scan()
    return response["Items"]
```

**2. N+1 queries without batching**
```python
# WRONG: 1 query per assignment
for assignment in assignments:
    vessel = vessel_repo.get_item(assignment["vessel_id"])
```

**Better: Use batch_get_item (not implemented in this codebase)**

**3. Synchronous processing of large batches**
```python
# WRONG: Blocks Lambda for 30 seconds
for i in range(1000):
    send_email(users[i])
```

**Better: Use SQS + background Lambda**

**4. Not using DynamoDB connection pooling**
```python
# WRONG: Creates new client per request
def handler(event, context):
    client = boto3.client("dynamodb")
```

**Correct: Initialize client at module level (already done in this codebase)**

### 9.3 What Breaks Security

**1. Not validating JWT signature**
```python
# WRONG: Trusts client-provided user ID
user_id = event["headers"]["X-User-ID"]
```

**2. Logging sensitive data**
```python
# WRONG
logger.info("User registered: %s", payload.password)
```

**3. Not using HTTPS for S3 pre-signed URLs**
```python
# WRONG: Uses HTTP
url = f"http://{bucket}.s3.amazonaws.com/{key}"
```

**4. Allowing unrestricted file uploads**
```python
# WRONG: No size limit, no type validation
presigned_url = generate_presigned_put_url(key, content_type="*/*")
```

**5. Not sanitizing user input in DynamoDB expressions**
```python
# WRONG: SQL injection equivalent
filter_expr = f"status = {user_input}"  # If user_input = "'; DROP TABLE--"
```

**Correct: Use ExpressionAttributeValues**

### 9.4 What Breaks Data Integrity

**1. Not using conditional writes**
```python
# WRONG: Overwrites existing item
table.put_item(Item=item)
```

**Correct: Use ConditionExpression**

**2. Not handling partial batch failures**
```python
# WRONG: Assumes all items were written
batch_write_item(RequestItems=...)
```

**Correct: Check UnprocessedItems and retry**

**3. Deleting items without checking references**
```python
# WRONG: Deletes vessel even if assignments exist
vessel_repo.delete_item(vessel_id)
```

**Correct: Check for assignments first, or use soft delete**

**4. Not validating foreign keys**
```python
# WRONG: Creates assignment without checking if vessel exists
assignment = InspectionAssignmentDBModel(vessel_id=payload.vessel_id, ...)
repo.put_item(assignment.dict())
```

**Correct: Validate in service (already done in this codebase)**

**5. Race conditions in business logic**
```python
# WRONG: Two concurrent requests can both pass this check
has_pending = repo.has_pending_assignments(crew_id)
if not has_pending:
    repo.put_item(assignment)  # Both requests create assignments
```

**Correct: Use DynamoDB transactions or conditional writes**

---

## Appendix: Quick Reference

### Key Files

| File | Purpose |
|------|---------|
| `config/settings.py` | Environment variable loading |
| `config/aws.py` | DynamoDB/S3 client initialization |
| `config/jwt_config.py` | JWT generation/verification |
| `utility/error_handler.py` | Exception → HTTP response conversion |
| `utility/cors.py` | CORS middleware decorator |
| `utility/body_parser.py` | JSON body parsing |
| `utility/s3_utils.py` | S3 pre-signed URL generation |
| `routers/*.py` | Lambda handler functions |
| `services/*.py` | Business logic layer |
| `repository/*.py` | DynamoDB data access layer |
| `models/db/*.py` | DynamoDB entity schemas |

### DynamoDB Tables

| Table | Primary Key | GSIs |
|-------|-------------|------|
| Inspectors | `inspector_id` | `email_index` |
| Admins | `admin_id` | `email_index` |
| Vessels | `vessel_id` | `admin_id_index` |
| Crew | `crew_id` | `email_index`, `vessel_id_index` |
| InspectionForms | `form_id` | `admin_id_index` |
| InspectionAssignments | `assignment_id` | `admin_id_index`, `form_id_index`, `assignee_id_index` |
| Defects | `defect_id` | `form_id_index` |

### Common Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| `email_exists` | 409 | Email already registered |
| `invalid_credentials` | 401 | Wrong email/password |
| `token_expired` | 401 | JWT expired |
| `invalid_token` | 401 | JWT signature invalid |
| `inspector_not_found` | 404 | Inspector ID does not exist |
| `vessel_not_found` | 404 | Vessel ID does not exist |
| `dynamodb_error` | 500 | DynamoDB operation failed |
| `presign_failed` | 500 | S3 pre-signed URL generation failed |

### Dependencies

```
boto3==1.34.90          # AWS SDK
pydantic==1.10.14       # Data validation
PyJWT==2.8.0            # JWT encoding/decoding
bcrypt==4.1.2           # Password hashing
python-dotenv==1.0.1    # .env file loading
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-24  
**Maintainer**: Backend Team
