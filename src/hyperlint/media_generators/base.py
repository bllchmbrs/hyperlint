from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MediaGenerator(ABC):
    """Abstract base class for generating media content with iterative user feedback."""

    @abstractmethod
    def generate(self) -> List[str]:
        """
        Generate media content.

        Returns:
            List[str]: Paths to generated content files
        """
        pass

class MediaGenerationResult(BaseModel):
    """Result from a media generation attempt"""
    file_path: str
    prompt: str
    task: str
    approved: bool
    feedback: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
