import re


class TranscriptCleaner:
    """Utility for cleaning up repetitive patterns and noise in Whisper transcripts."""

    @staticmethod
    def clean_repetitive_text(text: str, max_repetitions: int = 3) -> str:
        """
        Remove repetitive patterns from transcript text.

        Args:
            text: The transcript text to clean
            max_repetitions: Maximum allowed repetitions before removal

        Returns:
            Cleaned text with repetitive patterns reduced
        """
        if not text or not text.strip():
            return text

        # Pattern 1: Exact word repetitions (e.g., "Okay. Okay. Okay.")
        # Match word followed by punctuation, repeated multiple times
        pattern1 = r"\b(\w+[.,!?]*)\s*(?:\1\s*){" + str(max_repetitions) + r",}"
        text = re.sub(
            pattern1,
            lambda m: (m.group(1) + " ") * max_repetitions,
            text,
            flags=re.IGNORECASE,
        )

        # Pattern 2: Phrase repetitions (e.g., "in the, in the, in the")
        # Match 2-4 word phrases repeated multiple times
        pattern2 = r"\b((?:\w+\s*[,.]?\s*){1,4}?)(?:\1){" + str(max_repetitions) + r",}"
        text = re.sub(
            pattern2,
            lambda m: m.group(1) * max_repetitions,
            text,
            flags=re.IGNORECASE,
        )

        # Pattern 3: Single letter repetitions (e.g., "a a a a a")
        pattern3 = r"\b(\w)\s*(?:\1\s*){" + str(max_repetitions) + r",}"
        text = re.sub(pattern3, lambda m: m.group(1) + " ", text, flags=re.IGNORECASE)

        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    @staticmethod
    def detect_low_quality_segments(text: str, threshold: float = 0.3) -> bool:
        """
        Detect if a text segment appears to be low quality based on repetition ratio.

        Args:
            text: Text to analyze
            threshold: Ratio of repetitive content that indicates low quality

        Returns:
            True if segment appears to be low quality
        """
        if not text or len(text.split()) < 10:
            return False

        words = text.lower().split()
        word_count = len(words)
        unique_words = len(set(words))

        # Calculate repetition ratio
        repetition_ratio = 1 - (unique_words / word_count)

        return repetition_ratio > threshold

    @staticmethod
    def remove_low_quality_segments(text: str, threshold: float = 0.3) -> str:
        """
        Remove segments that appear to be low quality based on repetition.

        Args:
            text: Full transcript text
            threshold: Repetition threshold for removal

        Returns:
            Text with low-quality segments removed
        """
        # Split on sentence boundaries
        sentences = re.split(r"[.!?]+", text)
        cleaned_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and not TranscriptCleaner.detect_low_quality_segments(
                sentence, threshold
            ):
                cleaned_sentences.append(sentence)

        return ". ".join(cleaned_sentences) + "." if cleaned_sentences else ""
