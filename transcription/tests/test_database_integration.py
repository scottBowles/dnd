"""
Tests for database integration functionality.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from django.test import TestCase

from transcription.services import TranscriptionConfig, TranscriptionService
from transcription.models import AudioTranscript, TranscriptChunk
from nucleus.models import GameLog, SessionAudio


class DatabaseIntegrationTests(TestCase):
    """Test database integration functionality"""

    def setUp(self):
        patcher = patch("nucleus.models.GameLog.update_from_google")
        self.addCleanup(patcher.stop)
        self.mock_update_from_google = patcher.start()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            openai_api_key="test_key",
        )
        # Create a dummy GameLog and SessionAudio for all tests
        self.gamelog = GameLog.objects.create(title="Test Session", url="test-session")
        self.session_audio = SessionAudio.objects.create(
            gamelog=self.gamelog,
            file="audio/test.mp3",
            original_filename="test.mp3",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("transcription.services.openai")
    def test_save_audio_transcript_creates_database_record(self, mock_openai):
        """Test that _save_audio_transcript creates proper database records."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {
            "characters": [{"name": "Gandalf", "race": "Wizard"}],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        # Create test file
        test_file = self.temp_path / "test_player.mp3"
        test_file.write_text("fake audio content")

        # Create mock whisper response
        mock_response_data = {
            "text": "Test transcription",
            "segments": [{"start": 0, "end": 5, "text": "Test"}],
        }
        from transcription.responses import WhisperResponse

        whisper_response = WhisperResponse(mock_response_data)

        audio_transcript = service._save_audio_transcript(
            session_audio=self.session_audio,
            file_path=test_file,
            character_name="TestPlayer",
            file_size_mb=1.5,
            whisper_response=whisper_response,
            was_split=False,
            num_chunks=1,
            processing_time=10.5,
        )

        # Verify database record was created
        self.assertIsInstance(audio_transcript, AudioTranscript)
        self.assertEqual(audio_transcript.original_filename, "test_player.mp3")
        self.assertEqual(audio_transcript.character_name, "TestPlayer")
        self.assertEqual(audio_transcript.file_size_mb, 1.5)
        self.assertEqual(audio_transcript.transcript_text, "Test transcription")
        self.assertEqual(audio_transcript.whisper_response, mock_response_data)
        self.assertFalse(audio_transcript.was_split)
        self.assertEqual(audio_transcript.num_chunks, 1)
        self.assertEqual(audio_transcript.processing_time_seconds, 10.5)
        self.assertIn("characters", audio_transcript.campaign_context)

    @patch("transcription.services.openai")
    def test_save_transcript_chunks_creates_database_records(self, mock_openai):
        """Test that _save_transcript_chunks creates proper database records."""
        service = TranscriptionService(self.config)

        # Create session and audio transcript
        audio_transcript = AudioTranscript.objects.create(
            session_audio=self.session_audio,
            original_filename="test.mp3",
            character_name="TestPlayer",
            file_size_mb=2.0,
            transcript_text="Combined transcript",
            was_split=True,
            num_chunks=2,
        )

        # Create mock combined transcript data
        combined_transcript = {
            "text": "Chunk 1 text. Chunk 2 text.",
            "chunks": [
                {
                    "text": "Chunk 1 text",
                    "segments": [{"start": 0, "end": 5, "text": "Chunk 1"}],
                },
                {
                    "text": "Chunk 2 text",
                    "segments": [{"start": 0, "end": 3, "text": "Chunk 2"}],
                },
            ],
        }

        chunk_paths = [
            self.temp_path / "chunk_01.mp3",
            self.temp_path / "chunk_02.mp3",
        ]

        service._save_transcript_chunks(
            audio_transcript, combined_transcript, chunk_paths
        )

        # Verify chunk records were created
        chunks = TranscriptChunk.objects.filter(transcript=audio_transcript).order_by(
            "chunk_number"
        )
        self.assertEqual(chunks.count(), 2)

        # Verify first chunk
        chunk1 = chunks[0]
        self.assertEqual(chunk1.chunk_number, 1)
        self.assertEqual(chunk1.filename, "chunk_01.mp3")
        self.assertEqual(chunk1.start_time_offset, 0)
        self.assertEqual(chunk1.chunk_text, "Chunk 1 text")

        # Verify second chunk
        chunk2 = chunks[1]
        self.assertEqual(chunk2.chunk_number, 2)
        self.assertEqual(chunk2.filename, "chunk_02.mp3")
        self.assertEqual(
            chunk2.start_time_offset, service.config.chunk_duration_minutes * 60
        )
        self.assertEqual(chunk2.chunk_text, "Chunk 2 text")

    @patch("transcription.services.openai")
    def test_process_file_with_splitting_saves_to_database_and_json(self, mock_openai):
        """Test that processing saves data to both database and JSON files."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }
        service.context_service.get_formatted_context.return_value = "Test context"

        # Create test file and SessionAudio
        test_file = self.temp_path / "test_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("small audio content")
        session_audio = SessionAudio.objects.create(
            gamelog=self.gamelog,
            file="audio/test_player.mp3",
            original_filename="test_player.mp3",
        )
        # Mock successful API response
        mock_response = {"text": "Test transcription", "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response
        session_audio.file.chunks = Mock(return_value=[b"fake audio"])
        result = service.process_session_audio(session_audio, "previous", "notes")
        self.assertTrue(result)
        # Verify database records were created
        transcripts = AudioTranscript.objects.all()
        self.assertEqual(transcripts.count(), 1)
        transcript = transcripts[0]
        self.assertEqual(transcript.character_name, "test_player")
        self.assertEqual(transcript.transcript_text, "Test transcription")
        self.assertFalse(transcript.was_split)

    @patch("transcription.services.openai")
    def test_process_file_with_log_parameter(self, mock_openai):
        """Test processing with a GameLog parameter."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }
        service.context_service.get_formatted_context.return_value = "Test context"
        # Create test GameLog, bypassing Google Drive integration
        with patch("nucleus.models.GameLog.update_from_google"):
            game_log = GameLog.objects.create(
                title="Test Session 2", url="test-session-2"
            )
        # Create test file and SessionAudio
        test_file = self.temp_path / "test_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("small audio content")
        session_audio = SessionAudio.objects.create(
            gamelog=game_log,
            file="audio/test_player.mp3",
            original_filename="test_player.mp3",
        )
        # Mock successful API response
        mock_response = {"text": "Test transcription", "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response
        session_audio.file.chunks = Mock(return_value=[b"fake audio"])
        result = service.process_session_audio(session_audio, "previous", "notes")
        self.assertTrue(result)
        # Verify transcript is linked to the session
        transcript = AudioTranscript.objects.get()
        self.assertEqual(transcript.session_audio, session_audio)

    @patch("transcription.services.openai")
    def test_process_all_files_with_log_parameter(self, mock_openai):
        """Test process_all_files with GameLog parameter."""
        service = TranscriptionService(self.config)
        service.context_service = Mock()
        service.context_service.get_campaign_context.return_value = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }
        service.context_service.get_formatted_context.return_value = "Test context"
        # Create test GameLog, bypassing Google Drive integration
        with patch("nucleus.models.GameLog.update_from_google"):
            game_log = GameLog.objects.create(
                title="Test Session 3", url="test-session-3"
            )
        # Create test audio files and SessionAudio
        test_files = [
            self.temp_path / "player1.mp3",
            self.temp_path / "player2.flac",
        ]
        session_audios = []
        for file in test_files:
            file.write_text("content")
            sa = SessionAudio.objects.create(
                gamelog=game_log,
                file=f"audio/{file.name}",
                original_filename=file.name,
            )
            sa.file.chunks = Mock(return_value=[b"fake audio"])
            session_audios.append(sa)
        # Mock audio service and API responses
        mock_response = {"text": "Test transcription"}
        mock_openai.Audio.transcribe.return_value = mock_response
        processed_count = 0
        for sa in session_audios:
            if service.process_session_audio(sa):
                processed_count += 1
        self.assertEqual(processed_count, 2)
        # Verify all transcripts are linked to the correct session and GameLog
        transcripts = AudioTranscript.objects.all()
        self.assertEqual(transcripts.count(), 2)
        for transcript, sa in zip(transcripts, session_audios):
            self.assertEqual(transcript.session_audio, sa)
