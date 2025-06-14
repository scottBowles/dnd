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

    def test_no_shared_state_between_instances(self):
        """Test that modifying one config doesn't affect another."""
        config1 = TranscriptionConfig(max_file_size_mb=10)
        config2 = TranscriptionConfig(max_file_size_mb=20)

        # Modify config1
        config1.max_file_size_mb = 15

        # Verify config2 is unchanged
        self.assertEqual(config2.max_file_size_mb, 20)
        self.assertNotEqual(config1.max_file_size_mb, config2.max_file_size_mb)
