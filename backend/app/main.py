import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.embeddings import EmbeddingService
from app.pipeline import DocumentPipeline, DocumentIndex

from app.storage import DocumentStorage
from fastapi import Path as ApiPath

from app.answer_generation import AnswerGenerator
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Intelligent Document Assistant",
    description="Upload documents and retrieve relevant information.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# In-memory storage for this development version.
embedding_service = EmbeddingService()
pipeline = DocumentPipeline(embedding_service)
DB_PATH = PROJECT_ROOT / "data" / "assistant.db"
storage = DocumentStorage(DB_PATH)
answer_generator = AnswerGenerator()


class AskRequest(BaseModel):
    document_id: str
    question: str
    top_k: int = 3



@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    index = storage.load_index(document_id)

    if index is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # Find the saved file using the document ID and supported extension.
    deleted_from_db = storage.delete_document(document_id)

    if not deleted_from_db:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    for extension in SUPPORTED_EXTENSIONS:
        try:
            storage.delete_file(f"{document_id}{extension}")
        except Exception as exc:
            print(f"Could not delete stored file: {exc}")

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id,
    }
    

@app.get("/")
def home():
    return {"message": "Intelligent Document Assistant API is running."}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/documents")
def list_documents():
    documents = storage.list_documents()

    return {
        "count": len(documents),
        "documents": documents,
    }



@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    original_filename = Path(file.filename or "").name
    extension = Path(original_filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, TXT, and DOCX files are supported.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 10 MB.",
        )

    document_id = str(uuid4())
    stored_path = UPLOAD_DIR / f"{document_id}{extension}"

    
    object_path = f"{document_id}{extension}"
    uploaded_to_supabase = False

    try:
        # Temporary local copy, used only for document processing.
        stored_path.write_bytes(content)
        index = pipeline.process_document(stored_path)

        for chunk in index.chunks:
            chunk.filename = original_filename

        content_type = (
            mimetypes.guess_type(original_filename)[0]
            or "application/octet-stream"
        )

        storage.upload_file(object_path, content, content_type)
        uploaded_to_supabase = True

        storage.save_index(document_id, index)

    except Exception as exc:
        print(f"UPLOAD ERROR: {type(exc).__name__}: {exc}", flush=True)
        stored_path.unlink(missing_ok=True)

        if uploaded_to_supabase:
            try:
                storage.delete_file(object_path)
            except Exception as cleanup_error:
                print("Storage cleanup failed:", cleanup_error)

        raise HTTPException(
            status_code=422,
            detail="Could not process or save document. Check backend logs.",
        ) from exc

    finally:
        stored_path.unlink(missing_ok=True)
        await file.close()


    return {
        "document_id": document_id,
        "filename": original_filename,
        "chunks_created": len(index.chunks),
        "message": "Document uploaded and processed successfully.",
    }



@app.post("/ask")
def ask_question(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    if request.top_k < 1 or request.top_k > 10:
        raise HTTPException(
            status_code=400,
            detail="top_k must be between 1 and 10.",
        )

    index = storage.load_index(request.document_id)

    if index is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found. Upload it again first.",
        )

    retrieved_results = pipeline.ask(
        question=request.question,
        index=index,
        top_k=request.top_k,
    )

    try:
        answer = answer_generator.generate_answer(
            question=request.question,
            retrieved_chunks=retrieved_results,
        )
    except Exception as exc:
        print(f"ANSWER GENERATION ERROR: {type(exc).__name__}: {exc}")
        raise HTTPException(
        status_code=502,
        detail="Answer generation failed. Check the backend terminal."
    )from exc

    return {
        "document_id": request.document_id,
        "question": request.question,
        "answer": answer,
        "sources": [
            {
                "filename": result.chunk.filename,
                "page_number": result.chunk.page_number,
                "text": result.chunk.text,
                "similarity_score": round(result.score, 4),
            }
            for result in retrieved_results
        ],
    }
