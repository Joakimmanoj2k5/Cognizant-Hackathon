"""
TrustScore Backend - API Wrapper + Input Validation
Team RiskWise | Cognizant Technoverse 2026
Member 2 (Backend) deliverable
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from agent import get_ai_score

app = FastAPI(
    title="TrustScore API",
    description="AI-powered credit scoring for gig workers",
    version="1.0.0",
)

# Allow React frontend (M1) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── INPUT SCHEMA WITH VALIDATION ────────────────────────────────────────────

class GigWorkerInput(BaseModel):
    income: float = Field(..., description="Monthly income in INR", example=25000)
    rating: float = Field(..., description="Platform rating (0.0 to 5.0)", example=4.5)
    gigs: int = Field(..., description="Total gigs completed", example=80)

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


# ─── OUTPUT SCHEMA ────────────────────────────────────────────────────────────

class TrustScoreOutput(BaseModel):
    score: int
    risk: str
    reason: str
    advice: Optional[str] = None
    loan_eligible: bool
    loan_message: str


# ─── WRAPPER FUNCTION (M2's core task) ───────────────────────────────────────

def generate_score(data: dict) -> TrustScoreOutput:
    """
    Wrapper around M3's get_ai_score().
    Adds loan eligibility decision on top of AI output.
    """
    ai_result = get_ai_score(data)

    # Loan decision based on risk level
    if ai_result["risk"] == "Low":
        loan_eligible = True
        loan_message = "Congratulations! You qualify for a loan up to Rs.1,00,000."
    elif ai_result["risk"] == "Medium":
        loan_eligible = True
        loan_message = "Conditionally eligible. You may qualify for a loan up to Rs.30,000."
    else:
        loan_eligible = False
        loan_message = "Not eligible at this time. Keep building your profile and try again in 3 months."

    return TrustScoreOutput(
        score=ai_result["score"],
        risk=ai_result["risk"],
        reason=ai_result["reason"],
        advice=ai_result.get("advice"),
        loan_eligible=loan_eligible,
        loan_message=loan_message,
    )


# ─── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "TrustScore API is running",
        "version": "1.0.0",
        "team": "RiskWise"
    }


@app.post("/score", response_model=TrustScoreOutput)
def score(data: GigWorkerInput):
    """
    Generate a TrustScore for a gig worker.

    - **income**: Monthly income in INR (must be >= 0)
    - **rating**: Platform rating between 0.0 and 5.0
    - **gigs**: Total completed gigs (must be >= 0)
    """
    try:
        result = generate_score(data.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring engine error: {str(e)}")


@app.get("/health")
def health_check():
    return {"status": "healthy", "provider": "groq/openai via agent.py"}