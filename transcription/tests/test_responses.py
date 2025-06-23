"""
Tests for WhisperResponse class.
"""

from django.test import TestCase

from transcription.responses import WhisperResponse


class WhisperResponseTests(TestCase):
    """Test the WhisperResponse class."""

    def test_successful_response(self):
        """Test handling of a successful Whisper response."""
        response_data = {
            "text": "Hello world",
            "segments": [{"start": 0, "end": 1, "text": "Hello"}],
        }
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)
        self.assertEqual(response.text, "Hello world")
        self.assertEqual(len(response.segments), 1)

    def test_empty_response(self):
        """Test handling of an empty response."""
        response = WhisperResponse({})

        self.assertFalse(response.is_valid)
        self.assertEqual(response.text, "")
        self.assertEqual(response.segments, [])

    def test_invalid_response_structure(self):
        """Test handling of an invalid response structure."""
        response = WhisperResponse({"unexpected_key": "value"})

        self.assertFalse(response.is_valid)
        self.assertEqual(response.text, "")
        self.assertEqual(response.segments, [])

    def test_partial_response(self):
        """Test handling of a partially valid response."""
        response_data = {"text": "Partial response"}
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)
        self.assertEqual(response.text, "Partial response")
        self.assertEqual(response.segments, [])

    def test_segment_parsing(self):
        """Test parsing of segments in the response."""
        response_data = {
            "text": "Hello world",
            "segments": [
                {"start": 0, "end": 1, "text": "Hello"},
                {"start": 1, "end": 2, "text": "world"},
            ],
        }
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)
        self.assertEqual(len(response.segments), 2)
        self.assertEqual(response.segments[0]["text"], "Hello")
        self.assertEqual(response.segments[1]["text"], "world")

    def test_response_with_malformed_segments(self):
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

    def test_response_with_non_list_segments(self):
        """Test WhisperResponse handling when segments is not a list."""
        response_data = {"text": "Hello world", "segments": "not a list"}
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)  # Still valid due to text
        self.assertEqual(response.text, "Hello world")
        self.assertEqual(response.segments, [])  # Should return empty list

    def test_response_truthiness(self):
        """Test WhisperResponse __bool__ method."""
        valid_response = WhisperResponse({"text": "Hello"})
        invalid_response = WhisperResponse({})

        self.assertTrue(bool(valid_response))
        self.assertFalse(bool(invalid_response))

    def test_response_with_empty_text(self):
        """Test WhisperResponse with empty text field."""
        response_data = {"text": "", "segments": []}
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)
        self.assertEqual(response.text, "")
        self.assertEqual(response.segments, [])

    def test_response_with_none_values(self):
        """Test WhisperResponse with None values."""
        response_data = {"text": None, "segments": None}
        response = WhisperResponse(response_data)

        self.assertTrue(response.is_valid)  # None text should be valid structure
        self.assertEqual(response.text, "")  # Should handle None gracefully
        self.assertEqual(response.segments, [])

    def test_raw_response_invalid(self):
        """Test raw_response property with invalid response."""
        invalid_response = WhisperResponse("not a dict")

        self.assertFalse(invalid_response.is_valid)
        self.assertEqual(invalid_response.raw_response, {})
