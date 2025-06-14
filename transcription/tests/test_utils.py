"""
Tests for utility functions.
"""

import tempfile
import json
import shutil
from pathlib import Path

from django.test import TestCase

from transcription.utils import ordinal, safe_save_json


class UtilityFunctionTests(TestCase):
    """Test utility functions from utils.py"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_save_json_success(self):
        """Test successful JSON serialization and saving."""
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
        saved_data = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_data, test_data)

    def test_safe_save_json_serialization_error(self):
        """Test handling of non-serializable data."""
        # Create non-serializable data (function object)
        test_data = {"function": lambda x: x}
        output_path = self.temp_path / "test_output.json"

        result = safe_save_json(test_data, output_path, "non-serializable data")

        self.assertFalse(result)
        self.assertFalse(output_path.exists())

    def test_safe_save_json_file_permission_error(self):
        """Test handling of file permission errors."""
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
