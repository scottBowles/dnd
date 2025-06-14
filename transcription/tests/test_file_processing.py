"""
Tests for file processing and splitting functionality.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from django.test import TestCase

from transcription.services import TranscriptionConfig, TranscriptionService


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
        service.context_service.get_campaign_context.return_value = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }
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
        service.context_service.get_campaign_context.return_value = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }
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
        service.context_service.get_campaign_context.return_value = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }
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
