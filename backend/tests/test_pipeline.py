
from pathlib import Path

import pytest

from app.embeddings import EmbeddingService
from app.pipeline import DocumentPipeline


def test_pipeline_processes_document_and_retrieves_text(
    tmp_path: Path,
):
    file_path = tmp_path / "guide.txt"
    file_path.write_text(
        "To reset your password, select forgot password "
        "on the login page and follow the instructions.",
        encoding="utf-8",
    )

    pipeline = DocumentPipeline(EmbeddingService())

    index = pipeline.process_document(file_path)

    assert len(index.chunks) >= 1
    assert index.embeddings.shape == (len(index.chunks), 384)

    results = pipeline.ask("How do I reset my password?", index)

    assert len(results) >= 1
    assert "password" in results[0].chunk.text.lower()
    assert results[0].chunk.filename == "guide.txt"


def test_pipeline_rejects_empty_question(tmp_path: Path):
    file_path = tmp_path / "guide.txt"
    file_path.write_text("This is a sample document.", encoding="utf-8")

    pipeline = DocumentPipeline(EmbeddingService())
    index = pipeline.process_document(file_path)

    with pytest.raises(ValueError):
        pipeline.ask("   ", index)
