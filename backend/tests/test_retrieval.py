
import pytest

from app.chunking import DocumentChunk
from app.embeddings import EmbeddingService
from app.retrieval import Retriever


def test_retrieval_ranks_relevant_chunk_first():
    service = EmbeddingService()
    retriever = Retriever(service)

    chunks = [
        DocumentChunk(
            chunk_id=0,
            filename="guide.txt",
            page_number=None,
            text="Plants need sunlight and water to grow.",
        ),
        DocumentChunk(
            chunk_id=1,
            filename="guide.txt",
            page_number=None,
            text="Use the forgot-password option to regain account access.",
        ),
    ]

    results = retriever.retrieve(
        "How do I regain access to my account?",
        chunks,
        top_k=2,
    )

    assert len(results) == 2
    assert results[0].chunk.chunk_id == 1
    assert results[0].score > results[1].score


def test_retrieval_respects_top_k():
    service = EmbeddingService()
    retriever = Retriever(service)

    chunks = [
        DocumentChunk(i, "guide.txt", None, f"Sample document text number {i}.")
        for i in range(5)
    ]

    results = retriever.retrieve("Sample document text", chunks, top_k=2)

    assert len(results) == 2


def test_retrieval_rejects_invalid_inputs():
    retriever = Retriever(EmbeddingService())

    with pytest.raises(ValueError):
        retriever.retrieve("", [], top_k=1)

    with pytest.raises(ValueError):
        retriever.retrieve("A question", [], top_k=0)

    assert retriever.retrieve("A question", [], top_k=3) == []
