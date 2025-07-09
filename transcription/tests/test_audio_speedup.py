"""
Tests for audio speed-up functionality in AudioProcessingService.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from django.test import TestCase
from transcription.services import TranscriptionConfig, AudioProcessingService


class AudioSpeedUpTests(TestCase):
    """Test audio speed-up functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_speedup_configuration(self):
        """Test that speed-up configuration is properly set."""
        # Test default configuration
        config = TranscriptionConfig()
        self.assertTrue(config.enable_audio_speedup)
        self.assertEqual(config.audio_speedup_factor, 2.0)
        
        # Test custom configuration
        config_custom = TranscriptionConfig(
            enable_audio_speedup=False,
            audio_speedup_factor=1.5
        )
        self.assertFalse(config_custom.enable_audio_speedup)
        self.assertEqual(config_custom.audio_speedup_factor, 1.5)

    @patch('transcription.services.AudioSegment')
    def test_speedup_applied_with_silence_detection(self, mock_audio_segment):
        """Test that speed-up is applied when silence is detected."""
        # Mock audio segment
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=5000)  # 5 seconds
        mock_audio.max_possible_amplitude = 32767
        mock_audio.max = 16383
        mock_audio.dBFS = -20
        
        # Mock speedup method
        mock_sped_up = Mock()
        mock_sped_up.__len__ = Mock(return_value=2500)  # 2.5 seconds after 2x speedup
        mock_audio.speedup = Mock(return_value=mock_sped_up)
        
        # Mock silence detection to return empty (no silence)
        with patch('transcription.services.detect_silence', return_value=[]):
            config = TranscriptionConfig(
                enable_audio_speedup=True,
                audio_speedup_factor=2.0,
                enable_audio_preprocessing=True
            )
            service = AudioProcessingService(config)
            
            processed_audio, time_mapping = service.preprocess_audio(mock_audio)
            
            # Verify speedup was called
            mock_audio.speedup.assert_called_once_with(playback_speed=2.0)
            
            # Verify time mapping accounts for speed-up
            self.assertEqual(len(time_mapping), 1)
            mapping = time_mapping[0]
            self.assertEqual(mapping['original_start'], 0.0)
            self.assertEqual(mapping['original_end'], 5.0)
            self.assertEqual(mapping['processed_start'], 0.0)
            self.assertEqual(mapping['processed_end'], 2.5)  # 5.0 / 2.0

    @patch('transcription.services.AudioSegment')
    def test_speedup_disabled(self, mock_audio_segment):
        """Test that speed-up is not applied when disabled."""
        # Mock audio segment
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=5000)  # 5 seconds
        mock_audio.max_possible_amplitude = 32767
        mock_audio.max = 16383
        mock_audio.dBFS = -20
        
        # Mock silence detection to return empty (no silence)
        with patch('transcription.services.detect_silence', return_value=[]):
            config = TranscriptionConfig(
                enable_audio_speedup=False,
                audio_speedup_factor=2.0,
                enable_audio_preprocessing=True
            )
            service = AudioProcessingService(config)
            
            processed_audio, time_mapping = service.preprocess_audio(mock_audio)
            
            # Verify speedup was NOT called
            mock_audio.speedup.assert_not_called()
            
            # Verify time mapping is identity (no speed-up)
            self.assertEqual(len(time_mapping), 1)
            mapping = time_mapping[0]
            self.assertEqual(mapping['original_start'], 0.0)
            self.assertEqual(mapping['original_end'], 5.0)
            self.assertEqual(mapping['processed_start'], 0.0)
            self.assertEqual(mapping['processed_end'], 5.0)  # No change

    def test_convert_processed_to_original_with_speedup(self):
        """Test timestamp conversion with speed-up mapping."""
        # Create a time mapping that represents 2x speed-up
        time_mapping = [
            {
                'original_start': 0.0,
                'original_end': 10.0,
                'processed_start': 0.0,
                'processed_end': 5.0,  # 10 seconds compressed to 5 seconds
            }
        ]
        
        # Test conversion at various points
        service = AudioProcessingService(TranscriptionConfig())
        
        # Test at beginning
        original_time = service.convert_processed_to_original_timestamp(0.0, time_mapping)
        self.assertEqual(original_time, 0.0)
        
        # Test at middle
        original_time = service.convert_processed_to_original_timestamp(2.5, time_mapping)
        self.assertEqual(original_time, 5.0)
        
        # Test at end
        original_time = service.convert_processed_to_original_timestamp(5.0, time_mapping)
        self.assertEqual(original_time, 10.0)

    def test_convert_chunk_processed_to_original_with_speedup(self):
        """Test chunk timestamp conversion with speed-up."""
        # Create a time mapping that represents 2x speed-up for a chunk
        chunk_preprocessing_mapping = [
            {
                'original_start': 0.0,
                'original_end': 5.0,
                'processed_start': 0.0,
                'processed_end': 2.5,  # 5 seconds compressed to 2.5 seconds
            }
        ]
        
        chunk_start_time_s = 10.0  # Chunk starts at 10 seconds in original file
        
        service = AudioProcessingService(TranscriptionConfig())
        
        # Test conversion at chunk middle
        processed_time = 1.25  # Middle of processed chunk
        original_time = service.convert_chunk_processed_to_original_timestamp(
            processed_time, chunk_start_time_s, chunk_preprocessing_mapping
        )
        
        # Should be: chunk_start + (processed_time * speedup_factor)
        # = 10.0 + (1.25 * 2.0) = 12.5
        self.assertEqual(original_time, 12.5)

    @patch('transcription.services.AudioSegment')
    def test_speedup_error_handling(self, mock_audio_segment):
        """Test error handling when speed-up fails."""
        # Mock audio segment
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=5000)  # 5 seconds
        mock_audio.max_possible_amplitude = 32767
        mock_audio.max = 16383
        mock_audio.dBFS = -20
        
        # Mock speedup to raise an exception
        mock_audio.speedup = Mock(side_effect=Exception("Speed-up failed"))
        
        # Mock silence detection to return empty (no silence)
        with patch('transcription.services.detect_silence', return_value=[]):
            config = TranscriptionConfig(
                enable_audio_speedup=True,
                audio_speedup_factor=2.0,
                enable_audio_preprocessing=True
            )
            service = AudioProcessingService(config)
            
            # This should not raise an exception, but should fallback to original
            processed_audio, time_mapping = service.preprocess_audio(mock_audio)
            
            # Should return original audio with identity mapping
            self.assertEqual(processed_audio, mock_audio)
            self.assertEqual(len(time_mapping), 1)
            mapping = time_mapping[0]
            self.assertEqual(mapping['original_start'], 0.0)
            self.assertEqual(mapping['original_end'], 5.0)
            self.assertEqual(mapping['processed_start'], 0.0)
            self.assertEqual(mapping['processed_end'], 5.0)