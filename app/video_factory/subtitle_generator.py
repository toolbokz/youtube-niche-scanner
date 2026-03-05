"""Video Factory — Step 7: Subtitle Generation.

Generates SRT subtitle files aligned to voiceover narration timestamps.
Supports optional subtitle embedding into the video.
"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import (
    VideoScript,
    VoiceoverResult,
    SubtitleEntry,
    SubtitleResult,
)

logger = get_logger(__name__)

# Max characters per subtitle line
_MAX_CHARS_PER_LINE = 42
# Max duration per subtitle block (seconds)
_MAX_SUBTITLE_DURATION = 5.0
# Min duration per subtitle block (seconds)
_MIN_SUBTITLE_DURATION = 1.0


class SubtitleGenerator:
    """Generate subtitles from script and voiceover timestamps."""

    async def generate(
        self,
        script: VideoScript,
        voiceover: VoiceoverResult,
        output_dir: str,
        embed_in_video: bool = False,
        video_path: str = "",
    ) -> SubtitleResult:
        """Generate SRT subtitles aligned to the voiceover.

        Parameters
        ----------
        script : VideoScript
            The video script with narration text.
        voiceover : VoiceoverResult
            Voiceover result with section timestamps.
        output_dir : str
            Directory for output files.
        embed_in_video : bool
            Whether to burn subtitles into the video file.
        video_path : str
            Path to video file (required if embed_in_video is True).

        Returns
        -------
        SubtitleResult
            Subtitle entries and SRT file path.
        """
        logger.info("subtitle_generation_start", sections=len(script.sections))

        os.makedirs(output_dir, exist_ok=True)
        srt_path = os.path.join(output_dir, "subtitles.srt")

        # Generate subtitle entries from script + timestamps
        entries = self._generate_entries(script, voiceover)

        # Write SRT file
        self._write_srt(entries, srt_path)

        # Optionally embed subtitles into video
        if embed_in_video and video_path and os.path.exists(video_path):
            await self._embed_subtitles(srt_path, video_path)

        result = SubtitleResult(
            srt_path=srt_path,
            entries=entries,
            total_entries=len(entries),
            language="en",
        )

        logger.info(
            "subtitle_generation_done",
            entries=len(entries),
            path=srt_path,
        )
        return result

    def _generate_entries(
        self,
        script: VideoScript,
        voiceover: VoiceoverResult,
    ) -> list[SubtitleEntry]:
        """Generate subtitle entries by splitting narration into timed chunks."""
        entries: list[SubtitleEntry] = []
        index = 1

        for section in script.sections:
            # Find matching timestamp
            ts = self._find_timestamp(section.section_type, voiceover)

            if ts:
                section_start = ts.get("start_time", 0.0)
                section_end = ts.get("end_time", section_start + section.duration_seconds)
            else:
                # Estimate from accumulated duration
                section_start = sum(
                    e.end_time - e.start_time for e in entries
                ) if entries else 0.0
                section_end = section_start + float(section.duration_seconds)

            # Split section content into subtitle chunks
            sentences = self._split_into_sentences(section.content)
            if not sentences:
                continue

            # Distribute time across sentences proportionally by word count
            total_words = sum(len(s.split()) for s in sentences)
            if total_words == 0:
                continue

            section_duration = section_end - section_start
            current_time = section_start

            for sentence in sentences:
                word_count = len(sentence.split())
                sentence_duration = (word_count / total_words) * section_duration
                sentence_duration = max(_MIN_SUBTITLE_DURATION,
                                        min(_MAX_SUBTITLE_DURATION * 2, sentence_duration))

                # Break long sentences into subtitle-sized chunks
                chunks = self._break_into_chunks(sentence)

                chunk_duration = sentence_duration / max(len(chunks), 1)

                for chunk in chunks:
                    end_time = min(current_time + chunk_duration, section_end)
                    entries.append(SubtitleEntry(
                        index=index,
                        start_time=round(current_time, 3),
                        end_time=round(end_time, 3),
                        text=chunk.strip(),
                    ))
                    index += 1
                    current_time = end_time

        return entries

    @staticmethod
    def _find_timestamp(section_type: str, voiceover: VoiceoverResult) -> dict | None:
        """Find voiceover timestamp for a section type."""
        for ts in voiceover.sections_timestamps:
            if ts.get("section_type") == section_type:
                return ts
        return None

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        # Split on sentence-ending punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def _break_into_chunks(text: str) -> list[str]:
        """Break text into subtitle-sized chunks."""
        if len(text) <= _MAX_CHARS_PER_LINE * 2:
            return [text]

        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 > _MAX_CHARS_PER_LINE * 2:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks if chunks else [text]

    @staticmethod
    def _write_srt(entries: list[SubtitleEntry], path: str) -> None:
        """Write subtitle entries to an SRT file."""
        lines: list[str] = []
        for entry in entries:
            start = _format_srt_time(entry.start_time)
            end = _format_srt_time(entry.end_time)
            lines.append(f"{entry.index}")
            lines.append(f"{start} --> {end}")
            lines.append(entry.text)
            lines.append("")  # blank line separator

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    async def _embed_subtitles(srt_path: str, video_path: str) -> bool:
        """Burn subtitles into the video using ffmpeg."""
        try:
            output_path = video_path.replace(".mp4", "_subtitled.mp4")
            # Use the subtitles filter with styling
            srt_escaped = srt_path.replace("\\", "/").replace(":", r"\:")

            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"subtitles={srt_escaped}:force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'",
                "-c:a", "copy",
                output_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

            if proc.returncode == 0:
                # Replace original with subtitled version
                os.replace(output_path, video_path)
                return True

        except Exception as exc:
            logger.warning("subtitle_embed_failed", error=str(exc))

        return False


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
