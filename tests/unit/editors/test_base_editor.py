from hyperlint.editors.core import (
    BaseEditor,
    DeleteLineIssue,
    InsertLineIssue,
    ReplaceLineFixableIssue,
)


class MockEditor(BaseEditor):
    """Mock implementation of BaseEditor for testing."""

    def prerun_checks(self) -> bool:
        return True

    def collect_issues(self) -> None:
        pass


class TestBaseEditor:
    """Tests for the BaseEditor class."""

    def test_get_text(self, temp_markdown_file):
        """Test that get_text properly loads file content."""
        editor = MockEditor(path=temp_markdown_file)

        text = editor.get_text()

        assert text == "# Test Document\n\nThis is a test."
        assert editor.text == text  # Should be cached

    def test_get_line_number_lookup(self, temp_markdown_file):
        """Test that get_line_number_lookup creates correct line mapping."""
        editor = MockEditor(path=temp_markdown_file)

        lookup = editor.get_line_number_lookup()

        assert lookup == {1: "# Test Document", 2: "", 3: "This is a test."}

    def test_get_text_with_line_numbers(self, temp_markdown_file):
        """Test that get_text_with_line_numbers correctly formats text with line numbers."""
        editor = MockEditor(path=temp_markdown_file)

        text_with_lines = editor.get_text_with_line_numbers()

        assert "1: # Test Document" in text_with_lines
        assert "2: " in text_with_lines
        assert "3: This is a test." in text_with_lines

    def test_add_replacement(self, temp_markdown_file):
        """Test that add_replacement correctly adds a replacement issue."""
        editor = MockEditor(path=temp_markdown_file)

        issue = ReplaceLineFixableIssue(
            line=1,
            issue_message=["Title should be more descriptive"],
            existing_content="# Test Document",
        )

        editor.add_replacement(issue)

        assert len(editor.replacements) == 1
        assert editor.replacements[0] == issue

    def test_add_insertion(self, temp_markdown_file):
        """Test that add_insertion correctly adds an insertion issue."""
        editor = MockEditor(path=temp_markdown_file)

        issue = InsertLineIssue(line=2, insert_content="This is an inserted line.")

        editor.add_insertion(issue)

        assert len(editor.insertions) == 1
        assert editor.insertions[0] == issue

    def test_add_deletion(self, temp_markdown_file):
        """Test that add_deletion correctly adds a deletion issue."""
        editor = MockEditor(path=temp_markdown_file)

        issue = DeleteLineIssue(
            line=3,
            issue_message=["This line should be removed"],
            existing_content="This is a test.",
        )

        editor.add_deletion(issue)

        assert len(editor.deletions) == 1
        assert editor.deletions[0] == issue

    def test_generate_v2_with_no_changes(self, temp_markdown_file):
        """Test that generate_v2 returns the original text when no issues are collected."""
        editor = MockEditor(path=temp_markdown_file)

        result = editor.generate_v2()

        assert result == "# Test Document\n\nThis is a test."

    def test_generate_v2_with_replacements(self, temp_markdown_file, monkeypatch):
        """Test that generate_v2 correctly applies replacements."""

        # Create a subclass that overrides collect_issues
        class TestEditor(MockEditor):
            def collect_issues(self) -> None:
                # Do nothing, we'll add issues manually
                pass

        editor = TestEditor(path=temp_markdown_file)

        # Mock the fix method to return a known value
        def mock_fix(self):
            return "# Enhanced Test Document"

        monkeypatch.setattr(ReplaceLineFixableIssue, "fix", mock_fix)

        # Add a replacement issue
        issue = ReplaceLineFixableIssue(
            line=1,
            issue_message=["Title should be more descriptive"],
            existing_content="# Test Document",
        )
        editor.add_replacement(issue)

        result = editor.generate_v2()

        assert result.startswith("# Enhanced Test Document")
        assert "This is a test." in result

    def test_generate_v2_with_insertions(self, temp_markdown_file):
        """Test that generate_v2 correctly applies insertions."""

        # Create a subclass that overrides collect_issues
        class TestEditor(MockEditor):
            def collect_issues(self) -> None:
                # Do nothing, we'll add issues manually
                pass

        editor = TestEditor(path=temp_markdown_file)

        # Add an insertion issue
        editor.add_insertion(
            InsertLineIssue(line=2, insert_content="This is an inserted line.")
        )

        result = editor.generate_v2()

        assert "# Test Document" in result
        assert "This is an inserted line." in result
        assert "This is a test." in result

    def test_generate_v2_with_deletions(self, temp_markdown_file):
        """Test that generate_v2 correctly applies deletions."""

        # Create a subclass that overrides collect_issues
        class TestEditor(MockEditor):
            def collect_issues(self) -> None:
                # Do nothing, we'll add issues manually
                pass

        editor = TestEditor(path=temp_markdown_file)

        # Add a deletion issue
        editor.add_deletion(
            DeleteLineIssue(
                line=3,
                issue_message=["This line should be removed"],
                existing_content="This is a test.",
            )
        )

        result = editor.generate_v2()

        assert "# Test Document" in result
        assert "This is a test." not in result

    def test_generate_v2_with_mixed_changes(self, complex_markdown_file, monkeypatch):
        """Test that generate_v2 correctly applies mixed changes (replace, insert, delete)."""

        # Create a subclass that overrides collect_issues
        class TestEditor(MockEditor):
            def collect_issues(self) -> None:
                # Do nothing, we'll add issues manually
                pass

        editor = TestEditor(path=complex_markdown_file)

        # Mock the fix method to return a known value
        def mock_fix(self):
            return (
                "# Improved Sample Document"
                if self.line == 1
                else self.existing_content
            )

        monkeypatch.setattr(ReplaceLineFixableIssue, "fix", mock_fix)

        # Add various issues
        editor.add_replacement(
            ReplaceLineFixableIssue(
                line=1,
                issue_message=["Title should be more descriptive"],
                existing_content="# Sample Document",
            )
        )
        editor.add_insertion(
            InsertLineIssue(line=3, insert_content="This is a newly inserted line.")
        )
        editor.add_deletion(
            DeleteLineIssue(
                line=5,
                issue_message=["This section heading should be removed"],
                existing_content="## Section 1",
            )
        )

        result = editor.generate_v2()

        # Check replacements
        assert "# Improved Sample Document" in result
        assert "# Sample Document" not in result

        # Check insertions
        assert "This is a newly inserted line." in result

        # Check deletions
        assert "## Section 1" not in result

        # Make sure other content is preserved
        assert "This is a test document with **bold** text." in result
        assert "- Item 1" in result
