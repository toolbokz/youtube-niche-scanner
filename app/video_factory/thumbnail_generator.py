"""Video Factory — Thumbnail Generation.

Generates a YouTube thumbnail concept via AI and optionally creates
an actual thumbnail image using Pillow.
"""
from __future__ import annotations

import os
from typing import Any

from app.core.logging import get_logger
from app.video_factory.models import (
    ThumbnailConcept,
    ThumbnailResult,
)

logger = get_logger(__name__)

# Default thumbnail dimensions (YouTube recommended)
_THUMB_WIDTH = 1280
_THUMB_HEIGHT = 720


class ThumbnailGenerator:
    """Generate YouTube thumbnail concepts and images."""

    async def generate(
        self,
        niche: str,
        concept: Any,
        output_dir: str,
    ) -> ThumbnailResult:
        """Generate a thumbnail concept and image.

        Parameters
        ----------
        niche : str
            Target niche.
        concept : VideoConcept
            Video concept for context.
        output_dir : str
            Directory for output files.

        Returns
        -------
        ThumbnailResult
            The thumbnail concept and image path.
        """
        logger.info("thumbnail_generation_start", niche=niche)

        os.makedirs(output_dir, exist_ok=True)
        thumb_path = os.path.join(output_dir, "thumbnail.png")

        # Generate concept via AI
        thumb_concept = await self._generate_concept(niche, concept)

        # Generate actual image
        created = await self._create_image(thumb_concept, concept.title, thumb_path)

        result = ThumbnailResult(
            thumbnail_path=thumb_path if created else "",
            concept=thumb_concept,
            width=_THUMB_WIDTH,
            height=_THUMB_HEIGHT,
        )

        logger.info(
            "thumbnail_generation_done",
            niche=niche,
            has_image=created,
        )
        return result

    async def _generate_concept(
        self, niche: str, concept: Any
    ) -> ThumbnailConcept:
        """Generate a thumbnail concept using AI."""
        title = getattr(concept, "title", str(concept))
        description = getattr(concept, "concept", niche)
        try:
            from app.ai.client import get_ai_client

            client = get_ai_client()
            prompt = (
                f"Create a YouTube thumbnail concept for a video about "
                f"'{niche}'. Title: '{title}'. Concept: '{description}'. "
                f"Return JSON with: visual_concept, text_overlay, "
                f"color_scheme (list of hex), layout_structure, "
                f"emotion_trigger, contrast_strategy."
            )
            result = client.generate_json(prompt, temperature=0.7)

            if result and isinstance(result, dict):
                return ThumbnailConcept(
                    visual_concept=result.get("visual_concept", ""),
                    text_overlay=result.get("text_overlay", ""),
                    color_scheme=result.get("color_scheme", []),
                    layout_structure=result.get("layout_structure", ""),
                    emotion_trigger=result.get("emotion_trigger", ""),
                    contrast_strategy=result.get("contrast_strategy", ""),
                )

        except Exception as exc:
            logger.warning("thumbnail_concept_ai_failed", error=str(exc))

        # Fallback
        return ThumbnailConcept(
            visual_concept=f"Bold visual related to {niche}",
            text_overlay=title[:30] if title else niche.upper(),
            color_scheme=["#FF0000", "#FFFFFF", "#000000"],
            layout_structure="Large text left, visual right, gradient background",
            emotion_trigger="curiosity",
            contrast_strategy="High contrast red and white on dark background",
        )

    async def _create_image(
        self,
        thumb_concept: ThumbnailConcept,
        title: str,
        output_path: str,
    ) -> bool:
        """Create an actual thumbnail image using Pillow.

        Generates a visually appealing thumbnail with text overlay,
        gradient background, and accent graphics.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

            img = Image.new("RGB", (_THUMB_WIDTH, _THUMB_HEIGHT))
            draw = ImageDraw.Draw(img)

            # Parse colors from concept
            colors = thumb_concept.color_scheme or ["#FF0000", "#FFFFFF", "#000000"]
            bg_color = self._hex_to_rgb(colors[-1]) if len(colors) > 2 else (26, 26, 46)
            accent_color = self._hex_to_rgb(colors[0]) if colors else (255, 0, 0)
            text_color = self._hex_to_rgb(colors[1]) if len(colors) > 1 else (255, 255, 255)

            # Draw gradient background
            for y in range(_THUMB_HEIGHT):
                ratio = y / _THUMB_HEIGHT
                r = int(bg_color[0] * (1 - ratio * 0.5))
                g = int(bg_color[1] * (1 - ratio * 0.5))
                b = int(bg_color[2] * (1 - ratio * 0.5))
                draw.line([(0, y), (_THUMB_WIDTH, y)], fill=(r, g, b))

            # Draw accent stripe
            stripe_y = _THUMB_HEIGHT - 120
            draw.rectangle(
                [(0, stripe_y), (_THUMB_WIDTH, stripe_y + 80)],
                fill=(*accent_color, 200),
            )

            # Determine text to display
            display_text = thumb_concept.text_overlay or title[:30]
            display_text = display_text.upper()

            # Try to load a font, fallback to default
            font_large = self._get_font(72)
            font_small = self._get_font(36)

            # Draw main text (centered, with shadow)
            self._draw_text_with_shadow(
                draw, display_text, font_large, text_color,
                y_position=_THUMB_HEIGHT // 2 - 60,
            )

            # Draw subtitle text on accent stripe
            subtitle = thumb_concept.emotion_trigger.upper() if thumb_concept.emotion_trigger else ""
            if subtitle:
                self._draw_text_with_shadow(
                    draw, subtitle, font_small, (255, 255, 255),
                    y_position=stripe_y + 15,
                )

            img.save(output_path, "PNG", quality=95)
            return True

        except ImportError:
            logger.info("pillow_not_installed_creating_placeholder_thumbnail")
            return self._create_placeholder_thumbnail(output_path)
        except Exception as exc:
            logger.warning("thumbnail_image_creation_failed", error=str(exc))
            return self._create_placeholder_thumbnail(output_path)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return (128, 128, 128)
        try:
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            return (128, 128, 128)

    @staticmethod
    def _get_font(size: int) -> Any:
        """Load a font, falling back to default."""
        try:
            from PIL import ImageFont  # type: ignore[import]

            # Try common system fonts
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
            for path in font_paths:
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
            return ImageFont.load_default()
        except Exception:
            from PIL import ImageFont  # type: ignore[import]
            return ImageFont.load_default()

    @staticmethod
    def _draw_text_with_shadow(
        draw: Any,
        text: str,
        font: Any,
        color: tuple[int, int, int],
        y_position: int,
    ) -> None:
        """Draw text centered horizontally with a shadow."""
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
        except Exception:
            text_width = len(text) * 20

        x = (_THUMB_WIDTH - text_width) // 2

        # Shadow
        draw.text((x + 3, y_position + 3), text, fill=(0, 0, 0), font=font)
        # Main text
        draw.text((x, y_position), text, fill=color, font=font)

    @staticmethod
    def _create_placeholder_thumbnail(output_path: str) -> bool:
        """Create a minimal placeholder PNG file."""
        try:
            # Minimal valid 1x1 PNG
            import struct
            import zlib

            def _create_minimal_png(width: int, height: int) -> bytes:
                """Create a minimal PNG with a solid color."""

                def _chunk(chunk_type: bytes, data: bytes) -> bytes:
                    c = chunk_type + data
                    crc = zlib.crc32(c) & 0xFFFFFFFF
                    return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

                # Dark blue background
                raw_data = b""
                for _ in range(height):
                    raw_data += b"\x00"  # filter byte
                    raw_data += b"\x1a\x1a\x2e" * width  # RGB

                header = b"\x89PNG\r\n\x1a\n"
                ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
                return (
                    header
                    + _chunk(b"IHDR", ihdr)
                    + _chunk(b"IDAT", zlib.compress(raw_data))
                    + _chunk(b"IEND", b"")
                )

            png_data = _create_minimal_png(320, 180)
            with open(output_path, "wb") as f:
                f.write(png_data)
            return True

        except Exception:
            from pathlib import Path
            Path(output_path).touch()
            return False
