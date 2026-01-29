"""
Service layer for inspection form creation and updates.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

from repository.crew_repository import CrewRepository
from repository.defect_repository import DefectRepository
from repository.inspection_assignment_repository import InspectionAssignmentRepository
from repository.inspection_form_repository import InspectionFormRepository
from repository.inspection_response_repository import InspectionResponseRepository
from repository.inspector_repository import InspectorRepository
from repository.vessel_repository import VesselRepository
from utility.errors import ApiError
from utility.logger import get_logger
from utility.s3_utils import sign_s3_url_if_possible


class InspectionFormService:
    """
    Business logic for creating inspection forms with ordered questions.
    """

    def __init__(
        self,
        repository: InspectionFormRepository,
        assignment_repository: Optional[InspectionAssignmentRepository] = None,
        defect_repository: Optional[DefectRepository] = None,
        inspector_repository: Optional[InspectorRepository] = None,
        crew_repository: Optional[CrewRepository] = None,
    ) -> None:
        self._repository = repository
        self._assignment_repository = assignment_repository or InspectionAssignmentRepository()
        self._defect_repository = defect_repository or DefectRepository()
        self._inspector_repository = inspector_repository or InspectorRepository()
        self._crew_repository = crew_repository or CrewRepository()
        self._vessel_repository = VesselRepository()
        self._response_repository = InspectionResponseRepository()
        self._logger = get_logger(self.__class__.__name__)

    def _serialize_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert question/section request list into serializable dictionaries ordered by the order field.
        """
        if not questions:
            return []
            
        # Sort by order
        ordered = sorted(questions, key=lambda q: int(q.get("order", 0)))
        serialized: List[Dict[str, Any]] = []
        for question in ordered:
            item = {
                "order": int(question.get("order", 0)),
                "type": question.get("type"),
            }
            
            # Add fields based on item type
            if question.get("type") == "section":
                # For sections, add title
                item["title"] = question.get("title")
            else:
                # For questions, add question-specific fields
                item["prompt"] = question.get("prompt")
                item["options"] = question.get("options") or []
                item["media_url"] = question.get("media_url")
                item["allow_image_upload"] = question.get("allow_image_upload", False)
            
            serialized.append(item)
        
        # Debug: Log serialized items
        self._logger.info(f"📦 Serialized {len(serialized)} items")
        for idx, item in enumerate(serialized):
            if item.get("type") == "section":
                self._logger.info(f"  📌 Item {idx+1} (SECTION): order={item.get('order')}, title='{item.get('title')}', has_title={bool(item.get('title'))}")
            else:
                self._logger.info(f"  ❓ Item {idx+1} (QUESTION): order={item.get('order')}, type={item.get('type')}, prompt='{item.get('prompt', '')[:30]}...'")
        
        return serialized

    def _item_to_response(self, item: Dict[str, Any], inspection_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert DynamoDB item to dictionary response.
        
        If inspection_id is provided, fetches and merges responses from InspectionResponses table.
        Also re-signs media URLs.
        """
        
        # New: Fetch responses if inspection_id provided
        responses_map = {}
        if inspection_id:
            try:
                responses = self._response_repository.query_by_inspection(inspection_id)
                for r in responses:
                    # question_id is the order number as string
                    responses_map[r["question_id"]] = {
                        "value": r["answer_value"],
                        "media_url": r.get("media_url")
                    }
            except Exception as exc:
                self._logger.warning("Failed to fetch responses for merge: %s", exc)
                # Continue without responses (partial failure safe)
        
        questions_list = []
        for q in item.get("questions", []):
            q_dict = dict(q) if isinstance(q, dict) else q
            order_str = str(q_dict.get("order", ""))
            
            # Re-sign media_url if present (to handle expired S3 URLs)
            if "media_url" in q_dict and q_dict.get("media_url"):
                media_url = q_dict["media_url"]
                signed_url = sign_s3_url_if_possible(media_url, expires_in_seconds=900)
                if signed_url:
                    q_dict["media_url"] = signed_url
            
            # MERGE LOGIC:
            if inspection_id and order_str in responses_map:
                # Merge answer from InspectionResponses table
                response_data = responses_map[order_str]
                answer_value = response_data["value"]
                media_url = response_data.get("media_url")
                
                question_type = q_dict.get("type", "")
                
                # MERGE LOGIC:
                # Always set the text answer value
                q_dict["answer"] = answer_value

                # Set media_url if available (this preserves the image separately)
                if media_url:
                     q_dict["media_url"] = media_url
                
                # If specifically an image type question and no media_url but answer is a URL, move it to media_url
                # This handles legacy cases where URL was stored in answer
                if question_type == "image":
                    if not media_url and answer_value and str(answer_value).startswith("http"):
                         q_dict["media_url"] = answer_value
                         # We can keep it in answer too, or clear it. Keeping it is safer for now.
                
                # Re-sign merged media_url if present (e.g. from InspectionResponses)
                merged_media_url = q_dict.get("media_url")
                if merged_media_url and isinstance(merged_media_url, str) and merged_media_url.startswith("http") and "s3" in merged_media_url.lower():
                     signed_media_url = sign_s3_url_if_possible(merged_media_url, expires_in_seconds=900)
                     if signed_media_url:
                         q_dict["media_url"] = signed_media_url
                
            # Re-sign answer if it's an S3 URL (for image answers)
            answer_value = q_dict.get("answer")
            if answer_value:
                answer_str = str(answer_value).strip()
                if answer_str and answer_str.startswith("http") and "s3" in answer_str.lower():
                    signed_answer_url = sign_s3_url_if_possible(answer_str, expires_in_seconds=900)
                    if signed_answer_url:
                        q_dict["answer"] = signed_answer_url
            
            questions_list.append(q_dict)
        
        return {
            "form_id": item["form_id"],
            "vessel_id": item["vessel_id"],
            "created_by_admin_id": item.get("created_by_admin_id"),
            "ship_id": item.get("ship_id"),
            "title": item["title"],
            "description": item.get("description"),
            "status": item.get("status", "Unassigned"),
            "assigned_inspector_id": item.get("assigned_inspector_id"),
            "assigned_crew_id": item.get("assigned_crew_id"),
            "due_date": item.get("due_date"),
            "recurrence_start_date": item.get("recurrence_start_date"),
            "recurrence_interval_value": item.get("recurrence_interval_value"),
            "recurrence_interval_unit": item.get("recurrence_interval_unit"),
            "reminder_before_value": item.get("reminder_before_value"),
            "reminder_before_unit": item.get("reminder_before_unit"),
            "last_synced_at": item.get("last_synced_at"),
            "questions": questions_list,
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }

    def _item_to_response_without_questions(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert DynamoDB item to dictionary response without questions.
        Used for listing endpoints where questions are not needed.
        """
        return {
            "form_id": item["form_id"],
            "vessel_id": item["vessel_id"],
            "created_by_admin_id": item.get("created_by_admin_id"),
            "ship_id": item.get("ship_id"),
            "title": item["title"],
            "description": item.get("description"),
            "status": item.get("status", "Unassigned"),
            "assigned_inspector_id": item.get("assigned_inspector_id"),
            "assigned_crew_id": item.get("assigned_crew_id"),
            "due_date": item.get("due_date"),
            "recurrence_start_date": item.get("recurrence_start_date"),
            "recurrence_interval_value": item.get("recurrence_interval_value"),
            "recurrence_interval_unit": item.get("recurrence_interval_unit"),
            "reminder_before_value": item.get("reminder_before_value"),
            "reminder_before_unit": item.get("reminder_before_unit"),
            "last_synced_at": item.get("last_synced_at"),
            "questions": [],
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }

    def create_form(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an inspection form and persist it to DynamoDB.
        """

        try:
            vessel_id = payload.get("vessel_id")
            title = payload.get("title")
            
            if not title:
                raise ApiError("Title is required", 400, "missing_title")

            self._logger.info("Creating inspection form for admin_id=%s vessel_id=%s title=%s", admin_id, vessel_id, title)
            
            # Check if a form with the same title already exists and is active/assigned
            existing_form = self._repository.find_active_form_by_title(title)
            if existing_form:
                raise ApiError(
                    f"A form with the title '{title}' already exists and is active or assigned. Form names must be unique.",
                    409,
                    "duplicate_form_title",
                )
            
            questions = self._serialize_questions(payload.get("questions", []))
            vessel_id = vessel_id or "unassigned"
            
            now = datetime.utcnow().isoformat()
            # We don't have a Pydantic model to generate UUID, assume Repository or Service handles ID generation?
            # Looking at `repository.put_item`, it usually expects 'form_id'.
            # The previous Pydantic model `InspectionFormDBModel` likely auto-generated `form_id`.
            # I need to generate `form_id` here.
            from uuid import uuid4
            uid = str(uuid4())
            pk = f"FORM#{uid}"
            form_dict = {
                "PK":pk,
                "SK":"METADATA",
                "form_id": uid,
                "vessel_id": vessel_id,
                "title": title,
                "description": payload.get("description"),
                "due_date": payload.get("due_date"),
                "created_by_admin_id": admin_id,
                "questions": questions,
                "recurrence_start_date": payload.get("recurrence_start_date"),
                "recurrence_interval_value": payload.get("recurrence_interval_value"),
                "recurrence_interval_unit": payload.get("recurrence_interval_unit"),
                "reminder_before_value": payload.get("reminder_before_value"),
                "reminder_before_unit": payload.get("reminder_before_unit"),
                "status": "Unassigned",
                "created_at": now,
                "updated_at": now,
                "GSI1PK": "FORM",
                "GSI1SK": title,
            }
            
            # Exclude None values
            form_dict = {k: v for k, v in form_dict.items() if v is not None}
            
            self._logger.debug("Inspection form payload prepared: %s", form_dict)
            self._repository.put_item(form_dict)
            return self._item_to_response(form_dict)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to create inspection form: %s", exc)
            raise ApiError("Failed to create inspection form", 500, "create_form_failed") from exc

    def update_form(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an inspection form owned by the admin.
        """

        try:
            form_id = payload.get("form_id")
            if not form_id:
                raise ApiError("Form ID is required", 400, "missing_form_id")

            self._logger.info("Updating inspection form %s by admin %s", form_id, admin_id)
            existing = self._repository.get_item(form_id)
            if not existing:
                raise ApiError("Inspection form not found", 404, "form_not_found")

            if existing.get("created_by_admin_id") and existing.get("created_by_admin_id") != admin_id:
                raise ApiError("Not authorized to update this form", 403, "forbidden")

            attributes: Dict[str, Any] = {}
            if "vessel_id" in payload:
                attributes["vessel_id"] = payload.get("vessel_id") or "unassigned"
            
            payload_title = payload.get("title")
            if payload_title is not None:
                # Check if title is being changed and if new title conflicts with existing active form
                if payload_title != existing.get("title"):
                    existing_form = self._repository.find_active_form_by_title(
                        payload_title,
                        exclude_form_id=form_id
                    )
                    if existing_form:
                        raise ApiError(
                            f"A form with the title '{payload_title}' already exists and is active or assigned. Form names must be unique.",
                            409,
                            "duplicate_form_title",
                        )
                attributes["title"] = payload_title
                
            if "description" in payload:
                attributes["description"] = payload.get("description")
            if "due_date" in payload:
                attributes["due_date"] = payload.get("due_date")
            if "recurrence_start_date" in payload:
                attributes["recurrence_start_date"] = payload.get("recurrence_start_date")
            if "recurrence_interval_value" in payload:
                attributes["recurrence_interval_value"] = payload.get("recurrence_interval_value")
            if "recurrence_interval_unit" in payload:
                attributes["recurrence_interval_unit"] = payload.get("recurrence_interval_unit")
            if "reminder_before_value" in payload:
                attributes["reminder_before_value"] = payload.get("reminder_before_value")
            if "reminder_before_unit" in payload:
                attributes["reminder_before_unit"] = payload.get("reminder_before_unit")
            if "questions" in payload:
                attributes["questions"] = self._serialize_questions(payload.get("questions", []))
            if "status" in payload:
                attributes["status"] = payload.get("status")

            if not attributes:
                return self._item_to_response(existing)

            attributes["updated_at"] = datetime.utcnow().isoformat()
            updated_item = self._repository.update_item(form_id, attributes)
            return self._item_to_response(updated_item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to update inspection form: %s", exc)
            raise ApiError("Failed to update inspection form", 500, "update_form_failed") from exc

    def deactivate_form(self, admin_id: str, form_id: str) -> Dict[str, Any]:
        """
        Deactivate an inspection form by setting its status to 'deactivated'.
        """

        try:
            self._logger.info("Deactivating inspection form %s by admin %s", form_id, admin_id)
            existing = self._repository.get_item(form_id)
            if not existing:
                raise ApiError("Inspection form not found", 404, "form_not_found")

            # Verify admin owns the form
            if existing.get("created_by_admin_id") and existing.get("created_by_admin_id") != admin_id:
                raise ApiError("Not authorized to deactivate this form", 403, "forbidden")

            # Check if form is already closed
            current_status = existing.get("status", "Unassigned")
            if current_status.lower() == "closed":
                raise ApiError(
                    "Form is already closed. Cannot deactivate again.",
                    400,
                    "form_already_closed",
                )

            # Update form status to Closed
            attributes = {
                "status": "Closed",
                "updated_at": datetime.utcnow().isoformat(),
            }
            updated_item = self._repository.update_item(form_id, attributes)
            return self._item_to_response(updated_item)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to deactivate inspection form: %s", exc)
            raise ApiError("Failed to deactivate inspection form", 500, "deactivate_form_failed") from exc

    def get_form_by_id(self, payload: Dict[str, Any], inspection_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve an inspection form by its ID.
        """

        try:
            form_id = payload.get("form_id")
            if not form_id:
                raise ApiError("Form ID is required", 400, "missing_form_id")

            self._logger.info("Fetching inspection form: %s (inspection_id=%s)", form_id, inspection_id)
            item = self._repository.get_item(form_id)
            if not item:
                raise ApiError("Inspection form not found", 404, "form_not_found")
            
            return self._item_to_response(item, inspection_id=inspection_id)
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to fetch inspection form: %s", exc)
            raise ApiError("Failed to fetch inspection form", 500, "get_form_failed") from exc

    def _determine_actor_type(self, actor_id: str) -> str:
        """
        Determine if actor_id belongs to an inspector or crew member.
        """

        inspector = self._inspector_repository.get_item(actor_id)
        if inspector:
            return "inspector"
        crew = self._crew_repository.get_item(actor_id)
        if crew:
            return "crew"
        raise ApiError("Actor not found as inspector or crew member", 404, "actor_not_found")

    def _create_defect_for_question(
        self,
        form_item: Dict[str, Any],
        question: Dict[str, Any],
        question_order: int,
        answer_value: Any,
        actor_id: str,
        actor_type: str,
        assignment_id: Optional[str],
    ) -> None:
        """
        Create a defect record for a question marked as defect.
        """

        vessel_id = form_item.get("vessel_id", "unassigned")
        if not vessel_id or vessel_id == "unassigned":
            # Try to get vessel_id from assignment if available
            if assignment_id:
                assignment = self._assignment_repository.get_item(assignment_id)
                if assignment and assignment.get("vessel_id") and assignment.get("vessel_id") != "unassigned":
                    vessel_id = assignment.get("vessel_id")
        
        # Ensure vessel_id is never None or empty
        if not vessel_id:
            vessel_id = "unassigned"

        question_prompt = question.get("prompt", "")
        question_type = question.get("type", "")
        
        # Generate defect title from question prompt (truncate if too long)
        defect_title = question_prompt[:200] if len(question_prompt) <= 200 else question_prompt[:197] + "..."
        
        # Convert answer_value to string if needed
        answer_str = str(answer_value) if answer_value is not None else ""
        
        # Use answer as description if it's not an image
        description = None
        photos = None
        if question_type == "image" and answer_str.startswith("http"):
            photos = [answer_str]
        elif question_type != "image" and answer_str and answer_str.lower() != "defect":
            # Don't use "Defect" as description, use the actual answer if available
            description = f"Question answer: {answer_str}"[:1000]

        # Determine who raised the defect
        raised_by_inspector_id = None
        raised_by_crew_id = None
        if actor_type == "inspector":
            raised_by_inspector_id = actor_id
        elif actor_type == "crew":
            raised_by_crew_id = actor_id

        # Generate defect_id manually since we don't have DefectDBModel
        from uuid import uuid4
        defect_id = str(uuid4())
        pk=f"DEFECT#{defect_id}"
        defect_dict = {
            "PK":pk,
            "SK":"METADATA",
            "defect_id": defect_id,
            "vessel_id": vessel_id,
            "form_id": form_item["form_id"],
            "assignment_id": assignment_id,
            "title": defect_title,
            "description": description,
            "severity": "minor",
            "priority": "medium",
            "status": "open",
            "raised_by_inspector_id": raised_by_inspector_id,
            "raised_by_crew_id": raised_by_crew_id,
            "triggered_question_order": question_order,
            "triggered_question_text": question_prompt,
            "photos": photos,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "GSI1PK":"DEFECT",
            "GSI1SK":defect_title,
            "GSI2PK": vessel_id,
            "GSI2SK":defect_title,
            
        }
        
        defect_dict = {k: v for k, v in defect_dict.items() if v is not None}

        self._defect_repository.put_item(defect_dict)
        self._logger.info("Created defect %s for question %s in form %s", defect_id, question_order, form_item["form_id"])

    def _is_form_active(self, form: Dict[str, Any]) -> bool:
        """
        Check if a form is active and can accept submissions.
        """
        status = form.get("status", "Unassigned")
        return status.lower() in ("unassigned", "in progress")

    def submit_form(self, actor_id: str, payload: Dict[str, Any], inspection_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit answers for an inspection form by an inspector or crew member.
        """

        try:
            form_id = payload.get("form_id")
            if not form_id:
                raise ApiError("Form ID is required", 400, "missing_form_id")
            
            self._logger.info("Submitting inspection form %s by actor %s (inspection_id=%s)", form_id, actor_id, inspection_id)
            
            # CRITICAL CHECK: inspection_id is mandatory
            if not inspection_id:
                raise ApiError(
                    "inspection_id is required for submission. Please update your app.",
                    400,
                    "missing_inspection_id"
                )
            
            # NEW: Prevent resubmission of closed inspections
            assignment = self._assignment_repository.get_item(inspection_id)
            if assignment:
                current_status = assignment.get("status", "").upper()
                if current_status == "CLOSED" or current_status == "COMPLETED":
                    raise ApiError(
                        "This inspection has already been submitted and is closed. Resubmission is not allowed.",
                        400,
                        "inspection_already_closed"
                    )

            existing = self._repository.get_item(form_id)
            if not existing:
                raise ApiError("Inspection form not found", 404, "form_not_found")

            # Check if form is active and can accept submissions
            if not self._is_form_active(existing):
                status = existing.get("status", "Unassigned")
                raise ApiError(
                    f"Cannot submit to a {status} form. Form submissions are closed.",
                    400,
                    "form_not_active",
                )

            # Determine actor type (inspector or crew)
            actor_type = self._determine_actor_type(actor_id)

            answers_list = payload.get("answers", [])
            # Create a map of order -> entire answer object to access all fields
            answers_map = {
                int(answer.get("order")): answer 
                for answer in answers_list
                if "order" in answer
            }
            
            # Create simple map for legacy defect logic
            answers_by_order = {
                order: obj.get("value") for order, obj in answers_map.items()
            }
            
            defect_orders = set(payload.get("defects") or [])
            
            # Also check if any answer value is "Defect" (case-insensitive) and add to defects
            for order, answer_value in answers_by_order.items():
                if isinstance(answer_value, str) and answer_value.strip().lower() == "defect":
                    defect_orders.add(order)

            # 1. Prepare responses for batch write
            response_items: List[Dict[str, Any]] = []
            
            for answer in answers_list:
                order = int(answer.get("order"))
                value = answer.get("value")
                media_url = answer.get("media_url")
                
                # Validation: Legacy support - if value is a URL and no media_url, assume value IS the media_url
                if not media_url and isinstance(value, str) and value.startswith("http"):
                    media_url = value
                
                # Prepare item for InspectionResponses table
                response_item = {
                    "inspection_id": inspection_id,
                    "question_id": str(order),
                    "answer_value": str(value) if value is not None else "",
                    "is_defect": order in defect_orders,
                    "media_url": media_url, # Now strictly saving the media_url
                    "updated_at": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                }
                
                response_items.append(response_item)
            
            # 2. Write responses to InspectionResponses table
            if response_items:
                self._response_repository.batch_put_items(response_items)
            
            # 3. Create Defects (Legacy logic maintained)
            for question in existing.get("questions", []):
                order = int(question.get("order"))
                if order in defect_orders and order in answers_by_order:
                     self._create_defect_for_question(
                        form_item=existing,
                        question=question,
                        question_order=order,
                        answer_value=answers_by_order[order],
                        actor_id=actor_id,
                        actor_type=actor_type,
                        assignment_id=inspection_id,
                    )

            # 4. Update InspectionAssignment status
            updated_questions_count = len(existing.get("questions", []))
            answered_orders = set(answers_by_order.keys())
            
            all_questions_answered = len(answered_orders) >= updated_questions_count
            new_assignment_status = "CLOSED" if all_questions_answered else "IN_PROGRESS"
            
            try:
                self._assignment_repository.update_item(inspection_id, {"status": new_assignment_status, "updated_at": datetime.utcnow().isoformat()})
            except Exception as e:
                self._logger.warning("Failed to update assignment status: %s", e)

            # 5. Return updated form view
            return self.get_form_by_id(
                {"form_id": form_id},
                inspection_id=inspection_id
            )
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to submit inspection form: %s", exc)
            raise ApiError("Failed to submit inspection form", 500, "submit_form_failed") from exc

    def list_forms(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List inspection forms with searching, sorting, and pagination.
        """

        try:
            vessel_id = payload.get("vessel_id")
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            search = payload.get("search")
            
            # Fetch all matching items to allow global sorting and searching
            all_items = []
            cursor = None
            while True:
                if vessel_id:
                    items, cursor = self._repository.list_by_vessel(
                        vessel_id=vessel_id, limit=1000, cursor=cursor
                    )
                else:
                    items, cursor = self._repository.list_by_admin(
                        admin_id=admin_id, limit=1000, cursor=cursor
                    )
                all_items.extend(items)
                if not cursor:
                    break

            # Apply search filter if provided
            if search:
                search_term = search.lower().strip()
                all_items = [
                    item for item in all_items
                    if search_term in item.get("title", "").lower()
                    or search_term in item.get("description", "").lower()
                ]

            # Sort by created_at descending (newest first)
            all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            # Apply pagination
            total_items = len(all_items)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            paged_items = all_items[start_idx:end_idx]
            has_next = total_items > end_idx

            forms = [self._item_to_response(item) for item in paged_items]

            return {
                "items": forms,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list inspection forms: %s", exc)
            raise ApiError("Failed to list inspection forms", 500, "list_forms_failed") from exc

    def list_submitted_forms(self, admin_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List submitted (Closed) forms with answers for admin view.
        """

        try:
            inspector_id = payload.get("inspector_id")
            crew_id = payload.get("crew_id")
            vessel_id = payload.get("vessel_id")
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            
            self._logger.info(
                "Listing submitted forms for admin %s with filters: inspector_id=%s, crew_id=%s, vessel_id=%s",
                admin_id, inspector_id, crew_id, vessel_id
            )

            # Fetch all matching items for global sorting
            all_matching_items = []
            cursor = None
            while True:
                if vessel_id:
                    batch_items, cursor = self._repository.list_by_vessel(
                        vessel_id=vessel_id, limit=1000, cursor=cursor
                    )
                else:
                    batch_items, cursor = self._repository.list_by_admin(
                        admin_id=admin_id, limit=1000, cursor=cursor
                    )
                
                # Filter this batch
                for item in batch_items:
                    status = item.get("status", "Unassigned")
                    if status.strip().lower() != "closed":
                        continue
                    
                    if inspector_id and item.get("assigned_inspector_id") != inspector_id:
                        continue
                    
                    if crew_id and item.get("assigned_crew_id") != crew_id:
                        continue

                    all_matching_items.append(item)
                
                if not cursor:
                    break

            # Sort by created_at descending (newest first)
            all_matching_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            # Apply pagination
            total_items = len(all_matching_items)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            paged_items = all_matching_items[start_idx:end_idx]
            has_next = total_items > end_idx

            forms = [self._item_to_response(item) for item in paged_items]

            return {
                "items": forms,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list submitted forms: %s", exc)
            raise ApiError("Failed to list submitted forms", 500, "list_submitted_forms_failed") from exc

    def list_forms_for_inspector(self, inspector_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        List inspection forms assigned to an inspector.
        """

        try:
            page = payload.get("page", 1)
            limit = payload.get("limit", 20)
            search = payload.get("search")

            # Fetch all assignments for the inspector
            all_assignments = []
            cursor = None
            while True:
                assignments, cursor = self._assignment_repository.list_by_assignee(
                    assignee_id=inspector_id, limit=1000, cursor=cursor
                )
                all_assignments.extend(assignments)
                if not cursor:
                    break

            # Build list of (assignment, form, vessel_name)
            inspection_items = []
            
            # Cache vessel names to avoid repeated lookups
            vessel_cache = {}

            for assignment in all_assignments:
                form_id = assignment.get("form_id")
                if not form_id:
                    continue
                
                form_item = self._repository.get_item(form_id)
                if not form_item:
                    continue
                
                vessel_id = assignment.get("vessel_id")
                vessel_name = "Unassigned"
                
                if vessel_id:
                    if vessel_id in vessel_cache:
                        vessel_name = vessel_cache[vessel_id]
                    else:
                        if vessel_id.lower() != "unassigned":
                            vessel_item = self._vessel_repository.get_item(vessel_id)
                            if vessel_item:
                                vessel_name = vessel_item.get("name", "Unknown Vessel")
                                vessel_cache[vessel_id] = vessel_name
                            else:
                                vessel_cache[vessel_id] = "Unknown Vessel"
                        else:
                            vessel_cache[vessel_id] = "Unassigned"
                
                inspection_items.append({
                    "assignment": assignment,
                    "form": form_item,
                    "vessel_name": vessel_name
                })

            # Apply search filter if provided
            if search:
                search_term = search.lower().strip()
                filtered_items = []
                for item in inspection_items:
                    # Construct the display title for searching
                    base_title = item['form'].get("title", "")
                    vessel_suffix = f" - {item['vessel_name']}" if item['vessel_name'] != "Unassigned" else ""
                    full_title = f"{base_title}{vessel_suffix}"
                    
                    description = item['form'].get("description", "")
                    
                    if search_term in full_title.lower() or search_term in description.lower():
                        filtered_items.append(item)
                inspection_items = filtered_items

            # Sort by ASSIGNMENT created_at descending (newest assignment first)
            inspection_items.sort(key=lambda x: x["assignment"].get("created_at", ""), reverse=True)

            # Apply pagination
            total_items = len(inspection_items)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            paged_items = inspection_items[start_idx:end_idx]
            has_next = total_items > end_idx

            final_forms = []
            for item in paged_items:
                # Convert form item to response
                response = self._item_to_response_without_questions(item['form'])
                
                # Update Title with Vessel Name
                if item['vessel_name'] != "Unassigned":
                    current_title = response.get("title", "")
                    response["title"] = f"{current_title} - {item['vessel_name']}"
                
                # Override created_at with assignment created_at
                if item['assignment'].get("created_at"):
                    response["created_at"] = item['assignment'].get("created_at")
                
                # Add inspection_name from assignment
                if item['assignment'].get("inspection_name"):
                    response["inspection_name"] = item['assignment'].get("inspection_name")
                    
                final_forms.append(response)

            return {
                "items": final_forms,
                "page": page,
                "limit": limit,
                "has_next": has_next,
            }
        except ApiError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error("Failed to list inspection forms for inspector: %s", exc)
            raise ApiError("Failed to list inspection forms", 500, "list_forms_failed") from exc
