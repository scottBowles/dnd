"""
Response handling classes for external API integrations.
Contains classes for validating and parsing responses from external services.
"""

from typing import Any, Dict, List


class WhisperResponse:
    """
    Validates and provides clean access to OpenAI Whisper API responses.

    Handles both validation and parsing of Whisper responses in one place,
    providing safe access to text and segments data.
    """

    def __init__(self, response: Any):
        """Initialize with a Whisper API response.

        Args:
            response: The response from OpenAI Whisper API
        """
        self._raw_response = response
        self._is_valid = self._validate()

    def _validate(self) -> bool:
        """Validate that the response has expected structure."""
        if not isinstance(self._raw_response, dict):
            return False

        # Required fields for verbose_json format
        if "text" not in self._raw_response:
            return False

        # Validate segments if present (but allow malformed segments, just filter them out)
        if "segments" in self._raw_response:
            segments = self._raw_response["segments"]
            if not isinstance(segments, list):
                # Still valid, just return empty segments later
                pass

        return True

    @property
    def is_valid(self) -> bool:
        """Check if the response is valid."""
        return self._is_valid

    @property
    def text(self) -> str:
        """Get the transcribed text safely.

        Returns:
            str: The transcribed text, or empty string if not available
        """
        if not self.is_valid:
            return ""
        text_value = self._raw_response.get("text", "")
        # Handle None values gracefully
        return text_value if text_value is not None else ""

    @property
    def segments(self) -> List[Dict[str, Any]]:
        """Get the transcript segments safely.

        Returns:
            List[Dict]: List of valid segments, or empty list if not available
        """
        if not self.is_valid:
            return []

        segments = self._raw_response.get("segments", [])
        if not isinstance(segments, list):
            return []

        # Filter out malformed segments and warn if any are found
        valid_segments = []
        malformed_count = 0
        
        for segment in segments:
            if (
                isinstance(segment, dict)
                and "start" in segment
                and "end" in segment
                and "text" in segment
            ):
                valid_segments.append(segment)
            else:
                malformed_count += 1

        # Warn about malformed segments
        if malformed_count > 0:
            print(f"⚠️  Warning: {malformed_count} malformed segment(s) detected in Whisper response. "
                  f"Using {len(valid_segments)} valid segments. Consider retrying for complete segment data.")

        return valid_segments

    @property
    def raw_response(self) -> Dict[str, Any]:
        """Get the raw response data.

        Returns:
            Dict: The original response, or empty dict if invalid
        """
        if not self.is_valid:
            return {}
        return self._raw_response

    def __bool__(self) -> bool:
        """Allow truthiness testing."""
        return self.is_valid
