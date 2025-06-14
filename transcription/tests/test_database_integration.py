"""
Tests for database integration functionality.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from django.test import TestCase

from transcription.services import TranscriptionConfig, TranscriptionService
from transcription.models import TranscriptionSession, AudioTranscript, TranscriptChunk
from nucleus.models import GameLog


class DatabaseIntegrationTests(TestCase):
    """Test database integration functionality"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config = TranscriptionConfig(
            input_folder=self.temp_path / "input",
            output_folder=self.temp_path / "output",
            chunks_folder=self.temp_path / "chunks",
            openai_api_key="test_key",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_or_create_session_without_log(self):
        """Test creating a session without a GameLog."""
        service = TranscriptionService(self.config)

        session = service._get_or_create_session(session_notes="Test session")

        self.assertIsInstance(session, TranscriptionSession)
        self.assertIsNone(session.log)
        self.assertEqual(session.notes, "Test session")

        # Test that calling again returns the same session
        session2 = service._get_or_create_session(session_notes="Different notes")
        self.assertEqual(session.id, session2.id)

    def test_get_or_create_session_with_log(self):
        """Test creating a session with a GameLog."""
        service = TranscriptionService(self.config)

        # Create a test GameLog, bypassing Google Drive integration
        with patch("nucleus.models.GameLog.update_from_google"):
            game_log = GameLog.objects.create(title="Test Session", url="test-session")

        session = service._get_or_create_session(
            log=game_log, session_notes="Test session"
        )

        self.assertIsInstance(session, TranscriptionSession)
        self.assertEqual(session.log, game_log)
        self.assertEqual(session.notes, "Test session")

    def test_get_or_create_session_different_logs_create_different_sessions(self):
        """Test that different GameLogs create different sessions."""
        service = TranscriptionService(self.config)

        with patch("nucleus.models.GameLog.update_from_google"):
            log1 = GameLog.objects.create(title="Session 1", url="session-1")
            log2 = GameLog.objects.create(title="Session 2", url="session-2")

        session1 = service._get_or_create_session(log=log1)
        session2 = service._get_or_create_session(log=log2)

        self.assertNotEqual(session1.id, session2.id)
        self.assertEqual(session1.log, log1)
        self.assertEqual(session2.log, log2)

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

        session = service._get_or_create_session(session_notes="Test session")

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
            session=session,
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
        self.assertEqual(audio_transcript.session, session)
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
        session = service._get_or_create_session()
        audio_transcript = AudioTranscript.objects.create(
            session=session,
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

        # Create test file
        test_file = self.config.input_folder / "test_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("small audio content")

        # Mock successful API response
        mock_response = {"text": "Test transcription", "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service.process_file_with_splitting(test_file, "previous", "notes")

        self.assertTrue(result)

        # Verify JSON file was created
        output_file = self.config.output_folder / "test_player.json"
        self.assertTrue(output_file.exists())

        # Verify database records were created
        sessions = TranscriptionSession.objects.all()
        self.assertEqual(sessions.count(), 1)

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
            game_log = GameLog.objects.create(title="Test Session", url="test-session")

        # Create test file
        test_file = self.config.input_folder / "test_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("small audio content")

        # Mock successful API response
        mock_response = {"text": "Test transcription", "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            result = service.process_file_with_splitting(
                test_file, "previous", "notes", log=game_log
            )

        self.assertTrue(result)

        # Verify session is linked to the GameLog
        session = TranscriptionSession.objects.get()
        self.assertEqual(session.log, game_log)

        # Verify transcript is linked to the session
        transcript = AudioTranscript.objects.get()
        self.assertEqual(transcript.session, session)
        self.assertEqual(transcript.session.log, game_log)

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
            game_log = GameLog.objects.create(title="Test Session", url="test-session")

        # Create test audio files
        self.config.input_folder.mkdir(parents=True, exist_ok=True)
        test_files = [
            self.config.input_folder / "player1.mp3",
            self.config.input_folder / "player2.flac",
        ]

        for file in test_files:
            file.write_text("content")

        # Mock audio service and API responses
        service.audio_service = Mock()
        service.audio_service.split_audio_file.return_value = [test_files[0]]

        mock_response = {"text": "Test transcription"}
        mock_openai.Audio.transcribe.return_value = mock_response

        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            processed_count = service.process_all_files(log=game_log)

        self.assertEqual(processed_count, 2)

        # Verify all transcripts are linked to the same session and GameLog
        transcripts = AudioTranscript.objects.all()
        self.assertEqual(transcripts.count(), 2)

        for transcript in transcripts:
            self.assertEqual(transcript.session.log, game_log)

    @patch("transcription.services.openai")
    def test_database_survives_json_failure(self, mock_openai):
        """Test that database saving works even if JSON saving fails."""
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

        # Create test file
        test_file = self.config.input_folder / "test_player.mp3"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("small audio content")

        # Mock successful API response
        mock_response = {"text": "Test transcription", "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response

        # Mock JSON saving to fail but database should still work
        with patch("builtins.open", mock_open(read_data=b"fake audio")):
            with patch("transcription.services.safe_save_json", return_value=False):
                result = service.process_file_with_splitting(test_file)

        # Should return False due to JSON save failure
        self.assertFalse(result)

        # But database record should still exist
        transcripts = AudioTranscript.objects.all()
        self.assertEqual(transcripts.count(), 1)
        transcript = transcripts[0]
        self.assertEqual(transcript.transcript_text, "Test transcription")


class ModelValidationTests(TestCase):
    """Test model validation and constraints"""

    def test_transcription_session_nullable_log(self):
        """Test that TranscriptionSession can have null log."""
        session = TranscriptionSession.objects.create(notes="Test session")
        self.assertIsNone(session.log)
        session.full_clean()  # Should not raise validation error

    def test_transcription_session_with_log(self):
        """Test that TranscriptionSession can have a GameLog."""
        with patch("nucleus.models.GameLog.update_from_google"):
            game_log = GameLog.objects.create(title="Test", url="test-url")
        session = TranscriptionSession.objects.create(
            log=game_log, notes="Test session"
        )
        self.assertEqual(session.log, game_log)
        session.full_clean()  # Should not raise validation error

    def test_audio_transcript_required_fields(self):
        """Test that AudioTranscript requires certain fields."""
        session = TranscriptionSession.objects.create()

        # This should work - provide all required fields including JSON defaults
        transcript = AudioTranscript.objects.create(
            session=session,
            original_filename="test.mp3",
            character_name="TestPlayer",
            file_size_mb=1.0,
            transcript_text="Test",
            whisper_response={"text": "Test"},  # Required JSON field
            campaign_context={"characters": []},  # Required JSON field
        )
        transcript.full_clean()

    def test_transcript_chunk_foreign_key_relationship(self):
        """Test TranscriptChunk relationship to AudioTranscript."""
        session = TranscriptionSession.objects.create()
        transcript = AudioTranscript.objects.create(
            session=session,
            original_filename="test.mp3",
            character_name="TestPlayer",
            file_size_mb=1.0,
            transcript_text="Test",
        )

        chunk = TranscriptChunk.objects.create(
            transcript=transcript,
            chunk_number=1,
            filename="chunk_01.mp3",
            start_time_offset=0.0,  # Required field
            duration_seconds=60.0,  # Required field
            chunk_text="Chunk text",
        )

        # Test relationship
        self.assertEqual(chunk.transcript, transcript)
        self.assertEqual(list(transcript.chunks.all()), [chunk])

    def test_transcription_session_string_representation(self):
        """Test TranscriptionSession string representation."""
        # Test without GameLog
        session1 = TranscriptionSession.objects.create(notes="Test session")
        expected1 = f"Transcription Session {session1.id}"
        self.assertEqual(str(session1), expected1)

        # Test with GameLog
        with patch("nucleus.models.GameLog.update_from_google"):
            game_log = GameLog.objects.create(title="Test Session", url="test-session")
        session2 = TranscriptionSession.objects.create(
            log=game_log, notes="Test session"
        )
        expected2 = f"Transcription for {game_log.title}"
        self.assertEqual(str(session2), expected2)

    def test_audio_transcript_string_representation(self):
        """Test AudioTranscript string representation."""
        session = TranscriptionSession.objects.create()
        transcript = AudioTranscript.objects.create(
            session=session,
            original_filename="test_player.mp3",
            character_name="TestPlayer",
            file_size_mb=1.5,
            transcript_text="Test transcript",
        )

        expected = f"TestPlayer - test_player.mp3"
        self.assertEqual(str(transcript), expected)

    def test_transcript_chunk_string_representation(self):
        """Test TranscriptChunk string representation."""
        session = TranscriptionSession.objects.create()
        transcript = AudioTranscript.objects.create(
            session=session,
            original_filename="test_player.mp3",
            character_name="TestPlayer",
            file_size_mb=1.5,
            transcript_text="Test transcript",
        )
        chunk = TranscriptChunk.objects.create(
            transcript=transcript,
            chunk_number=1,
            filename="test_player_chunk_01.mp3",
            start_time_offset=0.0,
            duration_seconds=60.0,
            chunk_text="Chunk text",
        )

        expected = f"TestPlayer - Chunk 1"
        self.assertEqual(str(chunk), expected)

    def test_transcription_session_ordering(self):
        """Test that TranscriptionSession ordering works correctly."""
        # Create sessions in reverse chronological order
        session1 = TranscriptionSession.objects.create(notes="First")
        session2 = TranscriptionSession.objects.create(notes="Second")
        session3 = TranscriptionSession.objects.create(notes="Third")

        # Get all sessions (should be ordered by -created)
        sessions = list(TranscriptionSession.objects.all())

        # Should be in reverse chronological order (newest first)
        self.assertEqual(sessions[0], session3)
        self.assertEqual(sessions[1], session2)
        self.assertEqual(sessions[2], session1)
