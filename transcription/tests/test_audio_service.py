"""
Tests for AudioProcessingService class.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import TestCase

from transcription.services.AudioProcessingService import AudioProcessingService
from transcription.services.TranscriptionConfig import TranscriptionConfig


class AudioProcessingServiceTests(TestCase):
    """Test the AudioProcessingService with instance-based configuration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
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

    @patch("transcription.services.AudioProcessingService.AudioSegment")
    def test_split_audio_file_under_limit(self, mock_audio_segment):
        """Test that small files are not split."""
        test_file = self.temp_path / "small.mp3"
        test_file.write_text("small content")  # Very small file

        # Mock AudioSegment.from_file to return a mock audio segment
        mock_audio = Mock()
        mock_audio_segment.from_file.return_value = mock_audio

        # Patch ChunkingProcessor.process to return a single AudioData
        with patch(
            "transcription.services.AudioProcessingService.ChunkingProcessor.process"
        ) as mock_process:
            from transcription.services.AudioProcessingService import AudioData

            audio_data = AudioData.from_audio_segment(
                mock_audio, character_name="TestCharacter"
            )
            mock_process.return_value = [audio_data]
            result = self.service.split_audio_file(test_file, "TestCharacter")

        # Should return a list of AudioData objects
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], AudioData)
        mock_audio_segment.from_file.assert_called_once_with(test_file)

    @patch("transcription.services.AudioProcessingService.AudioSegment")
    def test_split_audio_file_over_limit(self, mock_audio_segment):
        """Test that large files are split into chunks."""
        test_file = self.temp_path / "large.mp3"
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        test_file.write_bytes(large_content.encode())

        # Mock audio processing
        mock_audio = Mock()
        mock_audio_segment.from_file.return_value = mock_audio

        # Patch ChunkingProcessor.process to return two AudioData objects
        with patch(
            "transcription.services.AudioProcessingService.ChunkingProcessor.process"
        ) as mock_process:
            from transcription.services.AudioProcessingService import AudioData

            audio_data1 = AudioData.from_audio_segment(
                mock_audio, character_name="TestCharacter"
            )
            audio_data2 = AudioData.from_audio_segment(
                mock_audio, character_name="TestCharacter"
            )
            mock_process.return_value = [audio_data1, audio_data2]
            result = self.service.split_audio_file(test_file, "TestCharacter")

        # Should create 2 chunks (2 minutes / 1 minute per chunk)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], AudioData)
        self.assertIsInstance(result[1], AudioData)
        mock_audio_segment.from_file.assert_called_once_with(test_file)

    @patch("transcription.services.AudioProcessingService.AudioSegment")
    def test_split_audio_handles_exceptions(self, mock_audio_segment):
        """Test that splitting handles exceptions gracefully."""
        test_file = self.temp_path / "problematic.mp3"
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        test_file.write_bytes(large_content.encode())

        # Mock exception during audio processing
        mock_audio_segment.from_file.side_effect = Exception("Audio processing failed")

        result = self.service.split_audio_file(test_file, "TestCharacter")

        # Should return empty list when splitting fails
        self.assertEqual(result, [])
