
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_documents():
    content = b"This document explains password recovery."

    upload = client.post(
        "/documents/upload",
        files={"file": ("list_test.txt", content, "text/plain")},
    )

    assert upload.status_code == 200

    response = client.get("/documents")

    assert response.status_code == 200

    data = response.json()
    assert data["count"] >= 1

    matching = [
        document
        for document in data["documents"]
        if document["document_id"] == upload.json()["document_id"]
    ]

    assert len(matching) == 1
    assert matching[0]["filename"] == "list_test.txt"
