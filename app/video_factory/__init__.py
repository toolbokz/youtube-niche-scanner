"""Video Factory — compilation video production pipeline.

Downloads real YouTube source videos, extracts segments, validates
clips, and assembles them into a final compilation video ready for
YouTube upload.  No slides or placeholder footage — real clips only.
"""
from __future__ import annotations

from app.video_factory.youtube_downloader import YouTubeDownloader
from app.video_factory.segment_extractor import SegmentExtractor
from app.video_factory.clip_validator import ClipValidator
from app.video_factory.copyright_guard import CopyrightGuard
from app.video_factory.video_assembler import CompilationAssembler
from app.video_factory.thumbnail_generator import ThumbnailGenerator
from app.video_factory.metadata_generator import MetadataGenerator
from app.video_factory.factory_orchestrator import FactoryOrchestrator
from app.video_factory.job_manager import FactoryJobManager

__all__ = [
    "YouTubeDownloader",
    "SegmentExtractor",
    "ClipValidator",
    "CopyrightGuard",
    "CompilationAssembler",
    "ThumbnailGenerator",
    "MetadataGenerator",
    "FactoryOrchestrator",
    "FactoryJobManager",
]
