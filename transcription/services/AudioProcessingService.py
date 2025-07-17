import collections
import contextlib
import math
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import webrtcvad
from pydub import AudioSegment

from .AudioProcessors_DEPRECATED import TimeOffsetMapping, TimeOffsetMappingEntry
from .TranscriptionConfig import TranscriptionConfig


@dataclass
class AudioData:
    audio: AudioSegment
    time_offset_mappings: List[TimeOffsetMapping] = field(default_factory=list)
    character_name: Optional[str] = None
    duration: Optional[float] = None  # seconds
    _temp_path: Path = field(init=False, repr=False)
    file_path: Path = field(init=False)

    def __post_init__(self):
        # Always create a temp WAV file for this audio
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        try:
            self.audio.export(temp_path, format="wav")
        finally:
            import os

            os.close(fd)
        self._temp_path = Path(temp_path)
        self.file_path = self._temp_path
        self.duration = self.audio.duration_seconds
        assert (
            self.file_path is not None
        ), "AudioData.file_path should never be None after initialization"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_temp_file()

    def convert_processed_to_original_timestamp(self, processed_time: float) -> float:
        t = processed_time
        for mapping in reversed(self.time_offset_mappings):
            if mapping:
                t = mapping.map_processed_to_original(t)
        return t

    def cleanup_temp_file(self):
        try:
            if self._temp_path and self._temp_path.exists():
                self._temp_path.unlink()
        except Exception as e:
            print(f"Warning: Failed to delete temp file {self._temp_path}: {e}")

    @classmethod
    def from_audio_segment(
        cls, audio: AudioSegment, time_offset_mappings=None, character_name=None
    ):
        return cls(
            audio=audio,
            time_offset_mappings=time_offset_mappings or [],
            character_name=character_name,
        )

    @classmethod
    def from_file(cls, file_path: Path, character_name=None):
        audio = AudioSegment.from_file(file_path)
        return cls(audio=audio, character_name=character_name)


def cleanup_audio_data_files(audio_data_list: List[AudioData]):
    """
    Utility to cleanup temp files for a list of AudioData objects.
    """
    for audio_data in audio_data_list:
        audio_data.cleanup_temp_file()


class ChunkingProcessor:
    """Splits audio into chunks and maintains time offset mapping for each chunk. Not a pipeline processor."""

    def __init__(self, chunk_duration_minutes=10):
        self.chunk_duration_s = chunk_duration_minutes * 60

    def process(self, source: AudioData) -> List[AudioData]:
        """
        Splits audio into chunks using VAD segments, writes each chunk to a temp file, and returns AudioData objects.
        """
        audio = source.audio
        character_name = source.character_name or "Unknown"

        # Ensure audio is 16kHz mono, 16-bit PCM before VAD
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

        # Export normalized audio to temp wav for VAD
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            audio.export(temp_wav.name, format="wav")
            wav_path = Path(temp_wav.name)

        # Get voiced segments from VAD
        vad_segments = VADProcessingService.extract_voiced_segments(wav_path)
        # Remove temp wav file
        wav_path.unlink(missing_ok=True)

        # Group voiced segments into chunks by total voiced duration, up to chunk_duration_s
        chunks = []
        current_chunk = []
        current_voiced_duration = 0.0
        for seg_start, seg_end in vad_segments:
            seg_len = seg_end - seg_start
            if current_voiced_duration + seg_len <= self.chunk_duration_s:
                current_chunk.append((seg_start, seg_end))
                current_voiced_duration += seg_len
            else:
                if current_chunk:
                    chunks.append(list(current_chunk))
                current_chunk = [(seg_start, seg_end)]
                current_voiced_duration = seg_len
        if current_chunk:
            chunks.append(list(current_chunk))

        audio_chunks: List[AudioData] = []
        for segs in chunks:
            # Concatenate only voiced segments for this chunk
            chunk_audio = None
            time_offset_mapping = TimeOffsetMapping([])
            processed_offset = 0.0
            for seg_start, seg_end in segs:
                seg_start_ms = int(seg_start * 1000)
                seg_end_ms = int(seg_end * 1000)
                seg_audio = audio[seg_start_ms:seg_end_ms]
                assert isinstance(
                    seg_audio, AudioSegment
                ), f"Expected AudioSegment, got {type(seg_audio)}"
                if chunk_audio is None:
                    chunk_audio = seg_audio
                else:
                    chunk_audio += seg_audio
                seg_len = seg_end - seg_start
                time_offset_mapping.add_entry(
                    TimeOffsetMappingEntry(
                        original_start=seg_start,
                        original_end=seg_end,
                        processed_start=processed_offset,
                        processed_end=processed_offset + seg_len,
                    )
                )
                processed_offset += seg_len
            # Skip this chunk if it contains no voiced audio
            if chunk_audio is None:
                continue

            time_offset_mappings = [time_offset_mapping]

            # Create AudioData instance (manages its own temp file)
            audio_chunk = AudioData.from_audio_segment(
                chunk_audio,
                time_offset_mappings=time_offset_mappings,
                character_name=character_name,
            )
            audio_chunks.append(audio_chunk)
        return audio_chunks


