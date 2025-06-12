"""
Tests for transcription services.
Comprehensive test suite for the instance-based transcription system.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from transcription.services import (
    AudioProcessingService,
    CampaignContextService,
    TranscriptionConfig,
    TranscriptionService,
)
from transcription.utils import ordinal
from transcription.responses import WhisperResponse


class TranscriptionConfigTests(TestCase):
    """Test the TranscriptionConfig class instance-based configuration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_initialization(self):
        """Test that config initializes with default values."""
        config = TranscriptionConfig()

        self.assertEqual(config.max_file_size_mb, 20)
        self.assertEqual(config.chunk_duration_minutes, 10)
        self.assertEqual(config.delay_between_requests, 21)
        self.assertEqual(config.recent_threshold_days, 180)
        self.assertEqual(config.input_folder, Path("recordings"))
        self.assertEqual(config.output_folder, Path("transcripts"))
        self.assertEqual(config.chunks_folder, Path("audio_chunks"))
        self.assertEqual(
            config.audio_extensions, [".flac", ".wav", ".aac", ".m4a", ".mp3"]
        )

    def test_custom_initialization(self):
        """Test that config can be initialized with custom values."""
        custom_input = self.temp_path / "custom_input"
        custom_output = self.temp_path / "custom_output"
        custom_chunks = self.temp_path / "custom_chunks"

        config = TranscriptionConfig(
            input_folder=custom_input,
            output_folder=custom_output,
            chunks_folder=custom_chunks,
            max_file_size_mb=15,
            chunk_duration_minutes=5,
            delay_between_requests=10,
            recent_threshold_days=90,
            openai_api_key="test_key",
        )

        self.assertEqual(config.input_folder, custom_input)
        self.assertEqual(config.output_folder, custom_output)
        self.assertEqual(config.chunks_folder, custom_chunks)
        self.assertEqual(config.max_file_size_mb, 15)
        self.assertEqual(config.chunk_duration_minutes, 5)
        self.assertEqual(config.delay_between_requests, 10)
        self.assertEqual(config.recent_threshold_days, 90)
        self.assertEqual(config.openai_api_key, "test_key")

    @patch("transcription.services.settings")
    @patch("transcription.services.os")
    def test_openai_key_from_environment(self, mock_os, mock_settings):
        """Test that OpenAI API key is loaded from environment."""
        # Make sure Django settings doesn't have the key
        del mock_settings.OPENAI_API_KEY  # Simulate attribute not existing
        # Mock environment variable
        mock_os.getenv.return_value = "env_test_key"

        config = TranscriptionConfig()
        self.assertEqual(config.openai_api_key, "env_test_key")

    @override_settings(OPENAI_API_KEY="settings_test_key")
    def test_openai_key_from_settings(self):
        """Test that OpenAI API key is loaded from Django settings."""
        with patch.dict(os.environ, {}, clear=True):
            config = TranscriptionConfig()
            self.assertEqual(config.openai_api_key, "settings_test_key")

    def test_setup_directories_creates_folders(self):
        """Test that setup_directories creates output and chunks folders."""
        config = TranscriptionConfig(
            output_folder=self.temp_path / "output",
            chunks_folder=self.temp_path / "chunks",
        )

        self.assertTrue(config.output_folder.exists())
        self.assertTrue(config.chunks_folder.exists())


