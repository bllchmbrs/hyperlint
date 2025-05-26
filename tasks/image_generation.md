# MediaGenerator Abstract Class Specification

## Problem Statement
Content creators need programmatic generation of visual assets (images, diagrams) with iterative refinement capabilities. Current solutions lack unified interfaces and approval tracking for tuning generation algorithms over time.

## Target Users
- Content developers integrating media generation into markdown tooling
- Technical writers needing diagrams and illustrations
- Developers extending the system with new media types

## Core Functionality

### `MediaGenerator` Abstract Base Class
```python
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
```

### Supporting Models

```python
class MediaGenerationResult(BaseModel):
    """Result from a media generation attempt"""
    file_path: str
    prompt: str
    task:str
    approved: bool
    feedback: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class MediaApproval(ApprovalRequest):
    """Approval record for generated media"""
    original_prompt: str
    refined_prompt: str
    context_text: str
    media_type: str
    approved: bool
    feedback: Optional[str] = None
    
class MediaApprovalLog(ApprovalLog):
    """Logging system for media generation approvals"""
    def get_log_file_path(self) -> Path:
        """Get path to media approval log file"""
        return self.config.get_judge_data_dir() / "media_approvals.jsonl"
        
    def prompt_for_approval(self, approval_request: MediaApproval) -> bool:
        """Display media and prompt for approval"""
        # Implementation details
```

## Implementations

### Image Generator

```python
class ImageGenerator(MediaGenerator):
    """Implementation for generating images from text"""
    
    def generate(self) -> List[str]:
        """Generate images"""
        # Implementation details
        pass
```

### Mermaid Diagram Generator

```python
class MermaidDiagramGenerator(MediaGenerator):
    """Implementation for generating Mermaid diagrams from text"""
    
    def generate(self) -> List[str]:
        """Generate Mermaid diagrams"""
        # Implementation details
        pass
```