class VADProcessingService:
    """
    Voice Activity Detection (VAD) processing service for audio files.
    This service can be used to split audio files into chunks based on voice activity.
    """

    Frame = collections.namedtuple("Frame", ["timestamp", "data"])

    @staticmethod
    def read_wave(path: str | Path) -> tuple[bytes, int]:
        """Reads a mono 16-bit PCM WAV file. Returns (PCM bytes, sample_rate)."""
        with contextlib.closing(wave.open(str(path), "rb")) as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            pcm_data = wf.readframes(wf.getnframes())
            return pcm_data, wf.getframerate()

    @staticmethod
    def frame_generator(audio_bytes: bytes, sample_rate: int, frame_duration_ms: int):
        """Generates frames of fixed duration from PCM audio data."""
        frame_size = int(
            sample_rate * (frame_duration_ms / 1000.0) * 2
        )  # 2 bytes per sample
        offset = 0
        timestamp = 0.0
        increment = frame_duration_ms / 1000.0
        while offset + frame_size <= len(audio_bytes):
            yield VADProcessingService.Frame(
                timestamp, audio_bytes[offset : offset + frame_size]
            )
            timestamp += increment
            offset += frame_size

    @staticmethod
    def vad_collector(
        frames: list, vad: webrtcvad.Vad, padding_ms: int = 300
    ) -> list[tuple[float, float]]:
        """Groups voiced frames into segments."""
        num_padding_frames = int(padding_ms / 30)
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False
        voiced_frames: list = []
        segments: list[tuple[float, float]] = []
        start_time: float | None = None

        for frame in frames:
            is_speech = vad.is_speech(frame.data, sample_rate=16000)

            # Defensive: ensure maxlen is not None for type checker
            assert (
                ring_buffer.maxlen is not None
            ), "ring_buffer.maxlen should never be None"

            if not triggered:
                ring_buffer.append((frame, is_speech))
                if (
                    sum(1 for _frame, speech in ring_buffer if speech)
                    > 0.9 * ring_buffer.maxlen
                ):
                    triggered = True
                    start_time = ring_buffer[0][0].timestamp
                    voiced_frames.extend(f for f, _ in ring_buffer)
                    ring_buffer.clear()
            else:
                voiced_frames.append(frame)
                ring_buffer.append((frame, is_speech))
                if (
                    sum(1 for f, speech in ring_buffer if not speech)
                    > 0.9 * ring_buffer.maxlen
                ):
                    end_time = frame.timestamp + 0.03  # 30ms frame size
                    segments.append((start_time, end_time))
                    triggered = False
                    ring_buffer.clear()
                    voiced_frames = []

        # Catch any trailing speech
        if triggered and voiced_frames:
            end_time = voiced_frames[-1].timestamp + 0.03
            segments.append((start_time, end_time))

        return segments

    @staticmethod
    def extract_voiced_segments(wav_path: str | Path) -> list[tuple[float, float]]:
        audio, _ = VADProcessingService.read_wave(wav_path)
        vad = webrtcvad.Vad(3)  # 0=aggressive silence removal, 3=more inclusive
        frames = list(
            VADProcessingService.frame_generator(
                audio, sample_rate=16000, frame_duration_ms=30
            )
        )
        segments = VADProcessingService.vad_collector(frames, vad)
        return segments

    # EXAMPLE USAGE
    # if __name__ == "__main__":
    #     import sys
    #     from pathlib import Path

    #     input_path = sys.argv[1]  # e.g., chunk_03.wav
    #     print(f"Processing: {input_path}")
    #     segments = extract_voiced_segments(input_path)

    #     for start, end in segments:
    #         print(f"Voiced segment: {start:.2f} to {end:.2f} sec")

    # can do
    # @app.task(rate_limit='10/m')  # 10 requests per minute
    #     def transcribe_audio_segment(...):
    #         ...

    # either
    # - use pydub to get the segments with voice and put them together, or
    # - get each segment and have it transcribed individually, or put them together up to a certain length, or
    # - put them together when they are close together in time (the silence gap is small, like maybe < 0.5 seconds)


class AudioProcessingService:
    """Service for audio file processing and splitting using processor abstraction."""

    def __init__(self, config: TranscriptionConfig):
        self.config = config

    @staticmethod
    def get_file_size_mb(file_path: Path) -> float:
        try:
            return file_path.stat().st_size / (1024 * 1024)
        except (FileNotFoundError, OSError):
            return 0.0

    def normalize_audio(self, audio: AudioSegment, target_factor=0.8) -> AudioSegment:
        max_possible_val = audio.max_possible_amplitude
        current_max = audio.max
        if current_max > 0:
            normalization_factor = max_possible_val / current_max * target_factor
            audio = audio + (20 * math.log10(normalization_factor))
        return audio

    def split_audio_file(
        self, file_path: Path, character_name: str = "Unknown"
    ) -> List[AudioData]:
        print(f"📂 Splitting {file_path.name} into chunks using VAD...")
        try:
            audio = AudioSegment.from_file(file_path)
            source = AudioData.from_audio_segment(
                audio=audio,
                character_name=character_name,
            )
            chunking_processor = ChunkingProcessor(
                chunk_duration_minutes=self.config.chunk_duration_minutes
            )
            return chunking_processor.process(source)
        except Exception as e:
            print(f"❌ Failed to split {file_path.name}: {e}")
            return []
