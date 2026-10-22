
from app.ingestion import DocumentSection, IngestedDocument
from app.chunking import chunk_document


def test_chunking_creates_overlapping_chunks():
    text = "A" * 1200
    document = IngestedDocument(
        filename="sample.txt",
        file_type="txt",
        sections=[DocumentSection(page_number=None, text=text)],
    )

    chunks = chunk_document(document, chunk_size=500, overlap=100)

    assert len(chunks) == 3
    assert len(chunks[0].text) == 500
    assert chunks[0].text[-100:] == chunks[1].text[:100]


def test_chunking_preserves_metadata():
    document = IngestedDocument(
        filename="report.pdf",
        file_type="pdf",
        sections=[
            DocumentSection(
                page_number=3,
                text="This is sample PDF content.",
            )
        ],
    )

    chunks = chunk_document(document)

    assert chunks[0].filename == "report.pdf"
    assert chunks[0].page_number == 3


def test_invalid_chunk_size_and_overlap():
    document = IngestedDocument(
        filename="sample.txt",
        file_type="txt",
        sections=[DocumentSection(page_number=None, text="Sample text")],
    )

    import pytest

    with pytest.raises(ValueError):
        chunk_document(document, chunk_size=0)

    with pytest.raises(ValueError):
        chunk_document(document, chunk_size=100, overlap=100)
