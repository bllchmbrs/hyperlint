import tempfile
from pathlib import Path

import pytest
from hyperlint.editors.core import BaseEditor, ReplaceLineFixableIssue
from hyperlint.config import SimpleConfig


class TestMDXEditor(BaseEditor):
    """Test implementation of BaseEditor for testing MDX functionality."""
    
    def prerun_checks(self) -> bool:
        return True
    
    def collect_issues(self) -> None:
        """Add test issues for testing."""
        # Add issues to various lines for testing
        line_lookup = self.get_line_number_lookup()
        
        for line_num, content in line_lookup.items():
            if content.strip():  # Skip empty lines
                self.add_replacement(ReplaceLineFixableIssue(
                    line=line_num,
                    issue_message=["Test issue"],
                    existing_content=content
                ))


class TestMDXIntegration:
    
    def test_mdx_file_detection(self):
        """Test that MDX files are properly detected."""
        mdx_content = """# Title
import { Button } from './Button'
<Button>Click</Button>
"""
        
        with tempfile.NamedTemporaryFile(suffix=".mdx", mode="w", delete=False) as f:
            f.write(mdx_content)
            mdx_path = Path(f.name)
        
        try:
            editor = TestMDXEditor(path=mdx_path, config=SimpleConfig())
            assert editor.is_mdx is True
            assert editor.mdx_parser is not None
        finally:
            mdx_path.unlink()
    
    def test_md_file_detection(self):
        """Test that regular MD files are not treated as MDX."""
        md_content = """# Title
Regular markdown content.
"""
        
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write(md_content)
            md_path = Path(f.name)
        
        try:
            editor = TestMDXEditor(path=md_path, config=SimpleConfig())
            assert editor.is_mdx is False
            assert editor.mdx_parser is None
        finally:
            md_path.unlink()
    
    def test_mdx_protected_line_filtering(self):
        """Test that issues in MDX protected lines are filtered out."""
        mdx_content = """# Title

import { Button } from './Button'

Regular markdown paragraph.

<Button onClick={() => console.log('test')}>
  Click me
</Button>

Another paragraph.

export default Button
"""
        
        with tempfile.NamedTemporaryFile(suffix=".mdx", mode="w", delete=False) as f:
            f.write(mdx_content)
            mdx_path = Path(f.name)
        
        try:
            config = SimpleConfig()
            config.dry_run = True  # Enable dry run to avoid approval prompts
            
            editor = TestMDXEditor(path=mdx_path, config=config)
            editor.collect_issues()
            
            # Test that issues are created
            assert len(editor.replacements) > 0
            
            # Test the approval filter for protected lines
            import_issue = ReplaceLineFixableIssue(
                line=3,  # import line
                issue_message=["Test issue"],
                existing_content="import { Button } from './Button'"
            )
            
            regular_issue = ReplaceLineFixableIssue(
                line=5,  # regular markdown line
                issue_message=["Test issue"],
                existing_content="Regular markdown paragraph."
            )
            
            # Import line should be filtered out
            assert not editor._approval_filter(import_issue, "fixed content")
            
            # Regular markdown line should be approved
            assert editor._approval_filter(regular_issue, "fixed content")
            
        finally:
            mdx_path.unlink()
    
    def test_mdx_component_line_filtering(self):
        """Test that JSX component lines are properly filtered."""
        mdx_content = """<CustomComponent prop="value">
  Content inside component
</CustomComponent>

Regular paragraph after component.
"""
        
        with tempfile.NamedTemporaryFile(suffix=".mdx", mode="w", delete=False) as f:
            f.write(mdx_content)
            mdx_path = Path(f.name)
        
        try:
            config = SimpleConfig()
            config.dry_run = True
            
            editor = TestMDXEditor(path=mdx_path, config=config)
            
            # Test component lines are protected
            component_start = ReplaceLineFixableIssue(
                line=1,
                issue_message=["Test issue"],
                existing_content='<CustomComponent prop="value">'
            )
            
            component_content = ReplaceLineFixableIssue(
                line=2,
                issue_message=["Test issue"],
                existing_content="  Content inside component"
            )
            
            component_end = ReplaceLineFixableIssue(
                line=3,
                issue_message=["Test issue"],
                existing_content="</CustomComponent>"
            )
            
            regular_paragraph = ReplaceLineFixableIssue(
                line=5,
                issue_message=["Test issue"],
                existing_content="Regular paragraph after component."
            )
            
            # Component lines should be filtered out
            assert not editor._approval_filter(component_start, "fixed")
            assert not editor._approval_filter(component_content, "fixed")
            assert not editor._approval_filter(component_end, "fixed")
            
            # Regular paragraph should be approved
            assert editor._approval_filter(regular_paragraph, "fixed")
            
        finally:
            mdx_path.unlink()