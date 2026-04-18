"""
TrustScore AI — FastAPI Backend
Team RiskWise | Cognizant Technoverse 2026
Serves the web UI and exposes scoring API endpoints.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import get_ai_score

# ── App Setup ──
app = FastAPI(
    title="TrustScore AI",
    description="AI-powered credit scoring for gig workers",
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


# ── Models ──
class WorkerProfile(BaseModel):
    income: float = Field(..., ge=0, description="Monthly income in INR")
    rating: float = Field(..., ge=0, le=5, description="Platform rating (0-5)")
    gigs: int = Field(..., ge=0, description="Total gigs completed")
    label: Optional[str] = None


class ScoreResult(BaseModel):
    score: int
    risk: str
    reason: str


# ── Routes ──
@app.get("/")
async def serve_index():
    """Serve the main web UI."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/api/score", response_model=ScoreResult)
async def score_worker(profile: WorkerProfile):
    """Score a single gig worker profile."""
    try:
        result = get_ai_score({
            "income": profile.income,
            "rating": profile.rating,
            "gigs": profile.gigs,
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch", response_model=list[ScoreResult])
async def score_batch(profiles: list[WorkerProfile]):
    """Score multiple gig worker profiles."""
    if len(profiles) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 profiles per batch")

    results = []
    for profile in profiles:
        try:
            result = get_ai_score({
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


# ── Run ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
