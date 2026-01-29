"""
Request models for inspection form creation.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, constr, validator


class InspectionQuestionRequest(BaseModel):
    """
    Represents a single question in an inspection form.
    """

    order: int = Field(..., description="Zero or one-based order of the question.")
    prompt: Optional[str] = Field(None, min_length=1, max_length=500, description="Question text (required for questions).")
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Section title (required for sections).")
    type: str = Field(..., description="Item type: mcq, text, image, or section.")
    options: Optional[List[str]] = Field(
        default=None,
        description="List of options for mcq type. Ignored for text, image, or section.",
    )
    media_url: Optional[str] = Field(
        default=None,
        description="Optional URL to an image or media asset associated with the question.",
    )
    allow_image_upload: Optional[bool] = Field(
        default=None,
        description="Whether this question allows image uploads as answers. For hybrid MCQ/text + image questions.",
    )

    @validator("type")
    def validate_type(cls, value: str) -> str:
        """
        Ensure only supported question types are accepted.
        """

        allowed = {"mcq", "text", "image", "section"}
        if value not in allowed:
            raise ValueError(f"Invalid question type. Allowed: {allowed}")
        return value

    @validator("options", always=True)
    def validate_options(cls, value: Optional[List[str]], values: dict) -> Optional[List[str]]:
        """
        Ensure options are present for MCQ questions and absent otherwise.
        """

        question_type = values.get("type")
        if question_type == "mcq":
            if not value or not [opt for opt in value if opt.strip()]:
                raise ValueError("MCQ questions require at least one non-empty option.")
            return [opt.strip() for opt in value if opt.strip()]
        if value and question_type != "mcq":  # Changed logic slightly to be cleaner
            raise ValueError("Only MCQ questions can include options.")
        return None

    @validator("media_url")
    def validate_media_url(cls, value: Optional[str], values: dict) -> Optional[str]:
        """
        Validate optional media_url for any question type.
        Media is treated as a supporting document, so it can be attached to mcq, text, or image questions.
        """

        if value is None:
            return value
        # Basic normalization/validation hook – trim whitespace and ensure non-empty when provided
        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class CreateInspectionFormRequest(BaseModel):
    """
    Request payload for creating an inspection form with questions.
    """

    vessel_id: Optional[str] = Field(
        default=None,
        description="Optional vessel identifier the form belongs to. If omitted, the form will be stored as unassigned.",
    )
    title: str = Field(..., min_length=1, max_length=100, description="Form title.")
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional form description.",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Optional ISO8601 due date.",
    )
    recurrence_start_date: Optional[str] = Field(
        default=None,
        description="Optional ISO8601 date when recurrence starts.",
    )
    recurrence_interval_value: Optional[int] = Field(
        default=None,
        description="How often the form should recur (numeric component).",
    )
    recurrence_interval_unit: Optional[str] = Field(
        default=None,
        description="Unit for recurrence interval: day, week, month, or year.",
    )
    reminder_before_value: Optional[int] = Field(
        default=None,
        description="How many units before due_date to send a reminder.",
    )
    reminder_before_unit: Optional[str] = Field(
        default=None,
        description="Unit for reminder offset: day, week, or month.",
    )
    questions: List[InspectionQuestionRequest] = Field(
        ..., description="Ordered list of questions."
    )

    @validator("recurrence_interval_unit")
    def validate_recurrence_interval_unit(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate recurrence interval unit when provided.
        """

        if value is None:
            return None
        allowed = {"day", "week", "month", "year"}
        if value not in allowed:
            raise ValueError(f"Invalid recurrence_interval_unit. Allowed: {allowed}")
        return value

    @validator("reminder_before_unit")
    def validate_reminder_before_unit(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate reminder unit when provided.
        """

        if value is None:
            return None
        allowed = {"day", "week", "month"}
        if value not in allowed:
            raise ValueError(f"Invalid reminder_before_unit. Allowed: {allowed}")
        return value

    @validator("questions")
    def validate_question_order(cls, value: List[InspectionQuestionRequest]) -> List[InspectionQuestionRequest]:
        """
        Ensure question orders are unique.
        """

        orders = [q.order for q in value]
        if len(orders) != len(set(orders)):
            raise ValueError("Question order values must be unique.")
        return value


class UpdateInspectionFormRequest(BaseModel):
    """
    Request payload for updating an inspection form with questions.
    All fields are optional except form_id.
    """

    form_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Inspection form identifier.")
    vessel_id: Optional[str] = Field(
        default=None,
        description="Optional vessel identifier the form belongs to. If omitted, the form will be stored as unassigned.",
    )
    title: Optional[str] = Field(default=None, min_length=1, max_length=100, description="Form title.")
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional form description.",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Optional ISO8601 due date.",
    )
    questions: Optional[List[InspectionQuestionRequest]] = Field(
        default=None, description="Ordered list of questions."
    )
    status: Optional[str] = Field(
        default=None,
        description="Workflow status: Unassigned, In Progress, Closed.",
    )
    recurrence_start_date: Optional[str] = Field(
        default=None,
        description="Optional ISO8601 date when recurrence starts.",
    )
    recurrence_interval_value: Optional[int] = Field(
        default=None,
        description="How often the form should recur (numeric component).",
    )
    recurrence_interval_unit: Optional[str] = Field(
        default=None,
        description="Unit for recurrence interval: day, week, month, or year.",
    )
    reminder_before_value: Optional[int] = Field(
        default=None,
        description="How many units before due_date to send a reminder.",
    )
    reminder_before_unit: Optional[str] = Field(
        default=None,
        description="Unit for reminder offset: day, week, or month.",
    )

    @validator("recurrence_interval_unit")
    def validate_recurrence_interval_unit_update(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate recurrence interval unit when provided on update.
        """

        if value is None:
            return None
        allowed = {"day", "week", "month", "year"}
        if value not in allowed:
            raise ValueError(f"Invalid recurrence_interval_unit. Allowed: {allowed}")
        return value

    @validator("reminder_before_unit")
    def validate_reminder_before_unit_update(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate reminder unit when provided on update.
        """

        if value is None:
            return None
        allowed = {"day", "week", "month"}
        if value not in allowed:
            raise ValueError(f"Invalid reminder_before_unit. Allowed: {allowed}")
        return value

    @validator("questions")
    def validate_question_order(cls, value: Optional[List[InspectionQuestionRequest]]) -> Optional[List[InspectionQuestionRequest]]:
        """
        Ensure question orders are unique when provided.
        """

        if value is None:
            return value
        orders = [q.order for q in value]
        if len(orders) != len(set(orders)):
            raise ValueError("Question order values must be unique.")
        return value

    @validator("status")
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """
        Ensure status is one of the allowed values.
        """

        if value is None:
            return value
        # Normalize the status value for comparison (case-insensitive, trim whitespace)
        normalized = value.strip() if isinstance(value, str) else str(value).strip()
        allowed = {"Unassigned", "In Progress", "Closed", "pending", "in_progress", "completed"}  # Support both old and new formats
        # Case-insensitive comparison
        if normalized.lower() not in {s.lower() for s in allowed}:
            raise ValueError(f"Invalid status. Allowed: Unassigned, In Progress, Closed")
        # Return normalized value (use new format)
        status_map = {
            "pending": "Unassigned",
            "in_progress": "In Progress",
            "completed": "Closed",
        }
        normalized_lower = normalized.lower()
        if normalized_lower in status_map:
            return status_map[normalized_lower]
        # If it's already in new format, return as-is (with proper casing)
        if normalized_lower == "unassigned":
            return "Unassigned"
        if normalized_lower == "in progress":
            return "In Progress"
        if normalized_lower == "closed":
            return "Closed"
        return normalized


class GetInspectionFormRequest(BaseModel):
    """
    Request payload for getting an inspection form by ID.
    """

    form_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Inspection form identifier.")


class DeleteInspectionFormRequest(BaseModel):
    """
    Request payload for deactivating an inspection form by ID.
    """

    form_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Inspection form identifier.")


class ListInspectionFormsRequest(BaseModel):
    """
    Query parameters for paginated inspection form listing.
    Vessel_id is optional - if provided, lists forms for that vessel.
    If not provided, lists all forms for the authenticated admin.
    """

    vessel_id: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        default=None, description="Optional vessel identifier to filter forms by vessel."
    )
    page: int = Field(default=1, ge=1, description="Page number (1-based).")
    limit: int = Field(default=20, ge=1, le=100, description="Number of forms per page.")
    search: Optional[str] = Field(default=None, description="Optional search term to filter by title or description.")


class ListSubmittedFormsRequest(BaseModel):
    """
    Query parameters for listing submitted (Closed) forms with answers.
    Allows filtering by inspector, crew, or vessel.
    """

    inspector_id: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        default=None, description="Optional inspector identifier to filter forms by inspector."
    )
    crew_id: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        default=None, description="Optional crew identifier to filter forms by crew member."
    )
    vessel_id: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        default=None, description="Optional vessel identifier to filter forms by vessel."
    )
    page: int = Field(default=1, ge=1, description="Page number (1-based).")
    limit: int = Field(default=20, ge=1, le=100, description="Number of forms per page.")


class InspectionAnswerRequest(BaseModel):
    """
    Represents a single answer provided for an inspection question.
    """

    order: int = Field(..., description="Order of the question being answered.")
    value: str = Field(..., description="Answer value (text, selected option label, or URL reference).")


class SubmitInspectionFormRequest(BaseModel):
    """
    Payload for submitting/filling an inspection form by an inspector or crew member.
    """

    form_id: constr(strip_whitespace=True, min_length=1) = Field(..., description="Inspection form identifier.")
    assignment_id: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        default=None,
        description="Optional assignment identifier if this submission is tied to a specific assignment.",
    )
    answers: List[InspectionAnswerRequest] = Field(
        ..., description="List of answers keyed by question order."
    )
    defects: Optional[List[int]] = Field(
        default=None,
        description="Optional list of question orders that are marked as defects.",
    )


