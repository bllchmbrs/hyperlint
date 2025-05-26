from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

class ApprovalRequest(BaseModel):
    """Base class for approval requests. Placeholder definition."""
    # Add common fields for approval requests here if any become apparent.
    pass

class MediaGenerationResult(BaseModel):
    """Result from a media generation attempt"""
    file_path: str
    prompt: str
    task: str # Describes the task that led to this generation
    approved: bool
    feedback: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MediaApproval(ApprovalRequest):
    """Approval record for generated media"""
    file_path: str # Ensure this field is present
    original_prompt: str
    refined_prompt: str
    context_text: str # Text that provided context for the media
    media_type: str # e.g., 'image', 'diagram'
    approved: bool
    feedback: Optional[str] = None
    # Consider adding file_path if directly relevant to the approval record itself
