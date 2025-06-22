"""
Tests for edge cases, error handling, and regression scenarios.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import TestCase

from transcription.services import (
    TranscriptionConfig,
    TranscriptionService,
    CampaignContextService,
    AudioProcessingService,
)
from transcription.responses import WhisperResponse


class ErrorHandlingTests(TestCase):
    """Test error handling scenarios across the system"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            openai_api_key="test_key",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class EdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            openai_api_key="test_key",
        )

    def tearDown(self):
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

    def test_audio_processing_get_file_size_with_zero_size_file(self):
        """Test file size calculation with zero-byte file."""
        zero_file = self.temp_path / "empty.mp3"
        zero_file.touch()  # Create empty file

        size = AudioProcessingService.get_file_size_mb(zero_file)
        self.assertEqual(size, 0.0)

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
        shutil.rmtree(self.temp_dir, ignore_errors=True)

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


class IntegrationTests(TestCase):
    """Integration tests for the entire transcription system."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multiple_config_instances_independence(self):
        """Test that multiple config instances don't interfere with each other."""
        config1 = TranscriptionConfig(max_file_size_mb=10)
        config2 = TranscriptionConfig(max_file_size_mb=25)

        # Verify configs are independent
        self.assertNotEqual(config1.max_file_size_mb, config2.max_file_size_mb)

    def test_no_shared_state_between_instances(self):
        """Test that modifying one config doesn't affect another."""
        config1 = TranscriptionConfig(max_file_size_mb=10)
        config2 = TranscriptionConfig(max_file_size_mb=20)

        # Modify config1
        config1.max_file_size_mb = 15

        # Verify config2 is unchanged
        self.assertEqual(config2.max_file_size_mb, 20)
        self.assertNotEqual(config1.max_file_size_mb, config2.max_file_size_mb)

    @patch("transcription.services.openai")
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
