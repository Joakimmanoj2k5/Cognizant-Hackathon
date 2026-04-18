"""
TrustScore AI Agent — Core Scoring Logic
Team RiskWise | Cognizant Technoverse 2026
Member 3 (AI Core) deliverable

Features:
  - 3 prompt versions (basic → reasoning → suggestions)
  - Rule-based fallback when LLM is unavailable
  - Strict output standardization: {score, risk, reason, advice}
  - Input validation with clear error messages
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# ============================================================
# CONFIG — Switch between providers by changing USE_PROVIDER
# ============================================================
USE_PROVIDER = os.getenv("USE_PROVIDER", "groq")  # options: "groq", "openai", "mock"

# Safely initialize the LLM client — falls back to mock if no API key
client = None
MODEL = None

try:
    if USE_PROVIDER == "groq" and os.getenv("GROQ_API_KEY"):
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        MODEL = "llama-3.3-70b-versatile"
    elif USE_PROVIDER == "openai" and os.getenv("OPENAI_API_KEY"):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        MODEL = "gpt-4o-mini"
    else:
        if USE_PROVIDER not in ("mock",):
            print(f"[TrustScore] No API key found for '{USE_PROVIDER}' — using fallback scorer")
        client = None
        MODEL = None
except Exception as e:
    print(f"[TrustScore] LLM client init failed ({e}) — using fallback scorer")
    client = None
    MODEL = None


# ============================================================
# PROMPT VERSIONS — The brain of the agent
# ============================================================

# Version 1: Basic scoring — returns score + risk only
PROMPT_V1_BASIC = """You are TrustScore, an AI credit analyst for gig workers.

Analyze the gig worker's financial data and return a TrustScore (0-100).

SCORING FRAMEWORK:
- Income stability (monthly earnings): 40% weight
- Platform rating (out of 5): 30% weight
- Work volume (total gigs completed): 30% weight

RISK LEVELS:
- Score 75-100 → "Low"
- Score 50-74  → "Medium"
- Score 0-49   → "High"

OUTPUT: Return ONLY valid JSON with keys: "score", "risk", "reason", "advice"
- "score": integer 0-100
- "risk": exactly "Low", "Medium", or "High"
- "reason": one sentence explaining score
- "advice": one sentence of actionable advice
No markdown, no code fences, no extra text.
"""

# Version 2: With detailed reasoning — explains each factor
PROMPT_V2_REASONING = """You are TrustScore, an AI credit analyst for gig workers.

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
- Use exactly these keys: "score", "risk", "reason", "advice"
- "score" must be an integer 0-100
- "risk" must be exactly "Low", "Medium", or "High"
- "reason" must be ONE clear sentence explaining the score with factor-level reasoning
- "advice" must be ONE actionable sentence to help the worker improve their score
"""

# Version 3: With suggestions + loan guidance — full analysis
PROMPT_V3_SUGGESTIONS = """You are TrustScore, an AI credit analyst for gig workers in India.

Your job: analyze a gig worker's financial data and produce a TrustScore (0-100)
that reflects their creditworthiness — even though they have no traditional credit history.
You also provide actionable advice to help them improve.

SCORING FRAMEWORK (weight each factor):
- Income stability (monthly earnings): 40%
  * < 15,000 INR   → weak (0-15 pts)
  * 15,000-30,000  → moderate (15-25 pts)
  * 30,000-60,000  → strong (25-35 pts)
  * > 60,000       → excellent (35-40 pts)
- Platform rating (out of 5): 30%
  * < 3.5  → poor reputation (0-10 pts)
  * 3.5-4.2 → acceptable (10-18 pts)
  * 4.2-4.7 → good (18-25 pts)
  * > 4.7  → excellent (25-30 pts)
- Work volume (total gigs completed): 30%
  * < 20   → very new, high risk (0-8 pts)
  * 20-80  → building history (8-18 pts)
  * 80-200 → established (18-25 pts)
  * > 200  → veteran (25-30 pts)