class CampaignContextServiceTests(TestCase):
    """Test the CampaignContextService with instance-based configuration."""

    def setUp(self):
        self.config = TranscriptionConfig(recent_threshold_days=30)
        self.service = CampaignContextService(self.config)

    def test_initialization_with_config(self):
        """Test that service initializes with config instance."""
        self.assertEqual(self.service.config, self.config)
        self.assertEqual(self.service.config.recent_threshold_days, 30)

    @patch("transcription.services.timezone")
    def test_get_campaign_context_empty_database(self, mock_timezone):
        """Test context fetching with empty database."""
        mock_timezone.now.return_value = timezone.now()

        context = self.service.get_campaign_context()

        expected_keys = ["characters", "places", "races", "items", "associations"]
        for key in expected_keys:
            self.assertIn(key, context)
            self.assertEqual(context[key], [])

    def test_format_context_for_prompt_empty_context(self):
        """Test prompt formatting with empty context."""
        empty_context = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        result = self.service._format_context_for_prompt(empty_context)
        self.assertEqual(result, "")

    def test_format_context_for_prompt_with_data(self):
        """Test prompt formatting with sample data."""
        context = {
            "characters": [
                {"name": "Gandalf", "race": "Wizard", "recently_mentioned": True},
                {"name": "Legolas", "race": "Elf", "recently_mentioned": False},
            ],
            "places": [{"name": "Rivendell", "recently_mentioned": True}],
            "races": [{"name": "Dwarf", "recently_mentioned": False}],
            "items": [
                {
                    "name": "Ring of Power",
                    "type": "artifact",
                    "recently_mentioned": True,
                }
            ],
            "associations": [{"name": "Fellowship", "recently_mentioned": True}],
        }

        result = self.service._format_context_for_prompt(context)

        # Check that all sections are included
        self.assertIn("Key Characters:", result)
        self.assertIn("Gandalf (Wizard)", result)
        self.assertIn("Important Places:", result)
        self.assertIn("Rivendell", result)
        self.assertIn("Notable Items:", result)
        self.assertIn("Ring of Power (artifact)", result)
        self.assertIn("Organizations:", result)
        self.assertIn("Fellowship", result)

    def test_format_context_truncates_long_text(self):
        """Test that long context is properly truncated."""
        # Create context that will exceed max_length
        long_characters = [
            {"name": f"Character_{i}", "race": "Human", "recently_mentioned": False}
            for i in range(50)
        ]
        context = {
            "characters": long_characters,
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        result = self.service._format_context_for_prompt(context, max_length=100)

        self.assertLessEqual(len(result), 120)  # Allow some buffer for truncation logic
        self.assertTrue(result.endswith("...") or result.endswith("."))


class AudioProcessingServiceTests(TestCase):
    """Test the AudioProcessingService with instance-based configuration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            chunks_folder=self.temp_path / "chunks",
            max_file_size_mb=1,  # Small for testing
            chunk_duration_minutes=1,
        )
        self.service = AudioProcessingService(self.config)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization_with_config(self):
        """Test that service initializes with config instance."""
        self.assertEqual(self.service.config, self.config)

    def test_get_file_size_mb(self):
        """Test file size calculation."""
        # Create a test file with known size
        test_file = self.temp_path / "test.txt"
        test_content = "x" * 1024  # 1KB
        test_file.write_text(test_content)

        size_mb = AudioProcessingService.get_file_size_mb(test_file)
        expected_size = 1024 / (1024 * 1024)  # Convert to MB
        self.assertAlmostEqual(size_mb, expected_size, places=6)

    @patch("transcription.services.AudioSegment")
    def test_split_audio_file_under_limit(self, mock_audio_segment):
        """Test that small files are not split."""
        test_file = self.temp_path / "small.mp3"
        test_file.write_text("small content")  # Very small file

        result = self.service.split_audio_file(test_file, "TestCharacter")

        # Should return original file without splitting
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], test_file)
        mock_audio_segment.from_file.assert_not_called()

    @patch("transcription.services.AudioSegment")
    def test_split_audio_file_over_limit(self, mock_audio_segment):
        """Test that large files are split into chunks."""
        # Create a large test file (larger than 1MB limit in config)
        test_file = self.temp_path / "large.mp3"
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        test_file.write_bytes(large_content.encode())

        # Ensure chunks folder exists
        self.config.chunks_folder.mkdir(parents=True, exist_ok=True)

        # Mock audio processing
        mock_audio = Mock()
        # Properly mock the __len__ method to return duration in milliseconds
        type(mock_audio).__len__ = Mock(
            return_value=120000
        )  # 2 minutes in milliseconds

        # Mock chunk creation and export
        mock_chunk = Mock()

        # Create a custom side effect for chunk export that creates dummy files
        def mock_export_side_effect(chunk_path, format):
            # Create the chunk file when export is called
            chunk_path.write_text("mock chunk content")

        mock_chunk.export.side_effect = mock_export_side_effect
        mock_audio.__getitem__ = Mock(return_value=mock_chunk)

        mock_audio_segment.from_file.return_value = mock_audio

        result = self.service.split_audio_file(test_file, "TestCharacter")

        # Should create 2 chunks (2 minutes / 1 minute per chunk)
        self.assertEqual(len(result), 2)
        mock_audio_segment.from_file.assert_called_once_with(test_file)
        # Verify that export was called for each chunk
        self.assertEqual(mock_chunk.export.call_count, 2)

    @patch("transcription.services.AudioSegment")
    def test_split_audio_handles_exceptions(self, mock_audio_segment):
        """Test that splitting handles exceptions gracefully."""
        test_file = self.temp_path / "problematic.mp3"
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        test_file.write_bytes(large_content.encode())

        # Mock exception during audio processing
        mock_audio_segment.from_file.side_effect = Exception("Audio processing failed")

        result = self.service.split_audio_file(test_file, "TestCharacter")

        # Should return original file when splitting fails
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], test_file)


class TranscriptionServiceTests(TestCase):
    """Test the TranscriptionService with instance-based configuration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            input_folder=self.temp_path / "input",
            output_folder=self.temp_path / "output",
            chunks_folder=self.temp_path / "chunks",
            openai_api_key="test_key",
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("transcription.services.openai")
    def test_initialization_with_config(self, mock_openai):
        """Test that service initializes with config instance."""
        service = TranscriptionService(self.config)

        self.assertEqual(service.config, self.config)
        self.assertIsInstance(service.context_service, CampaignContextService)
        self.assertIsInstance(service.audio_service, AudioProcessingService)
        # Check that openai.api_key was set correctly
        self.assertEqual(mock_openai.api_key, "test_key")

    def test_initialization_without_api_key(self):
        """Test that service raises error without API key."""
        # Create config with no API key
        config = TranscriptionConfig(openai_api_key=None)

        # Clear environment and settings to ensure no API key is available
        with patch.dict(os.environ, {}, clear=True):
            with patch("transcription.services.getattr", return_value=None):
                with patch("transcription.services.os.getenv", return_value=None):
                    # Force config to have no API key
                    config.openai_api_key = None

                    with self.assertRaises(ValueError) as context:
                        TranscriptionService(config)

                    self.assertIn("OpenAI API key not found", str(context.exception))

    def test_ordinal_conversion(self):
        """Test ordinal number conversion."""
        test_cases = [
            (1, "1st"),
            (2, "2nd"),
            (3, "3rd"),
            (4, "4th"),
            (11, "11th"),
            (12, "12th"),
            (13, "13th"),
            (21, "21st"),
            (22, "22nd"),
            (23, "23rd"),
            (24, "24th"),
        ]

        for number, expected in test_cases:
            with self.subTest(number=number):
                result = ordinal(number)
                self.assertEqual(result, expected)

    @patch("transcription.services.openai")
    def test_create_whisper_prompt_private(self, mock_openai):
        """Test whisper prompt creation."""
        service = TranscriptionService(self.config)

        # Mock context service
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }
        service.context_service.get_formatted_context.return_value = "Test context"

        prompt = service._create_whisper_prompt(
            character_name="TestPlayer",
            chunk_info="the 1st chunk of 3",
            previous_chunks_text="Previous text",
            previous_transcript="Last session transcript",
        )

        # Verify prompt contains expected elements
        self.assertIn("Dungeons & Dragons", prompt)
        self.assertIn("This is TestPlayer and this is the 1st chunk of 3", prompt)
        self.assertIn("Test context", prompt)
        self.assertIn("Previous text", prompt)
        self.assertIn("Last session transcript", prompt)

    @patch("transcription.services.openai")
    def test_call_whisper_api_success(self, mock_openai):
        """Test successful API call to Whisper."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"

        # Create test audio file
        test_file = self.config.input_folder / "test.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("fake audio content")

        # Mock OpenAI response
        mock_response = {"text": "Test transcription", "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service._call_whisper_api(test_file, "TestPlayer")

        # Should return a WhisperResponse object
        self.assertIsNotNone(result)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.text, "Test transcription")
        self.assertEqual(result.segments, [])
        self.assertEqual(result.raw_response, mock_response)
        mock_openai.Audio.transcribe.assert_called_once()

    @patch("transcription.services.openai")
    def test_call_whisper_api_failure(self, mock_openai):
        """Test API call failure handling."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"

        # Create test audio file
        test_file = self.config.input_folder / "test.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("fake audio content")

        # Mock OpenAI exception
        mock_openai.Audio.transcribe.side_effect = Exception("API Error")

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service._call_whisper_api(test_file, "TestPlayer")

        self.assertIsNone(result)

    @patch("transcription.services.openai")
    def test_process_all_files(self, mock_openai):
        """Test processing all files in input folder."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }
        service.context_service.format_context_for_prompt.return_value = ""

        # Create test audio files
        self.config.input_folder.mkdir(parents=True, exist_ok=True)
        test_files = [
            self.config.input_folder / "player1.mp3",
            self.config.input_folder / "player2.flac",
            self.config.input_folder / "notes.txt",  # Should be ignored
        ]

        for file in test_files:
            file.write_text("content")

        # Mock audio service
        service.audio_service = Mock()
        service.audio_service.split_audio_file.return_value = [
            test_files[0]
        ]  # Return same file

        # Mock successful transcription
        mock_response = {"text": "Test transcription"}
        mock_openai.Audio.transcribe.return_value = mock_response

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            processed_count = service.process_all_files()

        # Should process 2 audio files, ignore 1 text file
        self.assertEqual(processed_count, 2)


class IntegrationTests(TestCase):
    """Integration tests for the entire transcription system."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multiple_config_instances_independence(self):
        """Test that multiple config instances don't interfere with each other."""
        config1 = TranscriptionConfig(
            input_folder=self.temp_path / "config1_input",
            output_folder=self.temp_path / "config1_output",
            max_file_size_mb=10,
        )

        config2 = TranscriptionConfig(
            input_folder=self.temp_path / "config2_input",
            output_folder=self.temp_path / "config2_output",
            max_file_size_mb=25,
        )

        # Verify configs are independent
        self.assertNotEqual(config1.input_folder, config2.input_folder)
        self.assertNotEqual(config1.output_folder, config2.output_folder)
        self.assertNotEqual(config1.max_file_size_mb, config2.max_file_size_mb)

        # Verify both directories were created
        self.assertTrue(config1.output_folder.exists())
        self.assertTrue(config2.output_folder.exists())

    @patch("transcription.services.openai")
    def test_service_instances_use_correct_config(self, mock_openai):
        """Test that service instances use their assigned config."""
        config1 = TranscriptionConfig(
            output_folder=self.temp_path / "service1_output",
            recent_threshold_days=30,
            openai_api_key="key1",
        )

        config2 = TranscriptionConfig(
            output_folder=self.temp_path / "service2_output",
            recent_threshold_days=90,
            openai_api_key="key2",
        )

        service1 = TranscriptionService(config1)
        service2 = TranscriptionService(config2)

        # Verify services use correct configs
        self.assertEqual(service1.config.output_folder, config1.output_folder)
        self.assertEqual(service2.config.output_folder, config2.output_folder)
        self.assertEqual(service1.config.recent_threshold_days, 30)
        self.assertEqual(service2.config.recent_threshold_days, 90)

        # Verify context services use correct configs
        self.assertEqual(service1.context_service.config, config1)
        self.assertEqual(service2.context_service.config, config2)
        self.assertEqual(service1.context_service.config.recent_threshold_days, 30)
        self.assertEqual(service2.context_service.config.recent_threshold_days, 90)

    def test_no_shared_state_between_instances(self):
        """Test that modifying one config doesn't affect another."""
        config1 = TranscriptionConfig(max_file_size_mb=10)
        config2 = TranscriptionConfig(max_file_size_mb=20)

        # Modify config1
        config1.max_file_size_mb = 15

        # Verify config2 is unchanged
        self.assertEqual(config2.max_file_size_mb, 20)
        self.assertNotEqual(config1.max_file_size_mb, config2.max_file_size_mb)


