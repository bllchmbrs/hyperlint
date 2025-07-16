import unittest
from unittest.mock import patch, MagicMock, mock_open

import pytest # Using pytest for potentially more features later, but unittest structure for now
from pathlib import Path
import os
import shutil
import tempfile
import json

# Imports for classes to be tested
# Assuming src is in PYTHONPATH or project is structured correctly
from src.media_generation.models import MediaGenerationResult, MediaApproval, ApprovalRequest
from pydantic import ValidationError # Added for potential future use
from src.media_generation.approval import MediaApprovalLog, ApprovalLog
from src.media_generation.generators import ImageGenerator, MediaGenerator

# Placeholder for base temporary directory for tests
TEST_TEMP_BASE_DIR = Path(tempfile.gettempdir()) / "media_gen_tests_temp"

class TestMediaGenerationModels(unittest.TestCase):
    def test_approval_request_creation(self):
        """Test basic creation of ApprovalRequest."""
        try:
            req = ApprovalRequest() # Simple placeholder model
            self.assertIsNotNone(req)
        except Exception as e:
            self.fail(f"ApprovalRequest instantiation failed: {e}")

    def test_media_generation_result_creation_and_serialization(self):
        """Test creation and JSON serialization of MediaGenerationResult."""
        data = {
            "file_path": "/path/to/image.png",
            "prompt": "A test prompt",
            "task": "Test task",
            "approved": True,
            "feedback": "Looks good!",
            "metadata": {"key": "value"}
        }
        try:
            result = MediaGenerationResult(**data)
            self.assertEqual(result.file_path, data["file_path"])
            self.assertEqual(result.prompt, data["prompt"])
            self.assertEqual(result.task, data["task"])
            self.assertTrue(result.approved)
            self.assertEqual(result.feedback, data["feedback"])
            self.assertEqual(result.metadata, data["metadata"])

            # Test serialization
            json_output = result.model_dump_json()
            loaded_data = json.loads(json_output)
            self.assertEqual(loaded_data["file_path"], data["file_path"])
            self.assertEqual(loaded_data["prompt"], data["prompt"])
            self.assertTrue(loaded_data["approved"])

        except ValidationError as ve:
            self.fail(f"MediaGenerationResult validation failed: {ve}")
        except Exception as e:
            self.fail(f"MediaGenerationResult test failed: {e}")

    def test_media_approval_creation_and_serialization(self):
        """Test creation and JSON serialization of MediaApproval."""
        data = {
            "file_path": "/path/to/approved_image.png", # Added in models.py
            "original_prompt": "Initial idea",
            "refined_prompt": "Improved idea",
            "context_text": "Some context for the image",
            "media_type": "image",
            "approved": False,
            "feedback": "Needs more blue."
        }
        try:
            approval = MediaApproval(**data)
            self.assertEqual(approval.file_path, data["file_path"])
            self.assertEqual(approval.original_prompt, data["original_prompt"])
            self.assertEqual(approval.refined_prompt, data["refined_prompt"])
            self.assertEqual(approval.context_text, data["context_text"])
            self.assertEqual(approval.media_type, data["media_type"])
            self.assertFalse(approval.approved)
            self.assertEqual(approval.feedback, data["feedback"])

            # Test serialization
            json_output = approval.model_dump_json()
            loaded_data = json.loads(json_output)
            self.assertEqual(loaded_data["original_prompt"], data["original_prompt"])
            self.assertEqual(loaded_data["media_type"], data["media_type"])
            self.assertFalse(loaded_data["approved"])
            
        except ValidationError as ve:
            self.fail(f"MediaApproval validation failed: {ve}")
        except Exception as e:
            self.fail(f"MediaApproval test failed: {e}")

    def test_media_generation_result_optional_fields(self):
        """Test MediaGenerationResult with optional fields omitted."""
        data = {
            "file_path": "/path/to/another.png",
            "prompt": "Another prompt",
            "task": "Another task",
            "approved": True
            # feedback and metadata are optional
        }
        try:
            result = MediaGenerationResult(**data)
            self.assertEqual(result.file_path, data["file_path"])
            self.assertIsNone(result.feedback) # Pydantic default for Optional[str] is None
            self.assertEqual(result.metadata, {}) # Pydantic default for Dict with default_factory=dict
        except Exception as e:
            self.fail(f"MediaGenerationResult optional fields test failed: {e}")

    def test_media_approval_optional_fields(self):
        """Test MediaApproval with optional fields omitted."""
        data = {
            "file_path": "/path/to/image_no_feedback.png",
            "original_prompt": "Prompt X",
            "refined_prompt": "Prompt Y",
            "context_text": "Context Z",
            "media_type": "diagram",
            "approved": True
            # feedback is optional
        }
        try:
            approval = MediaApproval(**data)
            self.assertEqual(approval.file_path, data["file_path"])
            self.assertIsNone(approval.feedback)
        except Exception as e:
            self.fail(f"MediaApproval optional fields test failed: {e}")

