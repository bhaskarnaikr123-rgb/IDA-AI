
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.ingestion import ingest_document
from app.chunking import DocumentChunk, chunk_document
from app.embeddings import EmbeddingService
from app.retrieval import RetrievedChunk


@dataclass
class DocumentIndex:
    chunks: list[DocumentChunk]
    embeddings: np.ndarray


class DocumentPipeline:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

    def process_document(
        self,
        file_path: str | Path,
        chunk_size: int = 500,
        overlap: int = 100,
    ) -> DocumentIndex:
        document = ingest_document(file_path)
        chunks = chunk_document(document, chunk_size, overlap)

        embeddings = self.embedding_service.embed_texts(
            [chunk.text for chunk in chunks]
        )

        return DocumentIndex(chunks=chunks, embeddings=embeddings)

    def ask(
        self,
        question: str,
        index: DocumentIndex,
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        if not question.strip():
            raise ValueError("Question cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be positive")

        if not index.chunks:
            return []

        query_embedding = self.embedding_service.embed_texts(
            [question]
        )[0]

        scores = self.embedding_service.similarity(
            query_embedding,
            index.embeddings,
        )

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        return [
            RetrievedChunk(
                chunk=index.chunks[int(i)],
                score=float(scores[i]),
            )
            for i in ranked_indices
        ]
