"""
TrustScore AI Agent - Core Scoring Logic
Team RiskWise | Cognizant Technoverse 2026
Member 3 (AI Core) deliverable
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# ============================================================
# CONFIG - Switch between providers by changing USE_PROVIDER
# ============================================================
USE_PROVIDER = "groq"  # options: "groq", "openai", "mock"

if USE_PROVIDER == "groq":
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )
    MODEL = "llama-3.3-70b-versatile"
elif USE_PROVIDER == "openai":
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MODEL = "gpt-4o-mini"
else:
    client = None
    MODEL = None


# ============================================================
# PROMPT - The brain of the agent
# ============================================================
SYSTEM_PROMPT = """You are TrustScore, an AI credit analyst for gig workers.

Your job: analyze a gig worker's financial data and produce a TrustScore (0-100)
that reflects their creditworthiness — even though they have no traditional credit history.

SCORING FRAMEWORK (weight each factor):
- Income stability (monthly earnings): 40%
  * < 15,000 INR   → weak
  * 15,000-30,000  → moderate
  * 30,000-60,000  → strong
  * > 60,000       → excellent
- Platform rating (out of 5): 30%
  * < 3.5  → poor reputation
  * 3.5-4.2 → acceptable
  * 4.2-4.7 → good
  * > 4.7  → excellent
- Work volume (total gigs completed): 30%
  * < 20   → very new, high risk
  * 20-80  → building history
  * 80-200 → established
  * > 200  → veteran

RISK LEVELS:
- Score 75-100 → "Low"
- Score 50-74  → "Medium"
- Score 0-49   → "High"

OUTPUT RULES (CRITICAL):
- Respond with ONLY a valid JSON object
- No markdown, no code fences, no extra text
- Use exactly these keys: "score", "risk", "reason"
- "score" must be an integer 0-100
- "risk" must be exactly "Low", "Medium", or "High"
- "reason" must be ONE clear sentence explaining the score
"""


def _validate_input(data: dict) -> tuple[bool, str]:
    """Check that input has required fields with valid types."""
    required = ["income", "rating", "gigs"]
    for field in required:
        if field not in data:
            return False, f"Missing field: {field}"
    if not isinstance(data["income"], (int, float)) or data["income"] < 0:
        return False, "income must be a non-negative number"
    if not isinstance(data["rating"], (int, float)) or not 0 <= data["rating"] <= 5:
        return False, "rating must be between 0 and 5"
    if not isinstance(data["gigs"], int) or data["gigs"] < 0:
        return False, "gigs must be a non-negative integer"
    return True, ""


def _mock_score(data: dict) -> dict:
    """Fallback rule-based scoring when LLM unavailable. Demo safety net."""
    income, rating, gigs = data["income"], data["rating"], data["gigs"]
    income_pts = min(40, (income / 60000) * 40)
    rating_pts = min(30, (rating / 5) * 30)
    gigs_pts = min(30, (gigs / 200) * 30)
    score = int(income_pts + rating_pts + gigs_pts)

    if score >= 75:
        risk = "Low"
    elif score >= 50:
        risk = "Medium"
    else:
        risk = "High"

    return {
        "score": score,
        "risk": risk,
        "reason": f"Monthly income ₹{income}, rating {rating}/5, and {gigs} completed gigs indicate {risk.lower()} credit risk."
    }


def get_ai_score(data: dict) -> dict:
    """
    Main entry point — M2 imports this function.

    Args:
        data: dict with keys 'income' (number), 'rating' (0-5), 'gigs' (int)

    Returns:
        dict: {"score": int, "risk": str, "reason": str}
    """
    # Step 1: validate
    ok, msg = _validate_input(data)
    if not ok:
        return {"score": 0, "risk": "High", "reason": f"Invalid input: {msg}"}

    # Step 2: if no LLM configured, use rule-based fallback
    if USE_PROVIDER == "mock" or client is None:
        return _mock_score(data)

    # Step 3: call the LLM
    user_message = (
        f"Analyze this gig worker:\n"
        f"- Monthly income: ₹{data['income']}\n"
        f"- Platform rating: {data['rating']}/5\n"
        f"- Total gigs completed: {data['gigs']}\n\n"
        f"Return the JSON assessment."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,              # low = consistent outputs
            response_format={"type": "json_object"},  # forces valid JSON
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)

        # Step 4: validate the LLM's output shape
        if not all(k in result for k in ("score", "risk", "reason")):
            raise ValueError("LLM returned incomplete JSON")
        if result["risk"] not in ("Low", "Medium", "High"):
            raise ValueError("Invalid risk level")

        result["score"] = int(result["score"])
        return result

    except Exception as e:
        # Graceful fallback — your demo never crashes
        print(f"[warning] LLM call failed ({e}), using fallback scorer")
        return _mock_score(data)


# ============================================================
# Quick test when you run this file directly
# ============================================================
if __name__ == "__main__":
    sample = {"income": 30000, "rating": 4.5, "gigs": 100}
    result = get_ai_score(sample)
    print("Input:", sample)
    print("Output:", json.dumps(result, indent=2))
    import time
    start = time.time()
    result = get_ai_score(sample)
    print(f"Scored in {time.time()-start:.2f}s")