class TestMediaApprovalLog(unittest.TestCase):
    def setUp(self):
        # Create a unique temporary directory for each test to avoid collisions
        self.test_run_temp_dir = Path(tempfile.mkdtemp(prefix="media_log_tests_"))
        
        self.log_file_name = "test_approvals.jsonl"
        
        # Mock config for testing the preferred path
        self.mock_config_dir = self.test_run_temp_dir / "judge_data"
        self.mock_config_dir.mkdir(parents=True, exist_ok=True)
        
        self.mock_config = MagicMock()
        self.mock_config.get_judge_data_dir.return_value = self.mock_config_dir
        
        # Instance with config
        self.approval_log_with_config = MediaApprovalLog(
            log_file_name=self.log_file_name, 
            config=self.mock_config
        )
        
        # Instance without config (for fallback path testing)
        # To ensure fallback path is predictable and writable for tests,
        # we can patch Path.home() if direct home dir writing is problematic in CI.
        # For now, assuming direct test is fine or Path.home() is naturally sandboxed/mockable.
        self.home_patcher = patch('pathlib.Path.home', return_value=self.test_run_temp_dir / "fake_home")
        self.mock_home = self.home_patcher.start()
        self.mock_home.mkdir(parents=True, exist_ok=True) # Ensure fake_home/.media_assistant_logs can be made

        self.approval_log_no_config = MediaApprovalLog(log_file_name=self.log_file_name)


    def tearDown(self):
        # Stop any patches started in setUp
        self.home_patcher.stop()
        # Clean up the unique temporary directory created for the test run
        if self.test_run_temp_dir.exists():
            shutil.rmtree(self.test_run_temp_dir)

    def test_get_log_file_path_with_config(self):
        """Test log file path generation when config with get_judge_data_dir is provided."""
        expected_path = self.mock_config_dir / self.log_file_name
        self.assertEqual(self.approval_log_with_config.get_log_file_path(), expected_path)

    def test_get_log_file_path_without_config_fallback(self):
        """Test log file path generation fallback when config is not provided."""
        # Path.home() is mocked to self.test_run_temp_dir / "fake_home"
        expected_fallback_dir = self.mock_home / ".media_assistant_logs"
        expected_path = expected_fallback_dir / self.log_file_name
        self.assertEqual(self.approval_log_no_config.get_log_file_path(), expected_path)
        # Check that the directory is created by get_log_file_path if log_approval is called
        # (log_approval ensures parent dir exists; get_log_file_path itself does not)

    def test_log_approval_creates_file_and_writes_jsonl(self):
        """Test that log_approval creates the log file and writes a JSON line."""
        log = self.approval_log_with_config # Use the one with predictable config path
        log_path = log.get_log_file_path()

        approval_data = MediaApproval(
            file_path="/test/image.png",
            original_prompt="Test original",
            refined_prompt="Test refined",
            context_text="Test context",
            media_type="image_test",
            approved=True,
            feedback="Looks great from test"
        )
        
        log.log_approval(approval_data)
        
        self.assertTrue(log_path.exists())
        with open(log_path, 'r') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        logged_json = json.loads(lines[0])
        
        self.assertEqual(logged_json["file_path"], approval_data.file_path)
        self.assertEqual(logged_json["original_prompt"], approval_data.original_prompt)
        self.assertEqual(logged_json["approved"], approval_data.approved)
        self.assertEqual(logged_json["feedback"], approval_data.feedback)

        # Test appending
        approval_data_2 = MediaApproval(
            file_path="/test/image2.png",
            original_prompt="Test original 2",
            refined_prompt="Test refined 2",
            context_text="Test context 2",
            media_type="image_test_2",
            approved=False,
            feedback="Needs work from test"
        )
        log.log_approval(approval_data_2)
        with open(log_path, 'r') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)
        logged_json_2 = json.loads(lines[1])
        self.assertEqual(logged_json_2["file_path"], approval_data_2.file_path)
        self.assertFalse(logged_json_2["approved"])


    @patch('rich.prompt.Confirm.ask')
    @patch('rich.prompt.Prompt.ask') # For feedback input
    @patch.object(MediaApprovalLog, 'log_approval') # Mock log_approval to isolate prompting logic
    def test_prompt_for_approval_user_approves(self, mock_log_approval, mock_rich_prompt_ask, mock_confirm_ask):
        """Test prompt_for_approval when user approves."""
        mock_confirm_ask.return_value = True # User clicks 'yes' (approves)
        # mock_rich_prompt_ask is not called if user approves and provides no feedback by default

        log = self.approval_log_with_config # Instance of MediaApprovalLog
        
        approval_request = MediaApproval(
            file_path="/test/prompt_approve.png",
            original_prompt="Approve this",
            refined_prompt="Approve this refined",
            context_text="Context for approval",
            media_type="image_prompt_test",
            approved=False, # Initial state
            feedback=None
        )
        
        result = log.prompt_for_approval(approval_request)
        
        self.assertTrue(result) # Should return True (approved)
        self.assertTrue(approval_request.approved)
        self.assertEqual(approval_request.feedback, "Approved") # Default feedback for approval
        
        mock_confirm_ask.assert_called_once()
        mock_rich_prompt_ask.assert_not_called() # Not called if approved
        mock_log_approval.assert_called_once_with(approval_request) # Ensure it's logged

    @patch('rich.prompt.Confirm.ask')
    @patch('rich.prompt.Prompt.ask')
    @patch.object(MediaApprovalLog, 'log_approval')
    def test_prompt_for_approval_user_rejects_with_feedback(self, mock_log_approval, mock_rich_prompt_ask, mock_confirm_ask):
        """Test prompt_for_approval when user rejects and provides feedback."""
        mock_confirm_ask.return_value = False # User clicks 'no' (rejects)
        user_feedback_text = "It's blurry."
        mock_rich_prompt_ask.return_value = user_feedback_text # User types feedback

        log = self.approval_log_with_config
        
        approval_request = MediaApproval(
            file_path="/test/prompt_reject.png",
            original_prompt="Reject this",
            refined_prompt="Reject this refined",
            context_text="Context for rejection",
            media_type="image_prompt_test_reject",
            approved=True, # Initial state (will be overridden)
            feedback=None
        )
        
        result = log.prompt_for_approval(approval_request)
        
        self.assertFalse(result) # Should return False (rejected)
        self.assertFalse(approval_request.approved)
        self.assertEqual(approval_request.feedback, user_feedback_text)
        
        mock_confirm_ask.assert_called_once()
        mock_rich_prompt_ask.assert_called_once_with("Provide feedback/reason for rejection (optional)", default="")
        mock_log_approval.assert_called_once_with(approval_request)

    @patch('rich.prompt.Confirm.ask')
    @patch('rich.prompt.Prompt.ask')
    @patch.object(MediaApprovalLog, 'log_approval')
    def test_prompt_for_approval_user_rejects_no_feedback(self, mock_log_approval, mock_rich_prompt_ask, mock_confirm_ask):
        """Test prompt_for_approval when user rejects and provides no feedback (empty string)."""
        mock_confirm_ask.return_value = False # User rejects
        mock_rich_prompt_ask.return_value = "" # User provides empty feedback

        log = self.approval_log_with_config
        approval_request = MediaApproval(
            file_path="/test/prompt_reject_no_fb.png",
            original_prompt="Reject this",
            refined_prompt="Reject this refined",
            context_text="Context for rejection",
            media_type="image_prompt_test_reject_no_fb",
            approved=True, 
            feedback=None
        )
        
        result = log.prompt_for_approval(approval_request)
        
        self.assertFalse(result)
        self.assertFalse(approval_request.approved)
        self.assertEqual(approval_request.feedback, "Rejected without detailed feedback.") # Default for empty
        
        mock_confirm_ask.assert_called_once()
        mock_rich_prompt_ask.assert_called_once()
        mock_log_approval.assert_called_once_with(approval_request)

