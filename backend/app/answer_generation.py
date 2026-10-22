
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.retrieval import RetrievedChunk


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class AnswerGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Check your root .env file."
            )

        self.model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        print(f"Gemini model configured: {self.model}")
        self.client = genai.Client(api_key=api_key)

    def generate_answer(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> str:
        if not question.strip():
            raise ValueError("Question cannot be empty")

        if not retrieved_chunks:
            return "I couldn't find relevant information in the uploaded document."

        context_parts = []

        for i, result in enumerate(retrieved_chunks, start=1):
            chunk = result.chunk
            source = chunk.filename

            if chunk.page_number is not None:
                source += f", page {chunk.page_number}"

            context_parts.append(
                f"[Source {i}: {source}]\n{chunk.text}"
            )

        context = "\n\n".join(context_parts)

        prompt =  f"""
        You are a helpful document assistant. Answer the user's question
        using only the provided document excerpts.

        Rules:
        - Give a direct, complete answer in simple language.
        - Answer the entire question. Never stop mid-sentence.
        - For lists, include every relevant item found in the excerpts.
        - For comparison questions, explain both sides clearly.
        - Keep the answer concise, usually 1-4 sentences or a short list.
        - Do not include source labels, citations, references, or similarity scores.
        - Do not mention the excerpts or explain your retrieval process.
        - If the document does not contain the answer, say:
        "The document does not provide that information."
        - Never invent facts that are not supported by the excerpts.
        DOCUMENT EXCERPTS:
        {context}

USER QUESTION:
{question}
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=600,
            ),
        )

        answer = response.text

        if not answer or not answer.strip():
            raise RuntimeError("Gemini returned an empty answer.")

        return answer.strip()
