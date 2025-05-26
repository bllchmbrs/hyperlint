# Project Specification: Streamlit Issue Review Interface

## Objective
Create a Streamlit-based interface for reviewing and approving document changes that replaces the CLI approval system while collecting structured data for ML training.

## Core Requirements

1. **Integration with Existing Architecture**
   - Extend the `EditorApprovalLog` class with a new `StreamlitApprovalLog` implementation
   - Maintain compatibility with existing issue types (ReplaceLineFixableIssue, DeleteLineIssue, InsertLineIssue)
   - Save decisions in the same format for ML training dataset

2. **User Interface Components**
   - File/rule selection screen
   - Change-by-change review interface
   - Session progress tracking
   - Decision collection (approve/reject/unsure)

3. **Data Collection**
   - Store all decisions with metadata in the existing log format
   - Capture optional reviewer explanations for ML features
   - Track decision metrics (time spent, consistency)

## Implementation Architecture

### 1. Entry Point
```python
# app.py
import streamlit as st
from hyperlint.approval import get_approval_log
from hyperlint.config import load_config
from streamlit_approval import StreamlitApprovalLog

def main():
    st.title("Hyperlint Review Interface")
    # File selection, configuration loading
    # Session management
```

### 2. Approval Log Extension
```python
# streamlit_approval.py
from hyperlint.approval import EditorApprovalLog, EditorApprovalRequest
import streamlit as st

class StreamlitApprovalLog(EditorApprovalLog):
    def prompt_for_approval(self, approval_request: EditorApprovalRequest) -> bool:
        # Implement Streamlit-based approval UI
        # Return approval decision
        pass
    
    def get_log_file_path(self) -> Path:
        # Use same log path as existing implementation
        pass
```

### 3. Session Management
```python
# session.py
def initialize_session(file_path, rules_dir):
    # Set up editor, collect issues
    # Store in session state
    
def get_next_issue():
    # Return the next issue for review
    
def save_decision(issue_id, decision, explanation):
    # Log decision for ML training data
```

### 4. Data Structures
Extend existing approval log format:
```json
{
  "file_path": "test.md",
  "issue_type": "replace",
  "line": 24,
  "issue_messages": "Convert passive voice to active voice",
  "existing_content": "The data was processed by our system.",
  "replacement_content": "Our system processed the data.",
  "approved": true,
  "explanation": "Clearer and more direct",
  "decision_time": 4.2,
  "date": "2025-05-16T14:32:10.243Z"
}
```

## Integration Points

1. **Configuration**
   - Add `approval_type: "streamlit"` option to configuration
   - Update `get_approval_log()` factory function to return StreamlitApprovalLog

2. **Editor Interface**
   - Maintain existing editor classes (RulesEditor, ValeEditor)
   - Pass collected issues to Streamlit interface for review

3. **CLI Integration**
   - Add `--interface streamlit` option to CLI commands
   - Launch Streamlit server when selected

## Testing Strategy
- Unit tests for StreamlitApprovalLog implementation
- Integration tests for end-to-end workflow with mock data
- Validation of log format compatibility with existing systems

This implementation maintains the core architecture while providing a modern UI for the review process, focusing specifically on collecting high-quality labeled data for ML model training.