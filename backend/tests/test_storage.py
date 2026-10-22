
import numpy as np

from app.chunking import DocumentChunk
from app.pipeline import DocumentIndex
from app.storage import DocumentStorage


def test_storage_saves_and_reloads_index(tmp_path):
    storage = DocumentStorage(tmp_path / "test.db")

    chunks = [
        DocumentChunk(
            chunk_id=0,
            filename="guide.txt",
            page_number=None,
            text="Reset your password from the login page.",
        ),
        DocumentChunk(
            chunk_id=1,
            filename="guide.txt",
            page_number=None,
            text="Contact support if you cannot sign in.",
        ),
    ]

    embeddings = np.array(
        [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        dtype=np.float32,
    )

    original = DocumentIndex(chunks=chunks, embeddings=embeddings)
    storage.save_index("doc-123", original)

    # Create a new storage instance to simulate reopening the database.
    reopened_storage = DocumentStorage(tmp_path / "test.db")
    loaded = reopened_storage.load_index("doc-123")

    assert loaded is not None
    assert len(loaded.chunks) == 2
    assert loaded.chunks[0].text == chunks[0].text
    assert loaded.chunks[0].filename == "guide.txt"
    assert np.array_equal(loaded.embeddings, embeddings)


def test_storage_returns_none_for_unknown_document(tmp_path):
    storage = DocumentStorage(tmp_path / "test.db")

    assert storage.load_index("unknown-id") is None
