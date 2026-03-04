"""Monetization Strategy Engine."""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.core.models import MonetizationStrategy, NicheScore

logger = get_logger(__name__)


# ── Niche-to-Affiliate Mapping ─────────────────────────────────────────────────

AFFILIATE_PRODUCTS: dict[str, list[str]] = {
    "technology": ["VPN services", "Cloud hosting", "Software tools", "Tech gadgets"],
    "ai": ["AI tools (ChatGPT Plus, Midjourney)", "Online courses", "Cloud computing"],
    "finance": ["Trading platforms", "Investment apps", "Financial courses", "Credit cards"],
    "investing": ["Brokerage accounts", "Stock analysis tools", "Investment newsletters"],
    "crypto": ["Crypto exchanges", "Hardware wallets", "Trading bots"],
    "health": ["Supplements", "Fitness equipment", "Health apps", "Online coaching"],
    "fitness": ["Workout equipment", "Supplements", "Fitness apps", "Meal delivery"],
    "education": ["Online course platforms", "Books", "Study tools", "Tutoring services"],
    "productivity": ["Productivity apps", "Note-taking tools", "Project management software"],
    "cooking": ["Kitchen gadgets", "Meal kits", "Cookbooks", "Specialty ingredients"],
    "travel": ["Travel insurance", "Booking platforms", "Luggage", "Travel gear"],
    "gaming": ["Gaming peripherals", "PC components", "Gaming chairs", "Subscriptions"],
    "business": ["SaaS tools", "Web hosting", "Email marketing", "CRM platforms"],
    "marketing": ["Marketing tools", "Email platforms", "Analytics software", "Course creation"],
    "science": ["Science kits", "Books", "Online courses", "Lab equipment"],
    "psychology": ["Books", "Therapy apps", "Online courses", "Journaling tools"],
    "real estate": ["Real estate courses", "Property tools", "Investment platforms"],
}

SPONSORSHIP_CATEGORIES: dict[str, list[str]] = {
    "technology": ["SaaS companies", "Tech brands", "VPN providers", "Cloud services"],
    "finance": ["Fintech companies", "Banks", "Investment platforms", "Tax software"],
    "health": ["Health brands", "Supplement companies", "Fitness apps", "Wellness brands"],
    "education": ["EdTech platforms", "Online universities", "Book publishers"],
    "business": ["B2B SaaS", "Business tools", "Professional services"],
    "default": ["General advertisers", "App companies", "D2C brands", "Subscription services"],
}


class MonetizationEngine:
    """Generate monetization strategies for YouTube niches."""

    def generate_strategy(self, niche: NicheScore) -> MonetizationStrategy:
        """Generate a comprehensive monetization strategy."""
        niche_text = niche.niche.lower()

        affiliates = self._find_affiliate_products(niche_text)
        sponsorships = self._find_sponsorship_categories(niche_text)
        digital_products = self._suggest_digital_products(niche_text)
        lead_magnets = self._suggest_lead_magnets(niche_text)
        expansion = self._suggest_expansion(niche)

        strategy = MonetizationStrategy(
            affiliate_products=affiliates,
            sponsorship_categories=sponsorships,
            digital_products=digital_products,
            lead_magnets=lead_magnets,
            expansion_strategy=expansion,
        )

        logger.info("monetization_strategy_generated", niche=niche.niche)
        return strategy

    def _find_affiliate_products(self, niche_text: str) -> list[str]:
        """Find relevant affiliate products for the niche."""
        products: list[str] = []
        for category, items in AFFILIATE_PRODUCTS.items():
            if category in niche_text:
                products.extend(items)

        if not products:
            products = [
                "Relevant online courses",
                "Recommended books",
                "Useful tools and software",
                "Related equipment/gear",
            ]

        return list(dict.fromkeys(products))[:8]

    def _find_sponsorship_categories(self, niche_text: str) -> list[str]:
        """Find relevant sponsorship categories."""
        sponsors: list[str] = []
        for category, items in SPONSORSHIP_CATEGORIES.items():
            if category in niche_text:
                sponsors.extend(items)

        if not sponsors:
            sponsors = SPONSORSHIP_CATEGORIES["default"]

        return list(dict.fromkeys(sponsors))[:6]

    def _suggest_digital_products(self, niche_text: str) -> list[str]:
        """Suggest digital products to create."""
        return [
            f"Comprehensive {niche_text.title()} eBook/Guide",
            f"{niche_text.title()} Online Course",
            f"Premium {niche_text.title()} Template Pack",
            f"{niche_text.title()} Cheat Sheet / Quick Reference",
            f"Exclusive {niche_text.title()} Community Membership",
        ]

    def _suggest_lead_magnets(self, niche_text: str) -> list[str]:
        """Suggest lead magnets for email list building."""
        return [
            f"Free {niche_text.title()} Starter Guide (PDF)",
            f"{niche_text.title()} Checklist",
            f"Top 10 {niche_text.title()} Resources List",
            f"{niche_text.title()} Mini-Course (Email Series)",
        ]

    def _suggest_expansion(self, niche: NicheScore) -> str:
        """Suggest channel expansion strategy."""
        return (
            f"Phase 1 (Months 1-3): Build authority in {niche.niche} with consistent uploads. "
            f"Focus on SEO-optimized content to capture search traffic.\n"
            f"Phase 2 (Months 3-6): Launch digital products (guide/course). "
            f"Start affiliate marketing. Apply for YouTube Partner Program.\n"
            f"Phase 3 (Months 6-12): Pursue sponsorships. "
            f"Build email list with lead magnets. Consider a premium community.\n"
            f"Phase 4 (Year 2+): Diversify to adjacent niches. "
            f"Launch second channel. Build a personal brand."
        )

    def generate_batch(
        self, niches: list[NicheScore]
    ) -> dict[str, MonetizationStrategy]:
        """Generate monetization strategies for multiple niches."""
        results: dict[str, MonetizationStrategy] = {}
        for niche in niches:
            results[niche.niche] = self.generate_strategy(niche)
        return results