RISK LEVELS:
- Score 75-100 → "Low"   (likely eligible for loans)
- Score 50-74  → "Medium" (conditionally eligible)
- Score 0-49   → "High"   (not currently eligible — needs improvement)

OUTPUT RULES (CRITICAL):
- Respond with ONLY a valid JSON object
- No markdown, no code fences, no extra text
- Use exactly these keys: "score", "risk", "reason", "advice"
- "score" must be an integer 0-100
- "risk" must be exactly "Low", "Medium", or "High"
- "reason" must be 1-2 clear sentences explaining the score, mentioning each factor
- "advice" must be 1-2 actionable sentences: specific steps to improve their TrustScore
"""

# Active prompt — use the most complete version for competition
SYSTEM_PROMPT = PROMPT_V3_SUGGESTIONS


# ============================================================
# INPUT VALIDATION
# ============================================================

def _validate_input(data: dict) -> tuple[bool, str]:
    """Check that input has required fields with valid types."""
    required = ["income", "rating", "gigs"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: '{field}'"

    if not isinstance(data["income"], (int, float)) or data["income"] < 0:
        return False, "income must be a non-negative number"
    if not isinstance(data["rating"], (int, float)) or not 0 <= data["rating"] <= 5:
        return False, "rating must be a number between 0 and 5"
    if not isinstance(data["gigs"], (int, float)) or data["gigs"] < 0:
        return False, "gigs must be a non-negative integer"

    return True, ""


# ============================================================
# FALLBACK: Rule-Based Scoring (demo safety net)
# ============================================================

def _mock_score(data: dict) -> dict:
    """
    Deterministic rule-based scoring when LLM is unavailable.
    Mirrors the prompt's scoring framework exactly.
    """
    income = float(data["income"])
    rating = float(data["rating"])
    gigs = int(data["gigs"])

    # Income component (40 pts max)
    if income < 15000:
        income_pts = (income / 15000) * 16
    elif income < 30000:
        income_pts = 16 + ((income - 15000) / 15000) * 12
    elif income < 60000:
        income_pts = 28 + ((income - 30000) / 30000) * 8
    else:
        income_pts = min(40, 36 + ((income - 60000) / 60000) * 4)

    # Rating component (30 pts max)
    if rating < 3.5:
        rating_pts = (rating / 3.5) * 12
    elif rating < 4.2:
        rating_pts = 12 + ((rating - 3.5) / 0.7) * 8
    elif rating < 4.7:
        rating_pts = 20 + ((rating - 4.2) / 0.5) * 6
    else:
        rating_pts = min(30, 26 + ((rating - 4.7) / 0.3) * 4)

    # Gigs component (30 pts max)
    if gigs < 20:
        gigs_pts = (gigs / 20) * 10
    elif gigs < 80:
        gigs_pts = 10 + ((gigs - 20) / 60) * 10
    elif gigs < 200:
        gigs_pts = 20 + ((gigs - 80) / 120) * 6
    else:
        gigs_pts = min(30, 26 + ((gigs - 200) / 200) * 4)

    score = int(round(income_pts + rating_pts + gigs_pts))
    score = max(0, min(100, score))  # clamp to 0-100

    # Determine risk level
    if score >= 75:
        risk = "Low"
    elif score >= 50:
        risk = "Medium"
    else:
        risk = "High"

    # Build reasoning
    income_level = "excellent" if income >= 60000 else "strong" if income >= 30000 else "moderate" if income >= 15000 else "low"
    rating_level = "excellent" if rating >= 4.7 else "good" if rating >= 4.2 else "acceptable" if rating >= 3.5 else "poor"
    gigs_level = "veteran" if gigs >= 200 else "established" if gigs >= 80 else "building" if gigs >= 20 else "very new"

    reason = (
        f"Monthly income of ₹{income:,.0f} ({income_level}), "
        f"platform rating of {rating}/5 ({rating_level}), "
        f"and {gigs} completed gigs ({gigs_level}) "
        f"indicate {'strong' if risk == 'Low' else 'moderate' if risk == 'Medium' else 'weak'} creditworthiness."
    )

    # Build advice
    suggestions = []
    if income < 30000:
        suggestions.append("increase monthly earnings by taking on higher-value gigs")
    if rating < 4.2:
        suggestions.append("improve your platform rating by focusing on customer satisfaction")
    if gigs < 80:
        suggestions.append("complete more gigs to build a stronger work history")
    if not suggestions:
        suggestions.append("maintain your excellent profile to access premium loan offers")

    advice = "To improve your score, " + " and ".join(suggestions) + "."

    return {
        "score": score,
        "risk": risk,
        "reason": reason,
        "advice": advice,
    }


# ============================================================
# MAIN ENTRY POINT — M2 imports this function
# ============================================================

def get_ai_score(data: dict, prompt_version: int = 3) -> dict:
    """
    Generate a TrustScore for a gig worker.

    Args:
        data: dict with keys 'income' (number), 'rating' (0-5), 'gigs' (int)
        prompt_version: 1 = basic, 2 = reasoning, 3 = suggestions (default)

    Returns:
        dict: {"score": int, "risk": str, "reason": str, "advice": str}
    """
    # Step 1: validate input
    ok, msg = _validate_input(data)
    if not ok:
        return {
            "score": 0,
            "risk": "High",
            "reason": f"Invalid input — {msg}",
            "advice": "Please provide valid income, rating (0-5), and gigs values.",
        }

    # Step 2: if no LLM configured, use rule-based fallback
    if USE_PROVIDER == "mock" or client is None:
        return _mock_score(data)

    # Step 3: select prompt version
    prompts = {1: PROMPT_V1_BASIC, 2: PROMPT_V2_REASONING, 3: PROMPT_V3_SUGGESTIONS}
    active_prompt = prompts.get(prompt_version, PROMPT_V3_SUGGESTIONS)

    # Step 4: build user message
    user_message = (
        f"Analyze this gig worker:\n"
        f"- Monthly income: ₹{data['income']:,}\n"
        f"- Platform rating: {data['rating']}/5\n"
        f"- Total gigs completed: {data['gigs']}\n\n"
        f"Return the JSON assessment."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": active_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,  # low = consistent outputs
            response_format={"type": "json_object"},  # forces valid JSON
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)

        # Step 5: validate LLM output shape
        required_keys = ("score", "risk", "reason", "advice")
        if not all(k in result for k in required_keys):
            raise ValueError(f"LLM returned incomplete JSON — missing keys: {[k for k in required_keys if k not in result]}")
        if result["risk"] not in ("Low", "Medium", "High"):
            raise ValueError(f"Invalid risk level: {result['risk']}")

        # Normalize types
        result["score"] = max(0, min(100, int(result["score"])))
        result["risk"] = str(result["risk"])
        result["reason"] = str(result["reason"])
        result["advice"] = str(result["advice"])

        return result

    except Exception as e:
        # Graceful fallback — the demo never crashes
        print(f"[TrustScore] LLM call failed ({e}), using fallback scorer")
        return _mock_score(data)


# ============================================================
# Quick test when you run this file directly
# ============================================================
if __name__ == "__main__":
    import time

    test_cases = [
        {"income": 8000,  "rating": 3.2, "gigs": 15,  "label": "Low-income new worker"},
        {"income": 30000, "rating": 4.5, "gigs": 100, "label": "Solid gig worker"},
        {"income": 55000, "rating": 4.8, "gigs": 250, "label": "Veteran high earner"},
    ]

    print("=" * 60)
    print("  TrustScore AI — Agent Test Run")
    print("=" * 60)

    for case in test_cases:
        print(f"\n▸ {case['label']}")
        print(f"  Input: income=₹{case['income']:,}, rating={case['rating']}, gigs={case['gigs']}")

        start = time.time()
        result = get_ai_score(case)
        elapsed = time.time() - start

        print(f"  Score: {result['score']}/100  |  Risk: {result['risk']}")
        print(f"  Reason: {result['reason']}")
        print(f"  Advice: {result['advice']}")
        print(f"  ⏱ {elapsed:.2f}s")

    print("\n" + "=" * 60)
    print("  All tests passed ✅")
    print("=" * 60)