class WhisperResponseTests(TestCase):
    """Test the WhisperResponse class."""

    def test_successful_response(self):
        """Test handling of a successful Whisper response."""
        response_data = {
            "text": "Hello world",
            "segments": [{"start": 0, "end": 1, "text": "Hello"}],
        }
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)
        self.assertEqual(response.text, "Hello world")
        self.assertEqual(len(response.segments), 1)

    def test_empty_response(self):
        """Test handling of an empty response."""
        response = WhisperResponse({})

        self.assertFalse(response.is_valid)
        self.assertEqual(response.text, "")
        self.assertEqual(response.segments, [])

    def test_invalid_response_structure(self):
        """Test handling of an invalid response structure."""
        response = WhisperResponse({"unexpected_key": "value"})

        self.assertFalse(response.is_valid)
        self.assertEqual(response.text, "")
        self.assertEqual(response.segments, [])

    def test_partial_response(self):
        """Test handling of a partially valid response."""
        response_data = {"text": "Partial response"}
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)
        self.assertEqual(response.text, "Partial response")
        self.assertEqual(response.segments, [])

    def test_segment_parsing(self):
        """Test parsing of segments in the response."""
        response_data = {
            "text": "Hello world",
            "segments": [
                {"start": 0, "end": 1, "text": "Hello"},
                {"start": 1, "end": 2, "text": "world"},
            ],
        }
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)
        self.assertEqual(len(response.segments), 2)
        self.assertEqual(response.segments[0]["text"], "Hello")
        self.assertEqual(response.segments[1]["text"], "world")


