import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from pydub import AudioSegment

# =====================
# Audio Processor Abstraction
# =====================


@dataclass
class TimeOffsetMappingEntry:
    original_start: float
    original_end: float
    processed_start: float
    processed_end: float


class TimeOffsetMapping:
    def __init__(self, entries: Optional[List[TimeOffsetMappingEntry]] = None):
        self.entries: List[TimeOffsetMappingEntry] = entries or []

    def add_entry(self, entry: TimeOffsetMappingEntry):
        self.entries.append(entry)

    def map_processed_to_original(self, processed_time: float) -> float:
        for entry in self.entries:
            if entry.processed_start <= processed_time <= entry.processed_end:
                segment_progress = (
                    (processed_time - entry.processed_start)
                    / (entry.processed_end - entry.processed_start)
                    if entry.processed_end > entry.processed_start
                    else 0.0
                )
                original_duration = entry.original_end - entry.original_start
                return entry.original_start + segment_progress * original_duration
        return processed_time

    @classmethod
    def identity(cls, duration: float) -> "TimeOffsetMapping":
        return cls(
            [
                TimeOffsetMappingEntry(
                    original_start=0.0,
                    original_end=duration,
                    processed_start=0.0,
                    processed_end=duration,
                )
            ]
        )


class AudioProcessor(ABC):
    """Abstract base class for audio processors."""

    @abstractmethod
    def process(self, audio: AudioSegment) -> tuple[AudioSegment, TimeOffsetMapping]:
        """
        Process the audio and return (processed_audio, time_offset_mapping).
        Returns processed audio and updated mapping.
        """
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__


# =====================
# Audio Processing Pipeline
# =====================


class AudioProcessingPipeline:
    """Pipeline for applying a sequence of AudioProcessors."""

    def __init__(self, processors: List[AudioProcessor]):
        self.processors = processors

    def process(
        self, audio: AudioSegment
    ) -> tuple[AudioSegment, List[TimeOffsetMapping]]:
        """
        Process audio through the pipeline, returning processed audio and a list of mappings (one per processor).
        """
        processed_audio = audio
        mappings: List[TimeOffsetMapping] = []
        for processor in self.processors:
            processed_audio, processor_mapping = processor.process(processed_audio)
            mappings.append(processor_mapping)
        return processed_audio, mappings


# =====================
# Concrete Audio Processors
# =====================


class NormalizationProcessor(AudioProcessor):
    """Normalizes audio levels and maintains time offset mapping (identity)."""

    def __init__(self, target_factor=0.8):
        self.target_factor = target_factor

    def process(self, audio: AudioSegment) -> tuple[AudioSegment, TimeOffsetMapping]:
        max_possible_val = audio.max_possible_amplitude
        current_max = audio.max
        if current_max > 0:
            normalization_factor = max_possible_val / current_max * self.target_factor
            audio = audio + (20 * math.log10(normalization_factor))
        original_duration_ms = len(audio)
        identity_mapping = TimeOffsetMapping(
            [
                TimeOffsetMappingEntry(
                    original_start=0.0,
                    original_end=original_duration_ms / 1000.0,
                    processed_start=0.0,
                    processed_end=original_duration_ms / 1000.0,
                )
            ]
        )
        return audio, identity_mapping


class SilenceRemovalProcessor(AudioProcessor):
    """Removes long silences from audio and maintains time offset mapping."""

    def __init__(self, silence_len=2000, silence_db_offset=16, keep_silence=500):
        self.silence_len = silence_len
        self.silence_db_offset = silence_db_offset
        self.keep_silence = keep_silence

    def process(self, audio: AudioSegment) -> tuple[AudioSegment, TimeOffsetMapping]:
        from pydub.silence import detect_silence

        original_duration_ms = len(audio)
        silence_threshold = int(audio.dBFS - self.silence_db_offset)
        silence_ranges = detect_silence(
            audio,
            min_silence_len=self.silence_len,
            silence_thresh=silence_threshold,
        )
        if silence_ranges:
            mapping = TimeOffsetMapping()
            processed_audio = AudioSegment.empty()
            processed_position_ms = 0
            segments = []
            last_end = 0
            for silence_start, silence_end in silence_ranges:
                if silence_start > last_end:
                    segments.append((last_end, silence_start))
                last_end = silence_end
            if last_end < original_duration_ms:
                segments.append((last_end, original_duration_ms))
            for segment_start, segment_end in segments:
                segment_audio = audio[segment_start:segment_end]
                segment_length_ms = segment_end - segment_start
                if processed_audio:
                    processed_audio += AudioSegment.silent(duration=self.keep_silence)
                    processed_position_ms += self.keep_silence
                processed_audio += segment_audio
                mapping.add_entry(
                    TimeOffsetMappingEntry(
                        original_start=segment_start / 1000.0,
                        original_end=segment_end / 1000.0,
                        processed_start=processed_position_ms / 1000.0,
                        processed_end=(processed_position_ms + segment_length_ms)
                        / 1000.0,
                    )
                )
                processed_position_ms += segment_length_ms
            return processed_audio, mapping
        else:
            identity_mapping = TimeOffsetMapping.identity(original_duration_ms / 1000.0)
            return audio, identity_mapping
