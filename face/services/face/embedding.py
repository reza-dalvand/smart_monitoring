"""مدیریت امبدینگ چهره"""
import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingSerializer:
    @staticmethod
    def serialize(embedding):
        if embedding is None:
            return b''
        embedding = embedding.astype(np.float32)
        return embedding.tobytes()

    @staticmethod
    def deserialize(data, dimension=512):
        if not data:
            return None
        try:
            embedding = np.frombuffer(data, dtype=np.float32)
            if len(embedding) != dimension:
                logger.warning(f'Embedding dimension mismatch: expected {dimension}, got {len(embedding)}')
                return None
            return embedding
        except Exception as e:
            logger.error(f'Error deserializing embedding: {e}')
            return None


class EmbeddingStorage:
    def __init__(self):
        self.serializer = EmbeddingSerializer()

    def save_embedding(self, student_id, embedding, model_name, model_version,
                       embedding_dimension, source_image_path=None, is_active=True):
        from face.models import FaceEmbedding
        embedding_data = self.serializer.serialize(embedding)
        face_embedding = FaceEmbedding.objects.create(
            student_id=student_id,
            embedding=embedding_data,
            model_name=model_name,
            model_version=model_version,
            embedding_dimension=embedding_dimension,
            source_image=source_image_path or '',
            is_active=is_active
        )
        logger.info(f'Embedding saved for student {student_id}.')
        return face_embedding

    def get_embeddings_for_student(self, student_id, active_only=True):
        from face.models import FaceEmbedding
        queryset = FaceEmbedding.objects.filter(student_id=student_id)
        if active_only:
            queryset = queryset.filter(is_active=True)
        results = []
        for face_embedding in queryset:
            embedding = self.serializer.deserialize(
                face_embedding.embedding,
                face_embedding.embedding_dimension
            )
            if embedding is not None:
                results.append((embedding, face_embedding))
        return results

    def deactivate_all_for_student(self, student_id):
        from face.models import FaceEmbedding
        count = FaceEmbedding.objects.filter(
            student_id=student_id, is_active=True
        ).update(is_active=False)
        logger.info(f'Deactivated {count} embeddings for student {student_id}')
        return count