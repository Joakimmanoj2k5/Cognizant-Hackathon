"""
TrustScore AI — FastAPI Server
Team RiskWise | Cognizant Technoverse 2026
Serves the web UI and exposes scoring, chat, and file upload API endpoints.

Run:  python app.py
  or: uvicorn app:app --reload --port 8000
"""

import asyncio
import csv
import io
import json
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from main import generate_score, validate_input, analyze_document, chat_response
from agent import get_model_info, clear_chat_history

# ── Security / validation limits ──
MAX_INCOME = 10_000_000
MAX_GIGS = 1_000_000
MAX_BATCH_SIZE = 50
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_CSV_ROWS = 5_000
MAX_CSV_COLUMNS = 50
MAX_EXTRACTED_TEXT_CHARS = 20_000
SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
SESSION_ID_RE = re.compile(SESSION_ID_PATTERN)


def _allowed_origins() -> list[str]:
    """Read allowed browser origins from env, with safe local defaults."""
    raw = os.getenv(
        "TRUSTSCORE_ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    )
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:8000", "http://127.0.0.1:8000"]


def _public_error(status_code: int, detail: str) -> HTTPException:
    """Return client-safe errors without exposing internal exception strings."""
    return HTTPException(status_code=status_code, detail=detail)


# ── App Setup ──
app = FastAPI(
    title="TrustScore AI",
    description="AI-powered credit scoring for gig workers — Team RiskWise",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add browser security headers and reject oversized requests early."""
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_UPLOAD_BYTES + 1024:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request too large. Maximum size is 5MB."},
        )

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'",
    )
    return response

# Serve static files (CSS, JS, images)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Input / Output Models ──

class WorkerProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    income: float = Field(
        ...,
        ge=0,
        le=MAX_INCOME,
        allow_inf_nan=False,
        description="Monthly income in INR",
    )
    rating: float = Field(
        ...,
        ge=0,
        le=5,
        allow_inf_nan=False,
        description="Platform rating (0-5)",
    )
    gigs: int = Field(..., ge=0, le=MAX_GIGS, description="Total gigs completed")
    label: Optional[str] = Field(None, max_length=80)

    @field_validator("income")
    @classmethod
    def income_must_be_positive(cls, v):
        if v < 0:
            raise ValueError("Income cannot be negative")
        return v

    @field_validator("rating")
    @classmethod
    def rating_must_be_valid(cls, v):
        if not (0.0 <= v <= 5.0):
            raise ValueError("Rating must be between 0.0 and 5.0")
        return v

    @field_validator("gigs")
    @classmethod
    def gigs_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError("Gigs count cannot be negative")
        return v


class ScoreResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    risk: str = Field(..., pattern=r"^(Low|Medium|High)$")
    reason: str = Field(..., max_length=800)
    advice: str = Field("", max_length=800)
    loan_eligible: bool
    loan_message: str = Field(..., max_length=400)


class ChatContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    score: Optional[int] = Field(None, ge=0, le=100)
    risk: Optional[str] = Field(None, pattern=r"^(Low|Medium|High)$")
    income: Optional[float] = Field(None, ge=0, le=MAX_INCOME, allow_inf_nan=False)
    rating: Optional[float] = Field(None, ge=0, le=5, allow_inf_nan=False)
    gigs: Optional[int] = Field(None, ge=0, le=MAX_GIGS)
    loan_eligible: Optional[bool] = None
    loan_message: Optional[str] = Field(None, max_length=300)
    document_summary: Optional[str] = Field(None, max_length=1000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=1000, description="User's chat message")
    context: Optional[ChatContext] = Field(None, description="Optional context with last score data")
    session_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=64,
        pattern=SESSION_ID_PATTERN,
        description="Session ID for multi-turn chat",
    )

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, v):
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be blank")
        return stripped


class ChatResponse(BaseModel):
    reply: str = Field(..., max_length=1500)
    session_id: str = Field(..., pattern=SESSION_ID_PATTERN)


# ── Routes ──

@app.get("/")
async def serve_index():
    """Serve the main web UI."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/api/score", response_model=ScoreResult)
async def score_worker(profile: WorkerProfile):
    """
    Score a single gig worker profile.

    - **income**: Monthly income in INR (>= 0)
    - **rating**: Platform rating between 0.0 and 5.0
    - **gigs**: Total completed gigs (>= 0)
    """
    try:
        result = generate_score({
            "income": profile.income,
            "rating": profile.rating,
            "gigs": profile.gigs,
        })
        return result
    except Exception as e:
        print(f"[TrustScore] Scoring error: {e}")
        raise _public_error(500, "Scoring engine error. Please try again.")


@app.post("/api/batch", response_model=list[ScoreResult])
async def score_batch(profiles: list[WorkerProfile]):
    """Score multiple gig worker profiles concurrently (max 50 per request)."""
    if len(profiles) > MAX_BATCH_SIZE:
        raise _public_error(400, f"Maximum {MAX_BATCH_SIZE} profiles per batch")
    if not profiles:
        raise _public_error(400, "At least one profile is required")

    # Run all scoring in parallel using asyncio
    loop = asyncio.get_running_loop()

    async def score_one(profile):
        try:
            return await loop.run_in_executor(None, generate_score, {
                "income": profile.income,
                "rating": profile.rating,
                "gigs": profile.gigs,
            })
        except Exception as e:
            return {
                "score": 0,
                "risk": "High",
                "reason": f"Error: {str(e)}",
                "advice": "",
                "loan_eligible": False,
                "loan_message": "Scoring failed for this profile.",
            }

    results = await asyncio.gather(*[score_one(p) for p in profiles])
    return list(results)


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a PDF or CSV file for AI-powered financial analysis.

    - Supports PDF (text extraction) and CSV (data parsing)
    - Returns extracted data + TrustScore if financial data is found
    """
    # Validate file type
    filename = Path(file.filename or "").name
    allowed_types = {".pdf", ".csv", ".txt"}
    ext = Path(filename).suffix.lower()

    if ext not in allowed_types:
        raise _public_error(
            status_code=400,
            detail="Unsupported file type. Supported: PDF, CSV, TXT"
        )

    # Check content length header first (fast rejection)
    if hasattr(file, 'size') and file.size and file.size > MAX_UPLOAD_BYTES:
        raise _public_error(400, "File too large. Maximum size: 5MB")

    # Read file content with size limit
    try:
        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise _public_error(400, "File too large. Maximum size: 5MB")
        if not content:
            raise _public_error(400, "Uploaded file is empty")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TrustScore] Upload read error: {e}")
        raise _public_error(400, "Failed to read uploaded file")

    # Extract text based on file type
    extracted_text = ""

    if ext == ".pdf":
        if not content.lstrip().startswith(b"%PDF-"):
            raise _public_error(400, "Invalid PDF file")
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise ValueError("encrypted PDF")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise ValueError("too many PDF pages")
            pages_text = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            extracted_text = "\n".join(pages_text)
        except Exception as e:
            print(f"[TrustScore] PDF parse error for {filename}: {e}")
            raise _public_error(400, f"Failed to parse PDF. Upload an unencrypted PDF with {MAX_PDF_PAGES} pages or fewer.")

    elif ext == ".csv":
        if b"\x00" in content[:1024]:
            raise _public_error(400, "Invalid CSV file")
        try:
            decoded = content.decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(decoded))
            lines = []
            for row_number, row in enumerate(reader, start=1):
                if row_number > MAX_CSV_ROWS:
                    break
                safe_row = [cell[:500] for cell in row[:MAX_CSV_COLUMNS]]
                lines.append(", ".join(safe_row))
                if sum(len(line) for line in lines) >= MAX_EXTRACTED_TEXT_CHARS:
                    break
            extracted_text = "\n".join(lines)
        except Exception as e:
            print(f"[TrustScore] CSV parse error for {filename}: {e}")
            raise _public_error(400, "Failed to parse CSV")

    elif ext == ".txt":
        if b"\x00" in content[:1024]:
            raise _public_error(400, "Invalid text file")
        try:
            extracted_text = content.decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[TrustScore] Text parse error for {filename}: {e}")
            raise _public_error(400, "Failed to read text file")

    extracted_text = extracted_text[:MAX_EXTRACTED_TEXT_CHARS]

    if not extracted_text.strip():
        return JSONResponse(content={
            "success": False,
            "message": "No readable text could be extracted from the file.",
            "extracted": None,
            "score_result": None,
        })

    # Analyze the document
    try:
        result = analyze_document(extracted_text)
        return JSONResponse(content={
            "success": True,
            "message": "Document analyzed successfully.",
            "filename": filename,
            "extracted": result["extracted"],
            "score_result": result["score_result"],
        })
    except Exception as e:
        print(f"[TrustScore] Document analysis error for {filename}: {e}")
        raise _public_error(500, "Document analysis failed. Please try again.")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Conversational AI agent for loan/credit questions.
    Supports multi-turn conversation with session memory.

    - **message**: User's question (e.g., "Will I get a loan?")
    - **context**: Optional last score data for context-aware responses
    - **session_id**: Optional session ID for conversation continuity
    """
    # Generate session ID if not provided
    session_id = req.session_id or str(uuid.uuid4())
    context = req.context.model_dump(exclude_none=True) if req.context else None

    try:
        result = chat_response(req.message, context, session_id=session_id)
        return {"reply": result["reply"], "session_id": session_id}
    except Exception as e:
        print(f"[TrustScore] Chat error: {e}")
        raise _public_error(500, "Chat error. Please try again.")


@app.post("/api/chat/clear")
async def clear_chat(
    session_id: str = Query("default", min_length=1, max_length=64, pattern=SESSION_ID_PATTERN),
):
    """Clear chat history for a session."""
    if not SESSION_ID_RE.fullmatch(session_id):
        raise _public_error(400, "Invalid session ID")
    clear_chat_history(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/api/test-data")
async def get_test_data():
    """Return the sample test data for batch analysis demo."""
    test_file = Path(__file__).parent / "test_data.json"
    if not test_file.exists():
        raise HTTPException(status_code=404, detail="Test data file not found")

    with open(test_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@app.get("/api/info")
async def model_info():
    """Return current AI model configuration for UI display."""
    info = get_model_info()
    return JSONResponse(content=info)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    info = get_model_info()
    return {
        "status": "healthy",
        "provider": info["provider"],
        "model": info["model"],
        "version": "2.0.0",
        "team": "RiskWise",
        "features": info["features"],
    }


# ── Run ──
if __name__ == "__main__":
    import uvicorn
    print("\n🛡️  TrustScore AI server starting...")
    print("   Open http://localhost:8000 in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
