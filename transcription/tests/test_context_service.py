"""
Tests for CampaignContextService class.
"""

from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from transcription.services.TranscriptionConfig import TranscriptionConfig
from transcription.services.CampaignContextService import CampaignContextService


class CampaignContextServiceTests(TestCase):
    """Test the CampaignContextService with instance-based configuration."""

    def setUp(self):
        self.config = TranscriptionConfig(recent_threshold_days=30)
        self.service = CampaignContextService(self.config)

    def test_initialization_with_config(self):
        """Test that service initializes with config instance."""
        self.assertEqual(self.service.config, self.config)
        self.assertEqual(self.service.config.recent_threshold_days, 30)

    @patch("transcription.services.CampaignContextService.timezone")
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

    def test_format_context_with_max_length_zero(self):
        """Test context formatting with max_length=0."""
        context = {
            "characters": [
                {"name": "Test", "race": "Human", "recently_mentioned": True}
            ],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        result = self.service._format_context_for_prompt(context, max_length=0)
        self.assertEqual(result, "")

    def test_format_context_with_very_small_max_length(self):
        """Test context formatting with very small max_length."""
        context = {
            "characters": [
                {"name": "Test", "race": "Human", "recently_mentioned": True}
            ],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        result = self.service._format_context_for_prompt(context, max_length=10)
        self.assertLessEqual(len(result), 20)  # Allow some buffer for truncation
