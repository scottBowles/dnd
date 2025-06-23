"""
Tests for TranscriptionConfig class.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from transcription.services import TranscriptionConfig


class TranscriptionConfigTests(TestCase):
    """Test the TranscriptionConfig class instance-based configuration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        # Clean up temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_initialization(self):
        """Test that config initializes with default values."""
        config = TranscriptionConfig()

        self.assertEqual(config.max_file_size_mb, 20)
        self.assertEqual(config.chunk_duration_minutes, 10)
        self.assertEqual(config.delay_between_requests, 21)
        self.assertEqual(config.recent_threshold_days, 180)
        self.assertEqual(
            config.audio_extensions, [".flac", ".wav", ".aac", ".m4a", ".mp3"]
        )

    def test_custom_initialization(self):
        """Test that config can be initialized with custom values."""
        config = TranscriptionConfig(
            max_file_size_mb=15,
            chunk_duration_minutes=5,
            delay_between_requests=10,
            recent_threshold_days=90,
            openai_api_key="test_key",
        )

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
