"""Video Factory — Step 3: Voiceover Generation.

Converts a script into narration audio using AI voice synthesis.
Supports Google Cloud TTS, ElevenLabs, and local (pyttsx3/edge-tts) providers.
"""
from __future__ import annotations

import asyncio
import os
import struct
import wave
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import VideoScript, VoiceConfig, VoiceoverResult

logger = get_logger(__name__)


class VoiceGenerator:
    """Generate voiceover audio from a video script."""

    def __init__(self, config: VoiceConfig | None = None) -> None:
        self.config = config or VoiceConfig()

    async def generate(
        self,
        script: VideoScript,
        output_dir: str,
    ) -> VoiceoverResult:
        """Generate voiceover audio for the entire script.

        Parameters
        ----------
        script : VideoScript
            The video script with narration sections.
        output_dir : str
            Directory to write audio files.

        Returns
        -------
        VoiceoverResult
            Information about the generated audio file.
        """
        logger.info(
            "voiceover_generation_start",
            provider=self.config.provider,
            sections=len(script.sections),
        )

        os.makedirs(output_dir, exist_ok=True)

        # Combine all narration text
        full_text = "\n\n".join(
            section.content for section in script.sections if section.content.strip()
        )

        output_path = os.path.join(output_dir, "voiceover.wav")

        provider = self.config.provider.lower()

        if provider == "elevenlabs":
            result = await self._generate_elevenlabs(full_text, output_path, script)
        elif provider == "edge_tts":
            result = await self._generate_edge_tts(full_text, output_path, script)
        elif provider == "google_tts":
            result = await self._generate_google_tts(full_text, output_path, script)
        else:
            # Fallback: generate a silent placeholder WAV
            result = await self._generate_placeholder(full_text, output_path, script)

        logger.info(
            "voiceover_generation_done",
            provider=provider,
            duration=result.duration_seconds,
            path=result.audio_path,
        )
        return result

    async def _generate_google_tts(
        self,
        text: str,
        output_path: str,
        script: VideoScript,
    ) -> VoiceoverResult:
        """Generate voiceover using Google Cloud Text-to-Speech."""
        try:
            from google.cloud import texttospeech  # type: ignore[import]

            client = texttospeech.TextToSpeechClient()

            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=self.config.voice_name,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=self.config.speaking_rate,
                pitch=self.config.pitch,
                sample_rate_hertz=24000,
            )

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config,
                ),
            )

            with open(output_path, "wb") as f:
                f.write(response.audio_content)

            duration = len(response.audio_content) / (24000 * 2)  # 16-bit mono

            return VoiceoverResult(
                audio_path=output_path,
                duration_seconds=round(duration, 2),
                provider="google_tts",
                sample_rate=24000,
                sections_timestamps=self._estimate_timestamps(script, duration),
            )

        except Exception as exc:
            logger.warning("google_tts_failed", error=str(exc))
            return await self._generate_placeholder(text, output_path, script)

    async def _generate_elevenlabs(
        self,
        text: str,
        output_path: str,
        script: VideoScript,
    ) -> VoiceoverResult:
        """Generate voiceover using ElevenLabs API."""
        try:
            import httpx

            api_key = self.config.elevenlabs_api_key or os.environ.get("ELEVENLABS_API_KEY", "")
            voice_id = self.config.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"

            if not api_key:
                raise ValueError("ElevenLabs API key not configured")

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key,
            }
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            }

            mp3_path = output_path.replace(".wav", ".mp3")

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                with open(mp3_path, "wb") as f:
                    f.write(response.content)

            # Convert MP3 to WAV using ffmpeg if available
            wav_path = await self._convert_to_wav(mp3_path, output_path)

            # Estimate duration from file size (~128kbps MP3)
            file_size = os.path.getsize(mp3_path)
            duration = file_size / (128 * 1024 / 8)

            return VoiceoverResult(
                audio_path=wav_path,
                duration_seconds=round(duration, 2),
                provider="elevenlabs",
                sample_rate=24000,
                sections_timestamps=self._estimate_timestamps(script, duration),
            )

        except Exception as exc:
            logger.warning("elevenlabs_failed", error=str(exc))
            return await self._generate_placeholder(text, output_path, script)

    async def _generate_edge_tts(
        self,
        text: str,
        output_path: str,
        script: VideoScript,
    ) -> VoiceoverResult:
        """Generate voiceover using Microsoft Edge TTS (free, no API key)."""
        try:
            import edge_tts  # type: ignore[import]

            voice = "en-US-GuyNeural"
            mp3_path = output_path.replace(".wav", ".mp3")

            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(mp3_path)

            wav_path = await self._convert_to_wav(mp3_path, output_path)

            file_size = os.path.getsize(mp3_path)
            duration = file_size / (128 * 1024 / 8)

            return VoiceoverResult(
                audio_path=wav_path,
                duration_seconds=round(duration, 2),
                provider="edge_tts",
                sample_rate=24000,
                sections_timestamps=self._estimate_timestamps(script, duration),
            )

        except Exception as exc:
            logger.warning("edge_tts_failed", error=str(exc))
            return await self._generate_placeholder(text, output_path, script)

    async def _generate_placeholder(
        self,
        text: str,
        output_path: str,
        script: VideoScript,
    ) -> VoiceoverResult:
        """Generate a silent placeholder WAV file with correct duration estimate.

        Used when no TTS provider is available. The file is a valid WAV
        that can be used in the video pipeline.
        """
        # Estimate duration: ~150 words per minute
        word_count = len(text.split())
        duration = max(30.0, (word_count / 150) * 60)

        sample_rate = 24000
        num_samples = int(sample_rate * duration)

        with wave.open(output_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Write silence (zeros)
            silent_chunk = b"\x00\x00" * min(sample_rate, num_samples)
            written = 0
            while written < num_samples:
                chunk_size = min(sample_rate, num_samples - written)
                wf.writeframes(b"\x00\x00" * chunk_size)
                written += chunk_size

        return VoiceoverResult(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            provider="placeholder",
            sample_rate=sample_rate,
            sections_timestamps=self._estimate_timestamps(script, duration),
        )

    @staticmethod
    async def _convert_to_wav(mp3_path: str, wav_path: str) -> str:
        """Convert MP3 to WAV using ffmpeg."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode == 0:
                return wav_path
        except Exception:
            pass
        # If ffmpeg not available, return the mp3 path
        return mp3_path

    @staticmethod
    def _estimate_timestamps(script: VideoScript, total_duration: float) -> list[dict[str, Any]]:
        """Estimate timestamps for each script section based on word count ratios."""
        total_words = sum(len(s.content.split()) for s in script.sections)
        if total_words == 0:
            return []

        timestamps = []
        current_time = 0.0

        for i, section in enumerate(script.sections):
            section_words = len(section.content.split())
            section_duration = (section_words / total_words) * total_duration
            timestamps.append({
                "section_index": i,
                "section_type": section.section_type,
                "section_title": section.section_title,
                "start_time": round(current_time, 2),
                "end_time": round(current_time + section_duration, 2),
                "duration": round(section_duration, 2),
            })
            current_time += section_duration

        return timestamps
