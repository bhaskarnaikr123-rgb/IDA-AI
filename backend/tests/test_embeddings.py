
import numpy as np
from app.embeddings import EmbeddingService


def test_embedding_shape_and_normalization():
    service = EmbeddingService()
    embeddings = service.embed_texts([
        "Python is a programming language.",
        "The weather is sunny today.",
    ])

    assert embeddings.shape == (2, 384)
    assert np.allclose(np.linalg.norm(embeddings, axis=1), 1.0, atol=1e-5)


def test_empty_input():
    service = EmbeddingService()
    embeddings = service.embed_texts([])

    assert embeddings.shape == (0, 384)


def test_relevant_text_has_higher_similarity():
    service = EmbeddingService()
    texts = [
        "You can reset your password using the forgot-password option.",
        "Plants need sunlight and water to grow.",
    ]

    document_embeddings = service.embed_texts(texts)
    query_embedding = service.embed_texts(
        ["How do I regain access to my account?"]
    )[0]

    scores = service.similarity(query_embedding, document_embeddings)

    assert scores[0] > scores[1]
