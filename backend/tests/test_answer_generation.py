
import pytest

from app.answer_generation import AnswerGenerator


def test_missing_question_is_rejected():
    generator = AnswerGenerator.__new__(AnswerGenerator)

    with pytest.raises(ValueError):
        generator.generate_answer("   ", [])


def test_no_retrieved_chunks_returns_fallback():
    generator = AnswerGenerator.__new__(AnswerGenerator)

    answer = generator.generate_answer(
        "How do I reset my password?",
        [],
    )

    assert "couldn't find relevant information" in answer
