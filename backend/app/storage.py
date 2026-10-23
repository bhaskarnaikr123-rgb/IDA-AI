
import base64
import os

import numpy as np
from supabase import Client, create_client

from app.chunking import DocumentChunk
from app.pipeline import DocumentIndex


class DocumentStorage:
    def __init__(self, db_path=None):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SECRET_KEY")

        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SECRET_KEY must be configured."
            )

        self.client: Client = create_client(url, key)
        self.initialize()

    
    def initialize(self):
        # Verify that both Supabase tables are accessible.
        self.client.table("documents").select(
            "document_id"
        ).limit(1).execute()

        self.client.table("chunks").select(
            "document_id"
        ).limit(1).execute()


    def save_index(self, document_id: str, index: DocumentIndex):
        if len(index.chunks) != len(index.embeddings):
            raise ValueError("Each chunk must have one embedding")

        filename = index.chunks[0].filename if index.chunks else ""

        self.client.table("documents").upsert({
            "document_id": document_id,
            "filename": filename,
            "chunk_count": len(index.chunks),
        }).execute()

        # Remove old chunks before saving the replacement index.
        self.client.table("chunks").delete().eq(
            "document_id", document_id
        ).execute()

        rows = []
        for chunk, embedding in zip(index.chunks, index.embeddings):
            vector = np.asarray(embedding, dtype=np.float32)
            encoded = base64.b64encode(vector.tobytes()).decode("ascii")

            rows.append({
                "document_id": document_id,
                "chunk_id": chunk.chunk_id,
                "filename": chunk.filename,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "embedding": encoded,
            })

        # Insert in batches to avoid oversized API requests.
        for start in range(0, len(rows), 100):
            self.client.table("chunks").insert(
                rows[start:start + 100]
            ).execute()

    def load_index(self, document_id: str) -> DocumentIndex | None:
        document = (
            self.client.table("documents")
            .select("document_id")
            .eq("document_id", document_id)
            .limit(1)
            .execute()
        )

        if not document.data:
            return None

        result = (
            self.client.table("chunks")
            .select("chunk_id, filename, page_number, text, embedding")
            .eq("document_id", document_id)
            .order("chunk_id")
            .execute()
        )

        chunks = []
        embeddings = []

        for row in result.data:
            chunks.append(DocumentChunk(
                chunk_id=row["chunk_id"],
                filename=row["filename"],
                page_number=row["page_number"],
                text=row["text"],
            ))

            raw = base64.b64decode(row["embedding"])
            vector = np.frombuffer(raw, dtype=np.float32).copy()
            embeddings.append(vector)

        if not embeddings:
            return DocumentIndex(
                chunks=[],
                embeddings=np.empty((0, 384), dtype=np.float32),
            )

        return DocumentIndex(
            chunks=chunks,
            embeddings=np.vstack(embeddings),
        )

    def list_documents(self) -> list[dict]:
        result = (
            self.client.table("documents")
            .select("document_id, filename, chunk_count")
            .order("filename")
            .execute()
        )
        return result.data

    def delete_document(self, document_id: str) -> bool:
        existing = (
            self.client.table("documents")
            .select("document_id")
            .eq("document_id", document_id)
            .limit(1)
            .execute()
        )

        if not existing.data:
            return False

        # Delete chunks explicitly before the parent document.
        self.client.table("chunks").delete().eq(
            "document_id", document_id
        ).execute()

        self.client.table("documents").delete().eq(
            "document_id", document_id
        ).execute()

        return True

    def upload_file(self, object_path: str, content: bytes, content_type: str):
        return self.client.storage.from_("ida-documents").upload(
            path=object_path,
            file=content,
            file_options={
                "content-type": content_type,
                "upsert": "true",
            },
        )

    def delete_file(self, object_path: str):
        return self.client.storage.from_("ida-documents").remove(
            [object_path]
        )