class UtilityFunctionTests(TestCase):
    """Test utility functions from utils.py"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_save_json_success(self):
        """Test successful JSON serialization and saving."""
        from transcription.utils import safe_save_json

        test_data = {
            "text": "Hello world",
            "segments": [{"start": 0, "end": 1, "text": "Hello"}],
            "metadata": {"session": 1},
        }
        output_path = self.temp_path / "test_output.json"

        result = safe_save_json(test_data, output_path, "test data")

        self.assertTrue(result)
        self.assertTrue(output_path.exists())

        # Verify content was saved correctly
        import json

        saved_data = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_data, test_data)

    def test_safe_save_json_serialization_error(self):
        """Test handling of non-serializable data."""
        from transcription.utils import safe_save_json

        # Create non-serializable data (function object)
        test_data = {"function": lambda x: x}
        output_path = self.temp_path / "test_output.json"

        result = safe_save_json(test_data, output_path, "non-serializable data")

        self.assertFalse(result)
        self.assertFalse(output_path.exists())

    def test_safe_save_json_file_permission_error(self):
        """Test handling of file permission errors."""
        from transcription.utils import safe_save_json

        test_data = {"text": "Hello world"}
        # Create a read-only directory
        readonly_dir = self.temp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        output_path = readonly_dir / "test_output.json"

        result = safe_save_json(test_data, output_path, "permission test")

        self.assertFalse(result)

    def test_ordinal_basic_numbers(self):
        """Test ordinal conversion for basic numbers."""
        from transcription.utils import ordinal

        test_cases = [
            (1, "1st"),
            (2, "2nd"),
            (3, "3rd"),
            (4, "4th"),
            (5, "5th"),
            (21, "21st"),
            (22, "22nd"),
            (23, "23rd"),
            (24, "24th"),
            (31, "31st"),
            (32, "32nd"),
            (33, "33rd"),
            (34, "34th"),
            (101, "101st"),
            (102, "102nd"),
            (103, "103rd"),
            (104, "104th"),
        ]

        for number, expected in test_cases:
            with self.subTest(number=number):
                result = ordinal(number)
                self.assertEqual(result, expected)

    def test_ordinal_teens_special_case(self):
        """Test ordinal conversion for teen numbers (special 'th' case)."""
        from transcription.utils import ordinal

        teen_cases = [
            (10, "10th"),
            (11, "11th"),
            (12, "12th"),
            (13, "13th"),
            (14, "14th"),
            (15, "15th"),
            (16, "16th"),
            (17, "17th"),
            (18, "18th"),
            (19, "19th"),
            (20, "20th"),
        ]

        for number, expected in teen_cases:
            with self.subTest(number=number):
                result = ordinal(number)
                self.assertEqual(result, expected)

    def test_ordinal_hundreds_and_thousands(self):
        """Test ordinal conversion for larger numbers."""
        from transcription.utils import ordinal

        large_cases = [
            (111, "111th"),
            (112, "112th"),
            (113, "113th"),
            (121, "121st"),
            (1001, "1001st"),
            (1011, "1011th"),
            (1021, "1021st"),
        ]

        for number, expected in large_cases:
            with self.subTest(number=number):
                result = ordinal(number)
                self.assertEqual(result, expected)


class ProcessFileWithSplittingTests(TestCase):
    """Test the main public API method process_file_with_splitting()"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            input_folder=self.temp_path / "input",
            output_folder=self.temp_path / "output",
            chunks_folder=self.temp_path / "chunks",
            openai_api_key="test_key",
            max_file_size_mb=1,  # Small for testing splits
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("transcription.services.openai")
    def test_process_file_already_exists(self, mock_openai):
        """Test that already transcribed files are skipped."""
        service = TranscriptionService(self.config)

        # Create input file
        test_file = self.config.input_folder / "test_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("fake audio content")

        # Create existing output file
        output_file = self.config.output_folder / "test_player.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text('{"text": "existing transcript"}')

        result = service.process_file_with_splitting(test_file)

        self.assertTrue(result)
        mock_openai.Audio.transcribe.assert_not_called()

    @patch("transcription.services.openai")
    def test_process_file_single_file_success(self, mock_openai):
        """Test successful processing of a single file (no splitting)."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"

        # Create small input file (won't be split)
        test_file = self.config.input_folder / "test_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("small audio content")  # Small file

        # Mock successful API response
        mock_response = {"text": "Test transcription", "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service.process_file_with_splitting(test_file, "previous", "notes")

        self.assertTrue(result)
        mock_openai.Audio.transcribe.assert_called_once()

        # Verify output file was created
        output_file = self.config.output_folder / "test_player.json"
        self.assertTrue(output_file.exists())

    @patch("transcription.services.openai")
    def test_process_file_single_file_api_failure(self, mock_openai):
        """Test handling of API failure for single file."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"

        test_file = self.config.input_folder / "test_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("small audio content")

        # Mock API failure
        mock_openai.Audio.transcribe.side_effect = Exception("API Error")

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service.process_file_with_splitting(test_file)

        self.assertFalse(result)

    @patch("transcription.services.time.sleep")  # Mock sleep to speed up tests
    @patch("transcription.services.openai")
    @patch("transcription.services.AudioSegment")
    def test_process_file_with_splitting_success(
        self, mock_audio_segment, mock_openai, mock_sleep
    ):
        """Test successful processing of file that needs splitting."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"

        # Create large file that will be split
        test_file = self.config.input_folder / "large_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        test_file.write_bytes(large_content.encode())

        # Mock audio splitting
        chunk1 = self.config.chunks_folder / "large_player_chunk_01.mp3"
        chunk2 = self.config.chunks_folder / "large_player_chunk_02.mp3"
        chunk1.parent.mkdir(parents=True, exist_ok=True)
        chunk1.write_text("chunk1 content")
        chunk2.write_text("chunk2 content")

        # Mock audio service to return chunks
        service.audio_service = Mock()
        service.audio_service.split_audio_file.return_value = [chunk1, chunk2]

        # Mock successful API responses for chunks
        mock_responses = [
            {"text": "Chunk 1 transcription", "segments": []},
            {"text": "Chunk 2 transcription", "segments": []},
        ]
        mock_openai.Audio.transcribe.side_effect = mock_responses

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service.process_file_with_splitting(
                test_file, "previous transcript", "session notes"
            )

        self.assertTrue(result)
        self.assertEqual(mock_openai.Audio.transcribe.call_count, 2)

        # Verify combined output file was created
        output_file = self.config.output_folder / "large_player.json"
        self.assertTrue(output_file.exists())

    @patch("transcription.services.time.sleep")  # Mock sleep to speed up tests
    @patch("transcription.services.openai")
    def test_process_file_with_splitting_partial_failure(self, mock_openai, mock_sleep):
        """Test handling when some chunks fail during splitting."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"

        test_file = self.config.input_folder / "large_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        test_file.write_bytes(large_content.encode())

        # Mock chunks
        chunk1 = self.config.chunks_folder / "large_player_chunk_01.mp3"
        chunk2 = self.config.chunks_folder / "large_player_chunk_02.mp3"
        chunk1.parent.mkdir(parents=True, exist_ok=True)
        chunk1.write_text("chunk1 content")
        chunk2.write_text("chunk2 content")

        service.audio_service = Mock()
        service.audio_service.split_audio_file.return_value = [chunk1, chunk2]

        # Mock API failure for second chunk
        mock_openai.Audio.transcribe.side_effect = [
            {"text": "Chunk 1 transcription", "segments": []},
            Exception("API Error for chunk 2"),
        ]

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service.process_file_with_splitting(test_file)

        self.assertTrue(
            result
        )  # Should succeed with partial results (at least one chunk succeeded)


