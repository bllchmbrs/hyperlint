# Technical Specification: MDX Support for Hyperlint

## Problem Statement
Hyperlint currently supports standard Markdown (`.md`) files but lacks support for MDX (`.mdx`), which combines Markdown with JSX components. This limits its usefulness for projects using MDX for documentation.

## Requirements

### Must-Have
1. Support `.mdx` file extensions in file processing
2. Preserve JSX components during linting/editing
3. Adapt existing rules to recognize and properly handle:
   - Import/export statements
   - JSX components
   - JavaScript expressions in curly braces
4. Allow Vale linting to work with MDX content

### Nice-to-Have
1. MDX-specific rules for component consistency
2. Special handling for component props validation

## Technical Approach

### File Type Detection
```python
def find_markdown_files(
    directory_path: Path,
    include_pattern: str = "*.{md,mdx}",  # Modified to include mdx
    exclude_patterns: List[str] | None = None,
) -> List[Path]:
    # Existing implementation...
```

### Content Parsing Modification
Add an MDX-aware parser that:
1. Identifies JSX/component blocks
2. Marks them as "protected regions"
3. Only applies text-related rules to Markdown portions

```python
class MDXParser:
    def __init__(self, content: str):
        self.content = content
        self.protected_regions = []
        self._identify_protected_regions()
        
    def _identify_protected_regions(self):
        # Logic to identify JSX components and expressions
        # Store their line ranges in self.protected_regions
        
    def is_protected_line(self, line_number: int) -> bool:
        # Check if line is within a protected region
```

### Editor Modifications
Extend `BaseEditor` to be MDX-aware:

```python
class BaseEditor(ABC, BaseModel):
    # Existing implementation...
    is_mdx: bool = False
    mdx_parser: Optional[MDXParser] = None
    
    def model_post_init(self, context: Any, /) -> None:
        # Determine if file is MDX based on extension
        self.is_mdx = self.path.suffix.lower() == ".mdx"
        if self.is_mdx:
            self.mdx_parser = MDXParser(self.get_text())
            
    def _approval_filter(self, issue, proposed_fix: str) -> bool:
        # Add MDX-specific checks before approving changes
        if self.is_mdx and self.mdx_parser:
            if self.mdx_parser.is_protected_line(issue.line):
                logger.warning(f"Skipping protected MDX line {issue.line}")
                return False
        # Rest of existing implementation...
```

## Implementation Plan
1. Add MDX file type detection
2. Create MDX parser for identifying protected regions
3. Modify `BaseEditor` to handle MDX files
4. Update Vale integration to skip JSX blocks
5. Add tests for MDX files

## Testing Strategy
1. Create test MDX files with various JSX patterns
2. Verify linting preserves JSX components
3. Test rule application on mixed MDX/Markdown content