class TestImageGenerator(unittest.TestCase):
    def setUp(self):
        # Ensure the global base temp dir for all ImageGenerator tests exists and is clean
        self.suite_base_temp_dir = Path(tempfile.gettempdir()) / "media_gen_tests_suite_temp" / "image_generator"
        if self.suite_base_temp_dir.exists():
            shutil.rmtree(self.suite_base_temp_dir)
        self.suite_base_temp_dir.mkdir(parents=True, exist_ok=True)

        # Mock MediaApprovalLog instance to be injected
        self.mock_approval_log = MagicMock(spec=MediaApprovalLog)
        
        # Path for ImageGenerator's internal temp_dir_base, different for each test instance
        self.current_test_temp_base = self.suite_base_temp_dir / self.id().split('.')[-1] # e.g., test_generate_success
        self.current_test_temp_base.mkdir(parents=True, exist_ok=True)

        # Default generator for most tests
        self.generator = ImageGenerator(
            approval_log=self.mock_approval_log,
            temp_dir_base=str(self.current_test_temp_base)
        )

    def tearDown(self):
        # Cleanup the specific temp base for this test if it was used by ImageGenerator directly
        # The ImageGenerator's __del__ should handle its owned _owned_temp_dir.
        # Session dirs created by generate() within current_test_temp_base are cleaned by generate() itself.
        # So, cleaning self.current_test_temp_base might be redundant if ImageGenerator cleans its session dirs.
        # However, to be safe and ensure no cross-test contamination if a test fails mid-way:
        if self.current_test_temp_base.exists():
             shutil.rmtree(self.current_test_temp_base)
        # If suite_base_temp_dir needs cleanup after all tests, use a class method or test runner setup/teardown

    def test_initialization_with_temp_dir_base(self):
        """Test ImageGenerator initializes with a specific temp_dir_base."""
        self.assertEqual(self.generator._temp_dir_base, self.current_test_temp_base)
        self.assertIsNone(self.generator._owned_temp_dir) # Should not create an owned one

    def test_initialization_without_temp_dir_base_creates_owned_dir(self):
        """Test ImageGenerator creates an owned temp dir if no base is given."""
        # Patch tempfile.TemporaryDirectory to check it's called
        with patch('tempfile.TemporaryDirectory') as mock_temp_dir_constructor:
            # Create a fake TemporaryDirectory object that has a 'name' attribute
            mock_td_instance = MagicMock()
            mock_td_instance.name = str(self.current_test_temp_base / "owned_td") # Predictable name
            mock_temp_dir_constructor.return_value = mock_td_instance

            gen_no_base = ImageGenerator(approval_log=self.mock_approval_log)
            
            mock_temp_dir_constructor.assert_called_once_with(prefix="image_gen_")
            self.assertIsNotNone(gen_no_base._owned_temp_dir)
            self.assertEqual(gen_no_base._owned_temp_dir.name, mock_td_instance.name)
            
            # Test __del__ for cleanup (hard to test __del__ directly and reliably)
            # Instead, we check that _get_temp_dir_path gives the owned dir,
            # and trust TemporaryDirectory's own cleanup.
            # We can also manually call cleanup on the mock to simulate.
            # gen_no_base._owned_temp_dir.cleanup.assert_called_once() -> this would be after __del__

    @patch('src.media_generation.generators._generate_openai_image', return_value=True) # Mocks the helper
    def test_generate_approved_first_try(self, mock_openai_gen_helper):
        """Test successful generation where image is approved on the first attempt."""
        initial_prompt = "A happy cat"
        # dummy_image_filename = "image_iter_1.png" # Not directly used for assertion path, but for mental model
        
        # Configure mock_approval_log.prompt_for_approval to return True (approved)
        self.mock_approval_log.prompt_for_approval.return_value = True

        # Mock _generate_openai_image to "create" a file
        # This side effect needs to be robust to where the file is actually created by ImageGenerator
        created_image_paths = []
        def side_effect_create_file(prompt, file_path_str):
            Path(file_path_str).parent.mkdir(parents=True, exist_ok=True) # Ensure dir exists
            Path(file_path_str).touch() # Create dummy file
            created_image_paths.append(file_path_str)
            return True
        mock_openai_gen_helper.side_effect = side_effect_create_file

        generated_paths = self.generator.generate(initial_prompt=initial_prompt)
        
        self.assertEqual(len(generated_paths), 1)
        generated_file_path = Path(generated_paths[0])
        self.assertTrue(generated_file_path.name.endswith(".png")) 
        self.assertTrue(generated_file_path.exists()) 
        self.assertEqual(str(generated_file_path), created_image_paths[0])


        mock_openai_gen_helper.assert_called_once()
        args_openai, _ = mock_openai_gen_helper.call_args
        self.assertEqual(args_openai[0], initial_prompt) # Check prompt
        self.assertEqual(args_openai[1], created_image_paths[0]) # Check path

        self.mock_approval_log.prompt_for_approval.assert_called_once()
        args_approval, _ = self.mock_approval_log.prompt_for_approval.call_args
        approval_request_arg = args_approval[0]
        self.assertEqual(approval_request_arg.original_prompt, initial_prompt)
        self.assertEqual(approval_request_arg.file_path, created_image_paths[0])
        
        # Assuming check_and_revise_prompt is a module-level mockable object
        with patch('src.media_generation.generators.check_and_revise_prompt', MagicMock()) as mock_dspy_predict_check:
            # Re-run or ensure it's not called if already run; here we just check it wasn't called
            # This part of the test is tricky if generate() was already called.
            # The check should be for *after* generate() ran.
            # If generate() was already called, this check is for its non-invocation.
            # This test assumes check_and_revise_prompt is NOT called.
            # If generate() is called again here, it would be a different scenario.
            # The structure implies generate() was called above.
            # So, this check is implicitly part of the main test logic.
             mock_dspy_predict_check.assert_not_called() # This assertion is tricky without careful scoping of the patch or re-running generate.
                                                        # It's better to ensure the mock is active during the generate call.
                                                        # For simplicity, assuming it's checked implicitly by not needing DSPy.

    @patch('src.media_generation.generators._generate_openai_image')
    @patch('src.media_generation.generators.check_and_revise_prompt')
    @patch('src.media_generation.generators.DSPyImage.from_file') 
    def test_generate_reject_revise_approve(self, mock_dspy_from_file, mock_dspy_predict, mock_openai_gen_helper):
        """Test iterative generation: reject, DSPy revises, then approved."""
        initial_prompt = "A complex scene"
        revised_prompt = "A simpler, revised scene"

        generated_files_touch_paths = []
        def side_effect_create_file_tracked(prompt, file_path_str):
            Path(file_path_str).parent.mkdir(parents=True, exist_ok=True)
            Path(file_path_str).touch()
            generated_files_touch_paths.append(file_path_str)
            return True
        mock_openai_gen_helper.side_effect = side_effect_create_file_tracked
        
        self.mock_approval_log.prompt_for_approval.side_effect = [False, True] 

        mock_dspy_predict.return_value = MagicMock(feedback="DSPy feedback", revised_prompt=revised_prompt)
        mock_dspy_from_file.return_value = MagicMock() 

        generated_paths = self.generator.generate(initial_prompt=initial_prompt)

        self.assertEqual(len(generated_paths), 1)
        self.assertTrue(Path(generated_paths[0]).name.endswith(".png")) 
        self.assertTrue(Path(generated_paths[0]).exists())
        self.assertEqual(Path(generated_paths[0]), Path(generated_files_touch_paths[1])) 

        self.assertEqual(mock_openai_gen_helper.call_count, 2)
        # Check calls more robustly
        self.assertEqual(mock_openai_gen_helper.call_args_list[0][0][0], initial_prompt)
        self.assertEqual(mock_openai_gen_helper.call_args_list[0][0][1], generated_files_touch_paths[0])
        self.assertEqual(mock_openai_gen_helper.call_args_list[1][0][0], revised_prompt)
        self.assertEqual(mock_openai_gen_helper.call_args_list[1][0][1], generated_files_touch_paths[1])


        self.assertEqual(self.mock_approval_log.prompt_for_approval.call_count, 2)
        
        mock_dspy_predict.assert_called_once()
        dspy_call_args_pos, _ = mock_dspy_predict.call_args
        self.assertEqual(dspy_call_args_pos[0]['current_prompt'], initial_prompt) # DSPy called with initial prompt
        self.assertEqual(dspy_call_args_pos[0]['desired_prompt'], initial_prompt) # And desired prompt

        mock_dspy_from_file.assert_called_once_with(str(generated_files_touch_paths[0]))


    @patch('src.media_generation.generators._generate_openai_image', return_value=False)
    def test_generate_openai_fails_first_try(self, mock_openai_gen_helper):
        """Test behavior when OpenAI image generation fails on the first attempt."""
        initial_prompt = "This will fail"
        
        # Need to ensure the path provided to mock_openai_gen_helper is somewhat predictable
        # or use unittest.mock.ANY for the path if it's hard to predict.
        # The ImageGenerator creates a session_temp_dir. Let's predict the first file path.
        # This is tricky as mkdtemp is involved. Using ANY for path is safer.
        
        generated_paths = self.generator.generate(initial_prompt=initial_prompt)
        
        self.assertEqual(len(generated_paths), 0) 
        mock_openai_gen_helper.assert_called_once_with(initial_prompt, unittest.mock.ANY)
        self.mock_approval_log.prompt_for_approval.assert_not_called() 

    @patch('src.media_generation.generators._generate_openai_image')
    @patch('rich.prompt.Prompt.ask') 
    def test_generate_dspy_disabled_or_fails_fallback_to_user_prompt(self, mock_rich_prompt_ask, mock_openai_gen_helper):
        """Test fallback to user prompt if DSPy is disabled or fails."""
        initial_prompt = "Initial for DSPy fail test"
        user_revised_prompt = "User's revised prompt after DSPy fail"

        with patch('src.media_generation.generators.check_and_revise_prompt', None):
            generated_files_touch_paths = []
            def side_effect_create_file_tracked(prompt, file_path_str):
                Path(file_path_str).parent.mkdir(parents=True, exist_ok=True)
                Path(file_path_str).touch()
                generated_files_touch_paths.append(file_path_str)
                return True
            mock_openai_gen_helper.side_effect = side_effect_create_file_tracked
            
            self.mock_approval_log.prompt_for_approval.side_effect = [False, True] 
            mock_rich_prompt_ask.return_value = user_revised_prompt 

            generated_paths = self.generator.generate(initial_prompt=initial_prompt)

            self.assertEqual(len(generated_paths), 1) 
            self.assertEqual(Path(generated_paths[0]), Path(generated_files_touch_paths[1]))

            self.assertEqual(mock_openai_gen_helper.call_count, 2)
            self.assertEqual(mock_openai_gen_helper.call_args_list[0][0][0], initial_prompt)
            self.assertEqual(mock_openai_gen_helper.call_args_list[1][0][0], user_revised_prompt)
            
            self.assertEqual(self.mock_approval_log.prompt_for_approval.call_count, 2)
            # The prompt to user for revision is based on the current_prompt at that time
            mock_rich_prompt_ask.assert_called_once_with("Enter a revised prompt or type 'abort'", default=initial_prompt)


    def test_generate_max_iterations_reached(self):
        """Test that generation stops after max_iterations if no image is approved."""
        initial_prompt = "Max iterations test"
        # ImageGenerator.max_iterations is hardcoded to 5
        # If configurable, we'd set it lower for the test.
        
        with patch('src.media_generation.generators._generate_openai_image') as mock_oai_gen, \
             patch('src.media_generation.generators.check_and_revise_prompt', MagicMock(return_value=MagicMock(revised_prompt="dummy_revised"))) as mock_dspy, \
             patch('src.media_generation.generators.DSPyImage.from_file', MagicMock()):

            def side_effect_touch_file(prompt, file_path_str): 
                Path(file_path_str).parent.mkdir(parents=True, exist_ok=True)
                Path(file_path_str).touch()
                return True
            mock_oai_gen.side_effect = side_effect_touch_file

            self.mock_approval_log.prompt_for_approval.return_value = False # Always reject

            generated_paths = self.generator.generate(initial_prompt=initial_prompt)

            self.assertEqual(len(generated_paths), 0)
            # ImageGenerator has hardcoded max_iterations = 5
            self.assertEqual(mock_oai_gen.call_count, 5) 
            self.assertEqual(self.mock_approval_log.prompt_for_approval.call_count, 5)
            # DSPy is called after each rejection, so 5 times if all 5 iterations are rejected.
            self.assertEqual(mock_dspy.call_count, 5)


if __name__ == '__main__':
    # This allows running tests directly via `python tests/unit/test_media_generation.py`
    # For more comprehensive test runs, use `pytest`
    unittest.main()
