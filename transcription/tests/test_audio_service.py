"""
Tests for AudioProcessingService class.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import TestCase

from transcription.services import TranscriptionConfig, AudioProcessingService


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

    def test_get_file_size_with_zero_size_file(self):
        """Test file size calculation with zero-byte file."""
        zero_file = self.temp_path / "empty.mp3"
        zero_file.touch()  # Create empty file

        size = AudioProcessingService.get_file_size_mb(zero_file)
        self.assertEqual(size, 0.0)

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
