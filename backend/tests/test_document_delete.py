
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_delete_document():
    upload = client.post(
        "/documents/upload",
        files={
            "file": (
                "delete_test.txt",
                b"This document will be deleted.",
                "text/plain",
            )
        },
    )

    assert upload.status_code == 200
    document_id = upload.json()["document_id"]

    response = client.delete(f"/documents/{document_id}")

    assert response.status_code == 200
    assert response.json()["document_id"] == document_id

    listing = client.get("/documents")
    assert listing.status_code == 200

    remaining_ids = [
        document["document_id"]
        for document in listing.json()["documents"]
    ]
    assert document_id not in remaining_ids


def test_delete_unknown_document():
    response = client.delete("/documents/unknown-document-id")

    assert response.status_code == 404
