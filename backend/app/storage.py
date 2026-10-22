
import sqlite3
from pathlib import Path

import numpy as np

from app.chunking import DocumentChunk
from app.pipeline import DocumentIndex


class DocumentStorage:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    document_id TEXT NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    page_number INTEGER,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    PRIMARY KEY (document_id, chunk_id),
                    FOREIGN KEY (document_id)
                        REFERENCES documents(document_id)
                        ON DELETE CASCADE
                )
            """)

            connection.execute("PRAGMA foreign_keys = ON")

    def save_index(self, document_id: str, index: DocumentIndex):
        if len(index.chunks) != len(index.embeddings):
            raise ValueError("Each chunk must have one embedding")

        with self.connect() as connection:
            connection.execute(
                "DELETE FROM chunks WHERE document_id = ?",
                (document_id,),
            )
            connection.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,),
            )

            connection.execute(
                """
                INSERT INTO documents
                (document_id, filename, chunk_count)
                VALUES (?, ?, ?)
                """,
                (
                    document_id,
                    index.chunks[0].filename if index.chunks else "",
                    len(index.chunks),
                ),
            )

            for chunk, embedding in zip(index.chunks, index.embeddings):
                vector = np.asarray(embedding, dtype=np.float32)

                connection.execute(
                    """
                    INSERT INTO chunks
                    (document_id, chunk_id, filename, page_number, text, embedding)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        chunk.chunk_id,
                        chunk.filename,
                        chunk.page_number,
                        chunk.text,
                        sqlite3.Binary(vector.tobytes()),
                    ),
                )

    def load_index(self, document_id: str) -> DocumentIndex | None:
        with self.connect() as connection:
            document = connection.execute(
                "SELECT document_id FROM documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()

            if document is None:
                return None

            rows = connection.execute(
                """
                SELECT chunk_id, filename, page_number, text, embedding
                FROM chunks
                WHERE document_id = ?
                ORDER BY chunk_id
                """,
                (document_id,),
            ).fetchall()

        chunks = []
        embeddings = []

        for row in rows:
            chunks.append(
                DocumentChunk(
                    chunk_id=row["chunk_id"],
                    filename=row["filename"],
                    page_number=row["page_number"],
                    text=row["text"],
                )
            )

            vector = np.frombuffer(row["embedding"], dtype=np.float32).copy()
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
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, filename, chunk_count
                FROM documents
                ORDER BY filename
                """
            ).fetchall()

        return [dict(row) for row in rows]


    def delete_document(self, document_id: str) -> bool:
        with self.connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")

            cursor = connection.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,),
            )

            return cursor.rowcount > 0
