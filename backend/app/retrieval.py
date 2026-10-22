
from dataclasses import dataclass

import numpy as np

from app.chunking import DocumentChunk
from app.embeddings import EmbeddingService


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class Retriever:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

    def retrieve(
        self,
        query: str,
        chunks: list[DocumentChunk],
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            raise ValueError("Query cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be positive")

        if not chunks:
            return []

        query_embedding = self.embedding_service.embed_texts([query])[0]
        chunk_texts = [chunk.text for chunk in chunks]
        chunk_embeddings = self.embedding_service.embed_texts(chunk_texts)

        scores = self.embedding_service.similarity(
            query_embedding, chunk_embeddings
        )

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        return [
            RetrievedChunk(
                chunk=chunks[int(index)],
                score=float(scores[index]),
            )
            for index in ranked_indices
        ]
