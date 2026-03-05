"""Video Factory — fully automated YouTube video production pipeline.

Transforms a selected niche into a complete ready-to-upload YouTube video
with voiceover narration, subtitles, thumbnail, and publishing metadata.
"""
from __future__ import annotations

from app.video_factory.concept_engine import ConceptEngine
from app.video_factory.script_generator import ScriptGenerator
from app.video_factory.voice_generator import VoiceGenerator
from app.video_factory.clip_selector import ClipSelector
from app.video_factory.video_assembler import VideoAssembler
from app.video_factory.subtitle_generator import SubtitleGenerator
from app.video_factory.thumbnail_generator import ThumbnailGenerator
from app.video_factory.metadata_generator import MetadataGenerator
from app.video_factory.factory_orchestrator import FactoryOrchestrator
from app.video_factory.job_manager import FactoryJobManager

__all__ = [
    "ConceptEngine",
    "ScriptGenerator",
    "VoiceGenerator",
    "ClipSelector",
    "VideoAssembler",
    "SubtitleGenerator",
    "ThumbnailGenerator",
    "MetadataGenerator",
    "FactoryOrchestrator",
    "FactoryJobManager",
]