class ErrorHandlingTests(TestCase):
    """Test error handling scenarios across the system"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            input_folder=self.temp_path / "input",
            output_folder=self.temp_path / "output",
            chunks_folder=self.temp_path / "chunks",
            openai_api_key="test_key",
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_whisper_response_with_malformed_segments(self):
        """Test WhisperResponse handling of malformed segment data."""
        # Test segments with missing required fields
        response_data = {
            "text": "Hello world",
            "segments": [
                {"start": 0, "end": 1, "text": "Hello"},  # Valid
                {"start": 1, "text": "missing end"},  # Invalid - missing 'end'
                {"end": 2, "text": "missing start"},  # Invalid - missing 'start'
                {"start": 2, "end": 3},  # Invalid - missing 'text'
                "not a dict",  # Invalid - not a dict
                {"start": 3, "end": 4, "text": "valid"},  # Valid
            ],
        }
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)  # Should still be valid due to text
        self.assertEqual(response.text, "Hello world")
        # Should filter out malformed segments, keeping only valid ones
        valid_segments = response.segments
        self.assertEqual(len(valid_segments), 2)
        self.assertEqual(valid_segments[0]["text"], "Hello")
        self.assertEqual(valid_segments[1]["text"], "valid")

    def test_whisper_response_with_non_list_segments(self):
        """Test WhisperResponse handling when segments is not a list."""
        response_data = {"text": "Hello world", "segments": "not a list"}
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)  # Still valid due to text
        self.assertEqual(response.text, "Hello world")
        self.assertEqual(response.segments, [])  # Should return empty list

    def test_whisper_response_truthiness(self):
        """Test WhisperResponse __bool__ method."""
        valid_response = WhisperResponse({"text": "Hello"})
        invalid_response = WhisperResponse({})

        self.assertTrue(bool(valid_response))
        self.assertFalse(bool(invalid_response))

    @patch("transcription.services.openai")
    def test_create_combined_transcript_with_invalid_data(self, mock_openai):
        """Test _create_combined_transcript with invalid transcript data."""
        service = TranscriptionService(self.config)

        # Test with invalid transcript data
        invalid_transcripts = [
            {"invalid": "structure"},
            "not a dict",
            {"text": None},  # None text
        ]

        result = service._create_combined_transcript(invalid_transcripts)

        # Should handle gracefully and return something
        self.assertIsNotNone(result)
        self.assertIn("text", result)
        self.assertIn("segments", result)

    @patch("transcription.services.openai")
    def test_audio_processing_with_invalid_file(self, mock_openai):
        """Test audio processing with file that doesn't exist."""
        service = TranscriptionService(self.config)

        # Try to process non-existent file
        non_existent_file = self.config.input_folder / "does_not_exist.mp3"

        result = service.process_file_with_splitting(non_existent_file)

        # Should handle gracefully without crashing
        self.assertFalse(result)

    def test_config_directory_creation_permission_error(self):
        """Test config behavior when directory creation fails."""
        # Create a file where we want to create a directory
        conflicting_file = self.temp_path / "conflict"
        conflicting_file.write_text("blocking file")

        config = TranscriptionConfig(
            output_folder=conflicting_file,  # This will conflict
            chunks_folder=self.temp_path / "chunks",
        )

        # Directory creation should handle the error gracefully
        # (The property will try to create but may fail)
        try:
            _ = config.output_folder
            # If it doesn't raise an exception, that's fine too
        except Exception:
            # Expected behavior - should handle gracefully
            pass


class EdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            input_folder=self.temp_path / "input",
            output_folder=self.temp_path / "output",
            chunks_folder=self.temp_path / "chunks",
            openai_api_key="test_key",
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_whisper_response_with_empty_text(self):
        """Test WhisperResponse with empty text field."""
        response_data = {"text": "", "segments": []}
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)
        self.assertEqual(response.text, "")
        self.assertEqual(response.segments, [])

    def test_whisper_response_with_none_values(self):
        """Test WhisperResponse with None values."""
        response_data = {"text": None, "segments": None}
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)  # None text should be valid structure
        self.assertEqual(response.text, "")  # Should handle None gracefully
        self.assertEqual(response.segments, [])

    def test_whisper_response_raw_response_invalid(self):
        """Test raw_response property with invalid response."""
        invalid_response = WhisperResponse("not a dict")

        self.assertFalse(invalid_response.is_valid)
        self.assertEqual(invalid_response.raw_response, {})

    @patch("transcription.services.openai")
    def test_create_whisper_prompt_with_empty_parameters(self, mock_openai):
        """Test whisper prompt creation with all empty optional parameters."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = ""

        prompt = service._create_whisper_prompt(
            character_name="TestPlayer",
            chunk_info="",
            previous_chunks_text="",
            previous_transcript="",
            session_notes="",
        )

        self.assertIn("Dungeons & Dragons", prompt)
        self.assertIn("This is TestPlayer", prompt)
        # Should not contain empty context sections
        self.assertNotIn("Campaign Context:", prompt)
        self.assertNotIn("Previous Transcript:", prompt)

    @patch("transcription.services.openai")
    def test_create_whisper_prompt_with_long_previous_chunks(self, mock_openai):
        """Test prompt creation with very long previous chunks text."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Context"

        # Create very long previous chunks text (over 500 words)
        long_text = " ".join([f"word{i}" for i in range(600)])

        prompt = service._create_whisper_prompt(
            character_name="TestPlayer",
            previous_chunks_text=long_text,
        )

        # Should truncate to last 500 words
        self.assertIn("Recent chunks", prompt)
        truncated_portion = prompt.split(
            "Recent chunks from this session for TestPlayer:\n"
        )[1]
        word_count = len(truncated_portion.split("Campaign Context:")[0].split())
        self.assertLessEqual(word_count, 500)

    @patch("transcription.services.openai")
    def test_process_chunks_with_empty_chunk_list(self, mock_openai):
        """Test _process_chunks with empty chunk list."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()

        result = service._process_chunks([], "TestPlayer", 1, "")

        self.assertIsNone(result)
        mock_openai.Audio.transcribe.assert_not_called()

    @patch("transcription.services.openai")
    def test_create_combined_transcript_with_empty_list(self, mock_openai):
        """Test _create_combined_transcript with empty transcript list."""
        service = TranscriptionService(self.config)

        result = service._create_combined_transcript([])

        self.assertIsNotNone(result)
        self.assertEqual(result["text"], "")
        self.assertEqual(result["segments"], [])
        self.assertEqual(result["chunks"], [])

    @patch("transcription.services.openai")
    def test_create_combined_transcript_with_segments_time_offset(self, mock_openai):
        """Test that segments get proper time offsets in combined transcript."""
        service = TranscriptionService(self.config)

        transcripts = [
            {
                "text": "First chunk",
                "segments": [{"start": 0, "end": 5, "text": "First"}],
            },
            {
                "text": "Second chunk",
                "segments": [{"start": 0, "end": 3, "text": "Second"}],
            },
        ]

        result = service._create_combined_transcript(transcripts)

        self.assertIsNotNone(result)
        self.assertEqual(len(result["segments"]), 2)
        # First segment should have original timing
        self.assertEqual(result["segments"][0]["start"], 0)
        self.assertEqual(result["segments"][0]["end"], 5)
        # Second segment should have time offset added
        chunk_duration_seconds = service.config.chunk_duration_minutes * 60
        self.assertEqual(result["segments"][1]["start"], chunk_duration_seconds)
        self.assertEqual(result["segments"][1]["end"], chunk_duration_seconds + 3)

    def test_audio_processing_get_file_size_with_zero_size_file(self):
        """Test file size calculation with zero-byte file."""
        zero_file = self.temp_path / "empty.mp3"
        zero_file.touch()  # Create empty file

        size = AudioProcessingService.get_file_size_mb(zero_file)
        self.assertEqual(size, 0.0)

    @patch("transcription.services.openai")
    def test_process_all_files_with_empty_directory(self, mock_openai):
        """Test process_all_files with no audio files in directory."""
        service = TranscriptionService(self.config)

        # Create empty input directory
        self.config.input_folder.mkdir(parents=True, exist_ok=True)

        result = service.process_all_files()

        self.assertEqual(result, 0)
        mock_openai.Audio.transcribe.assert_not_called()

    @patch("transcription.services.openai")
    def test_process_all_files_with_only_non_audio_files(self, mock_openai):
        """Test process_all_files with only non-audio files."""
        service = TranscriptionService(self.config)

        # Create directory with non-audio files
        self.config.input_folder.mkdir(parents=True, exist_ok=True)
        (self.config.input_folder / "notes.txt").write_text("notes")
        (self.config.input_folder / "image.jpg").write_text("fake image")
        (self.config.input_folder / "document.pdf").write_text("fake pdf")

        result = service.process_all_files()

        self.assertEqual(result, 0)
        mock_openai.Audio.transcribe.assert_not_called()

    def test_campaign_context_service_format_context_with_max_length_zero(self):
        """Test context formatting with max_length=0."""
        service = CampaignContextService(self.config)

        context = {
            "characters": [
                {"name": "Test", "race": "Human", "recently_mentioned": True}
            ],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        result = service._format_context_for_prompt(context, max_length=0)
        self.assertEqual(result, "")

    def test_campaign_context_service_format_context_with_very_small_max_length(self):
        """Test context formatting with very small max_length."""
        service = CampaignContextService(self.config)

        context = {
            "characters": [
                {"name": "Test", "race": "Human", "recently_mentioned": True}
            ],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        result = service._format_context_for_prompt(context, max_length=10)
        self.assertLessEqual(len(result), 20)  # Allow some buffer for truncation


class RegressionTests(TestCase):
    """Tests to prevent regression of previously fixed issues"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_directory_lazy_creation(self):
        """Test that directories are created lazily on first access."""
        config = TranscriptionConfig(
            output_folder=self.temp_path / "lazy_output",
            chunks_folder=self.temp_path / "lazy_chunks",
        )

        # Directories should not exist yet
        self.assertFalse((self.temp_path / "lazy_output").exists())
        self.assertFalse((self.temp_path / "lazy_chunks").exists())

        # Access should create them
        _ = config.output_folder
        _ = config.chunks_folder

        self.assertTrue((self.temp_path / "lazy_output").exists())
        self.assertTrue((self.temp_path / "lazy_chunks").exists())

    @patch("transcription.services.openai")
    def test_no_duplicate_directory_setup_calls(self, mock_openai):
        """Test that directory setup is not called redundantly."""
        config = TranscriptionConfig(
            output_folder=self.temp_path / "test_output",
            chunks_folder=self.temp_path / "test_chunks",
            openai_api_key="test_key",
        )

        # Multiple service instantiations should not cause issues
        service1 = TranscriptionService(config)
        service2 = TranscriptionService(config)

        # Both should work fine
        self.assertEqual(service1.config, config)
        self.assertEqual(service2.config, config)

    @patch("transcription.services.openai")
    def test_context_service_uses_consistent_api(self, mock_openai):
        """Test that context service uses the new API consistently."""
        service = TranscriptionService(TranscriptionConfig(openai_api_key="test_key"))

        # Should use get_formatted_context, not the old two-step API
        self.assertTrue(hasattr(service.context_service, "get_formatted_context"))

        # Mock the method to ensure it's called
        service.context_service.get_formatted_context = Mock(
            return_value="test context"
        )

        prompt = service._create_whisper_prompt("TestPlayer")

        service.context_service.get_formatted_context.assert_called_once()


# Create your tests here.
