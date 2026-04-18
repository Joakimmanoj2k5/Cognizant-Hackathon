"""
TrustScore AI — FastAPI Server
Team RiskWise | Cognizant Technoverse 2026
Serves the web UI and exposes scoring API endpoints.

Run:  python app.py
  or: uvicorn app:app --reload --port 8000
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from main import generate_score, validate_input

# ── App Setup ──
app = FastAPI(
    title="TrustScore AI",
    description="AI-powered credit scoring for gig workers — Team RiskWise",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS, images)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Input / Output Models ──

class WorkerProfile(BaseModel):
    income: float = Field(..., ge=0, description="Monthly income in INR")
    rating: float = Field(..., ge=0, le=5, description="Platform rating (0-5)")
    gigs: int = Field(..., ge=0, description="Total gigs completed")
    label: Optional[str] = None

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
    score: int
    risk: str
    reason: str
    advice: str = ""
    loan_eligible: bool
    loan_message: str


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
        raise HTTPException(status_code=500, detail=f"Scoring engine error: {str(e)}")


@app.post("/api/batch", response_model=list[ScoreResult])
async def score_batch(profiles: list[WorkerProfile]):
    """Score multiple gig worker profiles (max 50 per request)."""
    if len(profiles) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 profiles per batch")

    results = []
    for profile in profiles:
        try:
            result = generate_score({
                "income": profile.income,
                "rating": profile.rating,
                "gigs": profile.gigs,
            })
            results.append(result)
        except Exception as e:
            results.append({
                "score": 0,
                "risk": "High",
                "reason": f"Error: {str(e)}",
                "advice": "",
                "loan_eligible": False,
                "loan_message": "Scoring failed for this profile.",
            })
    return results


@app.get("/api/test-data")
async def get_test_data():
    """Return the sample test data for batch analysis demo."""
    test_file = Path(__file__).parent / "test_data.json"
    if not test_file.exists():
        raise HTTPException(status_code=404, detail="Test data file not found")

    with open(test_file, "r") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    from agent import USE_PROVIDER
    return {
        "status": "healthy",
        "provider": USE_PROVIDER,
        "version": "1.0.0",
        "team": "RiskWise",
    }


# ── Run ──
if __name__ == "__main__":
    import uvicorn
    print("\n🛡️  TrustScore AI server starting...")
    print("   Open http://localhost:8000 in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
