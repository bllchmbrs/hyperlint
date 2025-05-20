import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from hyperlint.approval import MediaApproval, MediaApprovalLog, ApprovalRequest
from hyperlint.config import SimpleConfig
from rich.console import Console # For mocking input
from rich.panel import Panel # Potentially for mocking

class TestMediaApproval:
    def test_media_approval_creation(self):
        """Test successful creation of a MediaApproval instance."""
        file_path = Path("/fake/path/to/media.png")
        approval_data = {
            "original_prompt": "A cat playing a piano",
            "refined_prompt": "A fluffy ginger cat playing a grand piano in a sunlit room",
            "context_text": "The user wants a whimsical image for their blog post about music.",
            "media_type": "image",
            "file_path": file_path,
            "approved": False, # Default for the request object before decision
            "feedback": None,
        }
        media_approval = MediaApproval(**approval_data)

        assert media_approval.original_prompt == approval_data["original_prompt"]
        assert media_approval.refined_prompt == approval_data["refined_prompt"]
        assert media_approval.context_text == approval_data["context_text"]
        assert media_approval.media_type == approval_data["media_type"]
        assert media_approval.file_path == file_path
        assert isinstance(media_approval.file_path, Path)
        assert media_approval.approved == approval_data["approved"]
        assert media_approval.feedback is None

    def test_media_approval_path_serialization(self):
        """Test that Path object is serialized to string in model_dump."""
        file_path = Path("/fake/path/to/media.png")
        media_approval = MediaApproval(
            original_prompt="prompt",
            refined_prompt="refined_prompt",
            context_text="context",
            media_type="image",
            file_path=file_path,
            approved=True,
        )
        
        dumped_model = media_approval.model_dump()
        assert dumped_model["file_path"] == str(file_path)
        assert isinstance(dumped_model["file_path"], str)

        # Test JSON serialization as well, as this is a common use case
        dumped_json = media_approval.model_dump_json()
        # In JSON, it will be a string: "/fake/path/to/media.png"
        # We need to ensure it's correctly quoted in the JSON string
        assert f'"file_path": "{str(file_path).replace("\\", "\\\\")}"' in dumped_json


class TestMediaApprovalLog:
    @pytest.fixture
    def mock_config(self):
        """Fixture for a mock SimpleConfig."""
        mock_config = MagicMock(spec=SimpleConfig)
        mock_judge_dir = MagicMock(spec=Path)
        mock_config.get_judge_data_dir.return_value = mock_judge_dir
        # Mock ensure_storage_dirs as it's called in get_log_file_path and log_decision
        mock_config.ensure_storage_dirs = MagicMock()
        return mock_config

    @pytest.fixture
    def media_approval_request_data(self):
        """Fixture for sample MediaApproval data for the request."""
        return {
            "original_prompt": "A dog surfing",
            "refined_prompt": "A golden retriever surfing a big wave",
            "context_text": "For a summer campaign",
            "media_type": "image",
            "file_path": Path("/fake/image.jpg"),
            # 'approved' and 'feedback' are not part of the initial request to prompt_for_approval
            # but MediaApproval requires 'approved'. We will use a version of MediaApproval
            # that doesn't have `approved` for the request, or pass it as a dict.
            # For simplicity in the test, we'll construct MediaApproval with a default approved=False
        }

    def test_get_log_file_path(self, mock_config):
        """Test that get_log_file_path returns the correct path."""
        log = MediaApprovalLog(config=mock_config)
        expected_path = mock_config.get_judge_data_dir.return_value / "media_approvals.jsonl"
        
        actual_path = log.get_log_file_path()
        
        mock_config.ensure_storage_dirs.assert_called_once()
        assert actual_path == expected_path

    @patch('hyperlint.approval.Console') # To mock Console().input
    @patch('hyperlint.approval.Panel')    # To check if Panel is called
    def test_prompt_for_approval_yes(self, mock_panel_constructor, mock_console_class, mock_config, media_approval_request_data):
        """Test prompt_for_approval with 'y' input."""
        # Setup mock for Console().input
        mock_console_instance = MagicMock()
        mock_console_instance.input.return_value = "y"
        mock_console_class.return_value = mock_console_instance

        log = MediaApprovalLog(config=mock_config)
        # Mock log_decision directly on the instance
        log.log_decision = MagicMock()

        # Create a MediaApproval instance for the request
        # The 'approved' field is part of MediaApproval, but for a request coming into prompt_for_approval,
        # it wouldn't have a decision yet. The implementation creates a new MediaApproval object with the decision.
        # We give it a default approved=False for the input object.
        request_obj = MediaApproval(**media_approval_request_data, approved=False)

        result = log.prompt_for_approval(request_obj)

        assert result is True
        mock_panel_constructor.fit.assert_called_once() # Check Panel.fit was called
        log.log_decision.assert_called_once()
        
        # Check the argument passed to log_decision
        logged_approval = log.log_decision.call_args[0][0]
        assert isinstance(logged_approval, MediaApproval)
        assert logged_approval.approved is True
        assert logged_approval.file_path == request_obj.file_path # Ensure other data is preserved

    @patch('hyperlint.approval.Console')
    @patch('hyperlint.approval.Panel')
    def test_prompt_for_approval_no(self, mock_panel_constructor, mock_console_class, mock_config, media_approval_request_data):
        """Test prompt_for_approval with 'n' input."""
        mock_console_instance = MagicMock()
        mock_console_instance.input.return_value = "n"
        mock_console_class.return_value = mock_console_instance

        log = MediaApprovalLog(config=mock_config)
        log.log_decision = MagicMock()
        
        request_obj = MediaApproval(**media_approval_request_data, approved=False)

        result = log.prompt_for_approval(request_obj)

        assert result is False
        mock_panel_constructor.fit.assert_called_once()
        log.log_decision.assert_called_once()
        
        logged_approval = log.log_decision.call_args[0][0]
        assert isinstance(logged_approval, MediaApproval)
        assert logged_approval.approved is False
        assert logged_approval.file_path == request_obj.file_path
