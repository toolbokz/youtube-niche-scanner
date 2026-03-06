"""Niche Clustering Engine - groups keywords into meaningful niches."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from app.core.logging import get_logger
from app.core.models import KeywordCluster

logger = get_logger(__name__)


class NicheClusteringEngine:
    """Cluster keywords into semantic niches using TF-IDF and hierarchical clustering."""

    def __init__(
        self,
        min_cluster_size: int = 3,
        max_clusters: int = 50,
        distance_threshold: float = 0.7,
    ) -> None:
        self.min_cluster_size = min_cluster_size
        self.max_clusters = max_clusters
        self.distance_threshold = distance_threshold

    def cluster_keywords(
        self, keywords: list[str], seed_keywords: list[str] | None = None
    ) -> list[KeywordCluster]:
        """Cluster a list of keywords into niches."""
        if len(keywords) < self.min_cluster_size:
            if keywords:
                return [KeywordCluster(
                    cluster_id=0,
                    name=keywords[0],
                    keywords=keywords,
                    seed_keyword=keywords[0],
                    size=len(keywords),
                )]
            return []

        # Preprocess keywords
        cleaned = [self._clean_keyword(kw) for kw in keywords]

        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 3),
            max_features=5000,
            stop_words="english",
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(cleaned)
        except ValueError:
            logger.warning("tfidf_failed", count=len(keywords))
            return [KeywordCluster(
                cluster_id=0,
                name="general",
                keywords=keywords,
                seed_keyword=keywords[0] if keywords else "",
                size=len(keywords),
            )]

        # Determine optimal number of clusters
        n_clusters = min(self.max_clusters, max(2, len(keywords) // 5))

        # Hierarchical clustering
        try:
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters,
                metric="cosine",
                linkage="average",
            )
            labels = clustering.fit_predict(tfidf_matrix.toarray())
        except Exception as e:
            logger.warning("clustering_failed", error=str(e))
            labels = [0] * len(keywords)

        # Group keywords by cluster label
        clusters_map: defaultdict[int, list[str]] = defaultdict(list)
        for kw, label in zip(keywords, labels):
            clusters_map[label].append(kw)

        # Build KeywordCluster objects
        clusters: list[KeywordCluster] = []
        for cluster_id, kw_list in sorted(clusters_map.items()):
            if len(kw_list) < self.min_cluster_size:
                continue

            name = self._generate_cluster_name(kw_list)
            seed = self._find_best_seed(kw_list, seed_keywords)

            clusters.append(KeywordCluster(
                cluster_id=cluster_id,
                name=name,
                keywords=kw_list,
                seed_keyword=seed,
                size=len(kw_list),
            ))

        logger.info(
            "clustering_complete",
            total_keywords=len(keywords),
            clusters=len(clusters),
        )

        return clusters

    def _clean_keyword(self, keyword: str) -> str:
        """Normalize keyword for vectorization."""
        keyword = keyword.lower().strip()
        keyword = re.sub(r"[^\w\s]", " ", keyword)
        keyword = re.sub(r"\s+", " ", keyword)
        return keyword

    def _generate_cluster_name(self, keywords: list[str]) -> str:
        """Generate a descriptive name for a cluster from its keywords."""
        # Extract most common meaningful words
        all_words: list[str] = []
        stop_words = {
            "the", "a", "an", "is", "in", "to", "for", "of", "and", "or",
            "how", "what", "why", "when", "where", "which", "best", "top",
            "with", "from", "that", "this", "your", "you", "can", "will",
        }

        for kw in keywords:
            words = self._clean_keyword(kw).split()
            all_words.extend(w for w in words if w not in stop_words and len(w) > 2)

        if not all_words:
            return keywords[0] if keywords else "unknown"

        counter = Counter(all_words)
        top_words = [word for word, _ in counter.most_common(3)]
        return " ".join(top_words)

    def _find_best_seed(
        self, keywords: list[str], seed_keywords: list[str] | None
    ) -> str:
        """Find the most representative keyword as seed."""
        if seed_keywords:
            for seed in seed_keywords:
                for kw in keywords:
                    if seed.lower() in kw.lower():
                        return kw

        # Use shortest keyword as it's usually the most general
        return min(keywords, key=len)

    def merge_small_clusters(
        self, clusters: list[KeywordCluster], min_size: int = 3
    ) -> list[KeywordCluster]:
        """Merge clusters that are too small into the nearest larger cluster."""
        large = [c for c in clusters if c.size >= min_size]
        small = [c for c in clusters if c.size < min_size]

        if not large:
            # If all clusters are small, combine into one
            all_kws = []
            for c in clusters:
                all_kws.extend(c.keywords)
            if all_kws:
                return [KeywordCluster(
                    cluster_id=0,
                    name=self._generate_cluster_name(all_kws),
                    keywords=all_kws,
                    seed_keyword=all_kws[0],
                    size=len(all_kws),
                )]
            return []

        # Add small cluster keywords to the first large cluster (without mutation)
        if small:
            extra_kws: list[str] = []
            for c in small:
                extra_kws.extend(c.keywords)
            # Create a new cluster with merged keywords instead of mutating in-place
            merged = large[0]
            merged_keywords = list(merged.keywords) + extra_kws
            large[0] = KeywordCluster(
                cluster_id=merged.cluster_id,
                name=merged.name,
                keywords=merged_keywords,
                seed_keyword=merged.seed_keyword,
                size=len(merged_keywords),
            )

        return large
