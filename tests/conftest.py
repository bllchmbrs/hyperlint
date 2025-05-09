import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_markdown_file():
    """Creates a temporary markdown file for testing and cleans it up after the test."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Document\n\nThis is a test.")
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()

@pytest.fixture
def mock_ai_response():
    """Returns a mock AI response with line edits."""
    return {
        "line_edits": [
            {
                "starting_affected_line": 1,
                "ending_affected_line": 1,
                "issue_message": "Test issue",
                "resolution": "edit",
                "new_lines": ["# Test Document (Edited)"]
            }
        ]
    }

@pytest.fixture
def complex_markdown_file():
    """Creates a more complex temporary markdown file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# Sample Document

This is a test document with **bold** text.

## Section 1
- Item 1
- Item 2

Here's some code:
```python
print("Hello")
```
""")
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()