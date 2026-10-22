
from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}



def test_upload_and_ask_document(monkeypatch):
    content = (
        b"To reset your password, select forgot password "
        b"on the login page and follow the instructions."
    )

    upload_response = client.post(
        "/documents/upload",
        files={"file": ("guide.txt", content, "text/plain")},
    )

    assert upload_response.status_code == 200

    upload_data = upload_response.json()
    assert upload_data["filename"] == "guide.txt"
    assert upload_data["chunks_created"] >= 1

    monkeypatch.setattr(
    main_module.answer_generator,
    "generate_answer",
    lambda question, retrieved_chunks: (
        "To reset your password, select forgot password "
        "on the login page and follow the instructions. [Source 1]."
    ),
)
    # Ask a question using the uploaded document
    ask_response = client.post(
        "/ask",
        json={
            "document_id": upload_data["document_id"],
            "question": "How can I reset my password?",
            "top_k": 3,
        },
    )

    assert ask_response.status_code == 200

    ask_data = ask_response.json()

    assert ask_data["document_id"] == upload_data["document_id"]
    assert ask_data["question"] == "How can I reset my password?"
    assert isinstance(ask_data["answer"], str)
    assert len(ask_data["answer"]) > 0

    assert isinstance(ask_data["sources"], list)
    assert len(ask_data["sources"]) >= 1
    assert "reset your password" in ask_data["sources"][0]["text"].lower()



def test_upload_rejects_unsupported_file():
    response = client.post(
        "/documents/upload",
        files={"file": ("data.csv", b"name,value\nA,10", "text/csv")},
    )

    assert response.status_code == 400


def test_ask_rejects_empty_question():
    response = client.post(
        "/ask",
        json={
            "document_id": "some-document-id",
            "question": "   ",
            "top_k": 3,
        },
    )

    assert response.status_code == 400


def test_ask_rejects_unknown_document():
    response = client.post(
        "/ask",
        json={
            "document_id": "unknown-document-id",
            "question": "What does the document say?",
            "top_k": 3,
        },
    )

    assert response.status_code == 404
