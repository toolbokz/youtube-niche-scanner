"""SEO Description Generator."""
from __future__ import annotations

from app.core.logging import get_logger
from app.core.models import SEODescription, VideoIdea

logger = get_logger(__name__)


class DescriptionGenerationEngine:
    """Generate SEO-optimized YouTube video descriptions."""

    def generate(self, video: VideoIdea, niche: str) -> SEODescription:
        """Generate a complete SEO description for a video."""
        keywords = video.target_keywords

        # SEO intro paragraph
        intro = self._generate_intro(video.title, video.topic, niche)

        # Keyword cluster block
        keyword_block = self._build_keyword_block(keywords, niche)

        # Chapters suggestion
        chapters = self._suggest_chapters(video.topic, video.angle)

        # CTA structure
        cta = self._build_cta(niche)

        # Affiliate positioning
        affiliate = self._build_affiliate_section(niche)

        desc = SEODescription(
            intro_paragraph=intro,
            keyword_block=keyword_block,
            chapters=chapters,
            cta_structure=cta,
            affiliate_positioning=affiliate,
        )

        return desc

    def _generate_intro(self, title: str, topic: str, niche: str) -> str:
        """Generate SEO-optimized intro paragraph (first 150 chars visible)."""
        return (
            f"In this video, we dive deep into {topic.lower()} and uncover "
            f"everything you need to know about {niche.lower()}. "
            f"Whether you're a complete beginner or looking to level up your "
            f"knowledge, this comprehensive guide covers the latest insights, "
            f"strategies, and expert tips that will help you succeed. "
            f"Watch until the end for exclusive tips you won't find anywhere else."
        )

    def _build_keyword_block(self, keywords: list[str], niche: str) -> list[str]:
        """Build a keyword-rich tag block for the description."""
        block = [niche.lower()]
        block.extend(kw.lower() for kw in keywords[:10])
        # Add common modifiers
        modifiers = ["guide", "tutorial", "tips", "explained", "2026", "best"]
        for mod in modifiers:
            block.append(f"{niche.lower()} {mod}")
        return list(dict.fromkeys(block))  # Deduplicate

    def _suggest_chapters(self, topic: str, angle: str) -> list[str]:
        """Suggest video chapters/timestamps."""
        return [
            f"0:00 Introduction to {topic.title()}",
            f"0:30 Why {topic.title()} Matters",
            f"2:00 Key Concepts Explained",
            f"4:30 Deep Dive Analysis",
            f"7:00 Practical Examples",
            f"9:30 Common Mistakes to Avoid",
            f"11:00 Expert Tips & Strategies",
            f"13:00 Future Outlook",
            f"14:30 Summary & Key Takeaways",
        ]

    def _build_cta(self, niche: str) -> str:
        """Generate call-to-action structure."""
        return (
            f"🔔 Subscribe for more {niche} content and hit the notification bell!\n"
            f"👍 Like this video if you found it helpful\n"
            f"💬 Comment below with your thoughts or questions\n"
            f"📤 Share with someone who needs to see this\n\n"
            f"Follow us for more:\n"
            f"📧 Newsletter: [Link]\n"
            f"🐦 Twitter: [Link]\n"
            f"📸 Instagram: [Link]"
        )

    def _build_affiliate_section(self, niche: str) -> str:
        """Generate affiliate/resource positioning."""
        return (
            f"📚 Resources & Tools Mentioned:\n"
            f"• [Tool/Product 1] — [Affiliate Link]\n"
            f"• [Tool/Product 2] — [Affiliate Link]\n"
            f"• [Recommended Book] — [Affiliate Link]\n\n"
            f"(Some links above are affiliate links. Using them supports "
            f"this channel at no extra cost to you.)"
        )

    def generate_batch(
        self, videos: list[VideoIdea], niche: str
    ) -> list[SEODescription]:
        """Generate descriptions for multiple videos."""
        return [self.generate(v, niche) for v in videos]
