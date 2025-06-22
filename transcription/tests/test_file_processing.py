"""
Tests for file processing and splitting functionality.
"""

from unittest.mock import Mock, patch

from django.test import TestCase

from nucleus.models import GameLog, SessionAudio
from transcription.models import AudioTranscript
from transcription.services import TranscriptionConfig, TranscriptionService


class ProcessSessionAudioTests(TestCase):
    """Test the model-driven process_session_audio() API."""

    def setUp(self):
        patcher = patch("nucleus.models.GameLog.update_from_google")
        self.addCleanup(patcher.stop)
        self.mock_update_from_google = patcher.start()
        self.gamelog = GameLog.objects.create(title="Test Session", url="test-session")
        self.session_audio = SessionAudio.objects.create(
            gamelog=self.gamelog,
            original_filename="test_player.mp3",
            file="audio/test_player.mp3",
        )

    @patch("transcription.services.openai")
    def test_process_session_audio_success(self, mock_openai):
        """Test successful processing of a SessionAudio (no splitting)."""
        service = TranscriptionService()
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {}
        service.context_service.get_formatted_context.return_value = "Test context"

        # Mock file chunks and OpenAI response
        self.session_audio.file.chunks = Mock(return_value=[b"audio data"])
        mock_openai.Audio.transcribe.return_value = {
            "text": "Test transcription",
            "segments": [],
        }

        result = service.process_session_audio(self.session_audio, "previous", "notes")
        self.assertTrue(result)
        mock_openai.Audio.transcribe.assert_called_once()
        transcript = AudioTranscript.objects.get(session_audio=self.session_audio)
        self.assertEqual(transcript.transcript_text, "Test transcription")

    @patch("transcription.services.openai")
    def test_process_session_audio_api_failure(self, mock_openai):
        """Test handling of API failure for SessionAudio."""
        service = TranscriptionService()
        service.context_service = Mock()
        service.context_service.get_formatted_context.return_value = "Test context"
        self.session_audio.file.chunks = Mock(return_value=[b"audio data"])
        mock_openai.Audio.transcribe.side_effect = Exception("API Error")
        result = service.process_session_audio(self.session_audio)
        self.assertFalse(result)
        self.assertFalse(
            AudioTranscript.objects.filter(session_audio=self.session_audio).exists()
        )

    @patch("transcription.services.time.sleep")
    @patch("transcription.services.openai")
    def test_process_session_audio_with_splitting(self, mock_openai, mock_sleep):
        """Test processing of SessionAudio that needs splitting."""
        import tempfile
        from pathlib import Path
        service = TranscriptionService()
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {}
        service.context_service.get_formatted_context.return_value = "Test context"
        # Mock file chunks
        self.session_audio.file.chunks = Mock(return_value=[b"audio data"])
        # Create real temp files for chunk mocks
        temp_chunk1 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_chunk1.write(b"chunk1 data")
        temp_chunk1.flush()
        temp_chunk1_path = Path(temp_chunk1.name)
        temp_chunk1.close()
        temp_chunk2 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_chunk2.write(b"chunk2 data")
        temp_chunk2.flush()
        temp_chunk2_path = Path(temp_chunk2.name)
        temp_chunk2.close()
        service.audio_service = Mock()
        service.audio_service.split_audio_file.return_value = [temp_chunk1_path, temp_chunk2_path]
        # Mock OpenAI responses for chunks
        mock_openai.Audio.transcribe.side_effect = [
            {"text": "Chunk 1 transcription", "segments": [{"end": 60}]},
            {"text": "Chunk 2 transcription", "segments": [{"end": 120}]},
        ]
        result = service.process_session_audio(self.session_audio, "previous", "notes")
        self.assertTrue(result)
        transcript = AudioTranscript.objects.get(session_audio=self.session_audio)
        self.assertTrue(transcript.was_split)
        self.assertEqual(transcript.num_chunks, 2)
        self.assertIn("Chunk 1 transcription", transcript.transcript_text)
        self.assertIn("Chunk 2 transcription", transcript.transcript_text)
        # Clean up temp files
        temp_chunk1_path.unlink()
        temp_chunk2_path.unlink()

    @patch("transcription.services.time.sleep")
    @patch("transcription.services.openai")
    def test_process_session_audio_partial_failure(self, mock_openai, mock_sleep):
        """Test handling when some chunks fail during splitting."""
        service = TranscriptionService()
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {}
        service.context_service.get_formatted_context.return_value = "Test context"
        self.session_audio.file.chunks = Mock(return_value=[b"audio data"])
        chunk1 = Mock(name="chunk1", name_attr="chunk1.mp3")
        chunk2 = Mock(name="chunk2", name_attr="chunk2.mp3")
        service.audio_service = Mock()
        service.audio_service.split_audio_file.return_value = [chunk1, chunk2]
        mock_openai.Audio.transcribe.side_effect = [
            {"text": "Chunk 1 transcription", "segments": [{"end": 60}]},
            Exception("API Error for chunk 2"),
        ]
        result = service.process_session_audio(self.session_audio)
        self.assertFalse(result)
        self.assertFalse(AudioTranscript.objects.filter(session_audio=self.session_audio).exists())
