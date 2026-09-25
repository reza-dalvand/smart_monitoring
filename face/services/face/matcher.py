"""تطبیق چهره با استفاده از شباهت کسینوسی"""
import logging
from typing import List

import numpy as np

from .interfaces import BaseFaceMatcher, MatchResult
from face.constants import MatchDecision

logger = logging.getLogger(__name__)


class CosineFaceMatcher(BaseFaceMatcher):
    """
    روش تجمیع:
    - MAX: بیشترین شباهت بین امبدینگ‌های مرجع
    - TOP_K_MEAN: میانگین بیشترین شباهت‌ها
    - CENTROID: مقایسه با میانگین امبدینگ‌های مرجع

    برای نسخه توسعه، روش MAX ساده و قابل اتکا انتخاب شده است.
    """

    def __init__(self, aggregation_method='MAX', top_k=2):
        self.aggregation_method = (aggregation_method or 'MAX').strip()
        self.top_k = int(top_k or 2)

    def match(self, query_embedding, reference_embeddings, threshold):
        if not reference_embeddings:
            return MatchResult(
                decision=MatchDecision.PROCESSING_ERROR,
                similarity_score=0.0,
                details={'error': 'هیچ امبدینگ مرجعی وجود ندارد.'}
            )

        method = self._normalized_method()

        if method == 'CENTROID':
            centroid = np.mean(reference_embeddings, axis=0).astype(np.float32)
            score = self.calculate_similarity(query_embedding, centroid)
            best_index = -1
        else:
            similarities = []
            for ref_embedding in reference_embeddings:
                try:
                    sim = self.calculate_similarity(query_embedding, ref_embedding)
                    similarities.append(sim)
                except Exception as e:
                    logger.warning(f'Error calculating similarity: {e}')
                    similarities.append(0.0)

            if not similarities:
                return MatchResult(
                    decision=MatchDecision.PROCESSING_ERROR,
                    similarity_score=0.0,
                )

            score, best_index = self._aggregate(similarities, method)

        decision = MatchDecision.MATCH if score >= threshold else MatchDecision.SUSPICIOUS

        logger.info(
            'Face matching completed. Score=%.4f, Decision=%s, Method=%s',
            score,
            decision,
            method
        )

        return MatchResult(
            decision=decision,
            similarity_score=float(score),
            best_match_index=best_index,
            all_similarities=[] if method == 'CENTROID' else similarities,
            details={
                'aggregation_method': method,
                'threshold': threshold,
                'reference_count': len(reference_embeddings),
            }
        )

    def calculate_similarity(self, embedding_a, embedding_b):
        norm_a = np.linalg.norm(embedding_a)
        norm_b = np.linalg.norm(embedding_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        normalized_a = embedding_a / norm_a
        normalized_b = embedding_b / norm_b

        similarity = float(np.dot(normalized_a, normalized_b))
        return max(-1.0, min(1.0, similarity))

    def _normalized_method(self):
        method = (self.aggregation_method or 'MAX').upper()

        if method in ('حداکثر', 'MAX', 'MAXIMUM'):
            return 'MAX'

        if method in ('میانگین', 'TOP_K_MEAN', 'MEAN_TOP_K'):
            return 'TOP_K_MEAN'

        if method in ('مرکز', 'CENTROID'):
            return 'CENTROID'

        return 'MAX'

    def _aggregate(self, similarities: List[float], method: str):
        if not similarities:
            return 0.0, -1

        if method == 'TOP_K_MEAN':
            sorted_sims = sorted(similarities, reverse=True)
            top_k = max(1, min(self.top_k, len(sorted_sims)))
            top_sims = sorted_sims[:top_k]
            avg_sim = sum(top_sims) / len(top_sims)
            best_index = int(np.argmax(similarities))
            return float(avg_sim), best_index

        best_index = int(np.argmax(similarities))
        return float(similarities[best_index]), best_index