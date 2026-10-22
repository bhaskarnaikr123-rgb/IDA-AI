
from dataclasses import dataclass

from app.ingestion import IngestedDocument


@dataclass
class DocumentChunk:
    chunk_id: int
    filename: str
    page_number: int | None
    text: str


def chunk_document(
    document: IngestedDocument,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[DocumentChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks = []
    chunk_id = 0
    step = chunk_size - overlap

    for section in document.sections:
        text = section.text.strip()

        for start in range(0, len(text), step):
            chunk_text = text[start:start + chunk_size].strip()

            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        filename=document.filename,
                        page_number=section.page_number,
                        text=chunk_text,
                    )
                )
                chunk_id += 1

    return chunks
