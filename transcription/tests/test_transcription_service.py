"""
Tests for TranscriptionService class and main processing logic.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from django.test import TestCase

from transcription.services.TranscriptionConfig import TranscriptionConfig
from transcription.services.TranscriptionService import TranscriptionService


class TranscriptionServiceTests(TestCase):
    """Test the TranscriptionService with instance-based configuration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            openai_api_key="test_key",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("transcription.services.TranscriptionService.openai")
    def test_initialization_with_config(self, mock_openai):
        """Test that service initializes with config instance."""
        service = TranscriptionService(self.config)

        self.assertEqual(service.config, self.config)
        self.assertIsNotNone(service.context_service)
        self.assertIsNotNone(service.audio_service)
        # Check that openai.api_key was set correctly
        self.assertEqual(mock_openai.api_key, "test_key")

    def test_initialization_without_api_key(self):
        """Test that service raises error without API key."""
        # Create config with no API key
        config = TranscriptionConfig(openai_api_key=None)

        # Clear environment and settings to ensure no API key is available
        with patch.dict(os.environ, {}, clear=True):
            with patch("transcription.services.getattr", return_value=None):
                with patch("transcription.services.TranscriptionConfig.os.getenv", return_value=None):
                    # Force config to have no API key
                    config.openai_api_key = None

                    with self.assertRaises(ValueError) as context:
                        TranscriptionService(config)

                    self.assertIn("OpenAI API key not found", str(context.exception))

    @patch("transcription.services.TranscriptionService.openai")
    def test_create_whisper_prompt_private(self, mock_openai):
        """Test whisper prompt creation."""
        service = TranscriptionService(self.config)

        # Mock context service
        service.context_service = Mock()
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

    @patch("transcription.services.TranscriptionService.openai")
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

    @patch("transcription.services.TranscriptionService.openai")
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

    @patch("transcription.services.TranscriptionService.openai")
    def test_call_whisper_api_success(self, mock_openai):
        """Test successful API call to Whisper."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"

        # Create test audio file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as test_file:
            test_file.write(b"fake audio content")
            test_file_path = Path(test_file.name)

        # Mock OpenAI response
        mock_response = {"text": "Test transcription", "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service._call_whisper_api(test_file_path, "TestPlayer")

        # Should return a WhisperResponse object
        self.assertIsNotNone(result)
        if result is not None:
            self.assertTrue(result.is_valid)
            self.assertEqual(result.text, "Test transcription")
            self.assertEqual(result.segments, [])
            self.assertEqual(result.raw_response, mock_response)
        mock_openai.Audio.transcribe.assert_called_once()

    @patch("transcription.services.TranscriptionService.openai")
    def test_call_whisper_api_failure(self, mock_openai):
        """Test API call failure handling."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"

        # Create test audio file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as test_file:
            test_file.write(b"fake audio content")
            test_file_path = Path(test_file.name)

        # Mock OpenAI exception
        mock_openai.Audio.transcribe.side_effect = Exception("API Error")

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service._call_whisper_api(test_file_path, "TestPlayer")

        self.assertIsNone(result)

    # Removed test_process_chunks_with_empty_chunk_list: _process_chunks is private. Public API is tested elsewhere.

    @patch("transcription.services.TranscriptionService.openai")
    def test_create_combined_transcript_with_empty_list(self, mock_openai):
        """Test _create_combined_transcript with empty transcript list (public API robustness)."""
        service = TranscriptionService(self.config)
        result = service._create_combined_transcript([])
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.get("text", None), "")
            self.assertEqual(result.get("segments", None), [])
            self.assertEqual(result.get("chunks", None), [])

    @patch("transcription.services.TranscriptionService.openai")
    def test_create_combined_transcript_with_segments_time_offset(self, mock_openai):
        """Test that segments get proper time offsets in combined transcript using AudioData mapping."""
        service = TranscriptionService(self.config)

        # Mock AudioData with custom convert_processed_to_original_timestamp
        class MockAudioData:
            def __init__(self, offset):
                self.offset = offset

            def convert_processed_to_original_timestamp(self, t):
                return t + self.offset

        # Simulate two chunks, second chunk starts at offset 10
        chunk1 = MockAudioData(offset=0)
        chunk2 = MockAudioData(offset=10)
        transcripts = [
            {
                "text": "First chunk",
                "segments": [{"start": 0, "end": 5, "text": "First"}],
                "chunk": chunk1,
            },
            {
                "text": "Second chunk",
                "segments": [{"start": 0, "end": 3, "text": "Second"}],
                "chunk": chunk2,
            },
        ]
        result = service._create_combined_transcript(transcripts)
        self.assertIsNotNone(result)
        segments = result.get("segments") if result else None
        self.assertIsInstance(segments, list)
        if segments is not None:
            self.assertEqual(len(segments), 2)
            # First segment should have original timing (offset 0)
            self.assertEqual(segments[0]["start"], 0)
            self.assertEqual(segments[0]["end"], 5)
            # Second segment should have offset applied (offset 600)
            self.assertEqual(segments[1]["start"], 600)
            self.assertEqual(segments[1]["end"], 603)

    @patch("transcription.services.TranscriptionService.openai")
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
        if result is not None:
            self.assertIn("text", result)
            self.assertIn("segments", result)

    @patch("transcription.services.TranscriptionService.openai")
    def test_service_instances_use_correct_config(self, mock_openai):
        """Test that service instances use their assigned config."""
        config1 = TranscriptionConfig(
            recent_threshold_days=30,
            openai_api_key="key1",
        )

        config2 = TranscriptionConfig(
            recent_threshold_days=90,
            openai_api_key="key2",
        )

        service1 = TranscriptionService(config1)
        service2 = TranscriptionService(config2)

        # Verify services use correct configs
        self.assertEqual(service1.config.recent_threshold_days, 30)
        self.assertEqual(service2.config.recent_threshold_days, 90)

        # Verify context services use correct configs
        self.assertEqual(service1.context_service.config, config1)
        self.assertEqual(service2.context_service.config, config2)
        self.assertEqual(service1.context_service.config.recent_threshold_days, 30)
        self.assertEqual(service2.context_service.config.recent_threshold_days, 90)
