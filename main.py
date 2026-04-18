"""
TrustScore Backend — API Wrapper + Input Validation
Team RiskWise | Cognizant Technoverse 2026
Member 2 (Backend) deliverable

This module wraps M3's AI core (agent.py) into a clean function
and adds loan eligibility logic on top.
"""

from agent import get_ai_score


# ─── WRAPPER FUNCTION (M2's core deliverable) ────────────────────────────────

def generate_score(data: dict) -> dict:
    """
    Wrapper around M3's get_ai_score().
    Adds loan eligibility decision on top of AI output.

    Args:
        data: dict with keys 'income', 'rating', 'gigs'

    Returns:
        dict: {
            "score": int,
            "risk": "Low" | "Medium" | "High",
            "reason": str,
            "advice": str,
            "loan_eligible": bool,
            "loan_message": str,
        }
    """
    # Step 1: Input validation — reject bad data early
    errors = validate_input(data)
    if errors:
        return {
            "score": 0,
            "risk": "High",
            "reason": f"Invalid input: {'; '.join(errors)}",
            "advice": "Please correct your input and try again.",
            "loan_eligible": False,
            "loan_message": "Cannot assess — invalid input data.",
        }

    # Step 2: Call AI core
    ai_result = get_ai_score(data)

    # Step 3: Loan eligibility decision based on risk level
    if ai_result["risk"] == "Low":
        loan_eligible = True
        loan_message = "✅ Congratulations! You qualify for a loan up to ₹1,00,000."
    elif ai_result["risk"] == "Medium":
        loan_eligible = True
        loan_message = "⚠️ Conditionally eligible — you may qualify for a loan up to ₹30,000."
    else:
        loan_eligible = False
        loan_message = "❌ Not eligible at this time. Keep building your profile and try again in 3 months."

    return {
        "score": ai_result["score"],
        "risk": ai_result["risk"],
        "reason": ai_result["reason"],
        "advice": ai_result.get("advice", ""),
        "loan_eligible": loan_eligible,
        "loan_message": loan_message,
    }


# ─── INPUT VALIDATION (M2's Task 3) ──────────────────────────────────────────

def validate_input(data: dict) -> list[str]:
    """
    Validate input data before sending to AI.
    Returns a list of error messages (empty = valid).
    """
    errors = []

    # Check missing fields
    for field in ("income", "rating", "gigs"):
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        return errors  # can't validate types if fields are missing

    # Check data types
    if not isinstance(data["income"], (int, float)):
        errors.append("'income' must be a number")
    elif data["income"] < 0:
        errors.append("'income' cannot be negative")

    if not isinstance(data["rating"], (int, float)):
        errors.append("'rating' must be a number")
    elif not (0.0 <= data["rating"] <= 5.0):
        errors.append("'rating' must be between 0.0 and 5.0")

    if not isinstance(data["gigs"], (int, float)):
        errors.append("'gigs' must be a number")
    elif data["gigs"] < 0:
        errors.append("'gigs' cannot be negative")

    return errors


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("Testing generate_score wrapper...\n")

    # Valid input
    result = generate_score({"income": 35000, "rating": 4.5, "gigs": 120})
    print("Valid input result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Invalid input — missing field
    result = generate_score({"income": 35000, "rating": 4.5})
    print("\nMissing 'gigs' field:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Invalid input — bad type
    result = generate_score({"income": "abc", "rating": 4.5, "gigs": 50})
    print("\nBad 'income' type:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n✅ Wrapper tests complete")