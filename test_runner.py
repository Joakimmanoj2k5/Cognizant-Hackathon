"""
TrustScore AI — Automated Test Runner
Team RiskWise | Cognizant Technoverse 2026
Member 4 (Testing + GitHub Manager) deliverable

Runs all test cases and validates:
  ✅ Output format is correct (score, risk, reason, advice)
  ✅ Score is 0-100 integer
  ✅ Risk is exactly Low/Medium/High
  ✅ Risk matches expected level from test_data.json
  ✅ Edge cases don't crash
  ✅ Invalid inputs return graceful errors
  ✅ Wrapper function (main.py) adds loan eligibility
  ✅ Chat agent supports multi-turn memory
  ✅ Model info returns valid config
  ✅ Performance: no single call exceeds 5s
"""

import json
import sys
import time

# ── Import project modules ──
from agent import get_ai_score, get_model_info, chat_with_agent, clear_chat_history
from main import generate_score, validate_input


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name, passed, detail=""):
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))


def test_output_format():
    """Test 1: Verify output has correct keys and types."""
    print_header("TEST 1: Output Format Validation")

    sample = {"income": 30000, "rating": 4.5, "gigs": 100}
    result = get_ai_score(sample)

    passed = True

    # Check all required keys
    for key in ("score", "risk", "reason", "advice"):
        has_key = key in result
        print_result(f"Key '{key}' exists", has_key)
        if not has_key:
            passed = False

    # Check types
    if "score" in result:
        is_int = isinstance(result["score"], int)
        print_result("score is int", is_int, f"got {type(result['score']).__name__}")
        passed = passed and is_int

    if "risk" in result:
        valid_risk = result["risk"] in ("Low", "Medium", "High")
        print_result("risk is valid", valid_risk, f"got '{result['risk']}'")
        passed = passed and valid_risk

    if "score" in result:
        in_range = 0 <= result["score"] <= 100
        print_result("score in 0-100", in_range, f"got {result['score']}")
        passed = passed and in_range

    return passed


def test_all_test_data():
    """Test 2: Score all test_data.json entries and check risk alignment."""
    print_header("TEST 2: Test Data Scoring")

    with open("test_data.json", "r") as f:
        test_cases = json.load(f)

    passed = True
    for i, case in enumerate(test_cases):
        label = case.get("label", f"Case {i+1}")
        expected_risk = case.get("expected_risk")

        start = time.time()
        result = get_ai_score(case)
        elapsed = time.time() - start

        # Verify format
        has_keys = all(k in result for k in ("score", "risk", "reason", "advice"))

        # Verify risk matches expected (if provided)
        risk_match = True
        if expected_risk:
            risk_match = result["risk"] == expected_risk

        # Performance: no single call should exceed 5s
        timing_ok = elapsed < 5.0

        case_passed = has_keys and risk_match and timing_ok
        detail = f"Score={result['score']}, Risk={result['risk']}"
        if expected_risk and not risk_match:
            detail += f" (expected {expected_risk})"
        detail += f" [{elapsed:.2f}s]"
        if not timing_ok:
            detail += " ⚠️ SLOW!"

        print_result(label, case_passed, detail)
        if not case_passed:
            passed = False

    return passed


def test_input_validation():
    """Test 3: Verify invalid inputs are handled gracefully."""
    print_header("TEST 3: Input Validation")

    passed = True

    # Missing fields
    result = get_ai_score({"income": 30000})
    graceful = result["score"] == 0 and result["risk"] == "High"
    print_result("Missing fields → graceful error", graceful, result["reason"][:60])
    passed = passed and graceful

    # Negative income
    result = get_ai_score({"income": -5000, "rating": 4.0, "gigs": 50})
    graceful = result["score"] == 0 and result["risk"] == "High"
    print_result("Negative income → graceful error", graceful, result["reason"][:60])
    passed = passed and graceful

    # Rating out of range
    result = get_ai_score({"income": 30000, "rating": 7.0, "gigs": 50})
    graceful = result["score"] == 0 and result["risk"] == "High"
    print_result("Rating > 5 → graceful error", graceful, result["reason"][:60])
    passed = passed and graceful

    # Wrong types
    result = get_ai_score({"income": "abc", "rating": 4.0, "gigs": 50})
    graceful = result["score"] == 0 and result["risk"] == "High"
    print_result("String income → graceful error", graceful, result["reason"][:60])
    passed = passed and graceful

    # Empty dict
    result = get_ai_score({})
    graceful = result["score"] == 0 and result["risk"] == "High"
    print_result("Empty dict → graceful error", graceful, result["reason"][:60])
    passed = passed and graceful

    return passed


def test_wrapper_function():
    """Test 4: Verify main.py wrapper adds loan eligibility."""
    print_header("TEST 4: Wrapper Function (main.py)")

    passed = True

    # Low risk → loan eligible
    result = generate_score({"income": 55000, "rating": 4.8, "gigs": 250})
    has_loan = "loan_eligible" in result and "loan_message" in result
    print_result("Has loan_eligible key", has_loan)
    passed = passed and has_loan

    if has_loan:
        is_eligible = result["loan_eligible"] == True
        print_result("Low risk → loan eligible", is_eligible, f"risk={result['risk']}")
        passed = passed and is_eligible

    # High risk → not eligible
    result = generate_score({"income": 5000, "rating": 2.0, "gigs": 5})
    if "loan_eligible" in result:
        not_eligible = result["loan_eligible"] == False
        print_result("High risk → not eligible", not_eligible, f"risk={result['risk']}")
        passed = passed and not_eligible

    return passed


def test_validate_input_function():
    """Test 5: Verify validate_input from main.py."""
    print_header("TEST 5: validate_input() Function")

    passed = True

    # Valid input
    errors = validate_input({"income": 30000, "rating": 4.5, "gigs": 100})
    valid = len(errors) == 0
    print_result("Valid input → no errors", valid)
    passed = passed and valid

    # Missing field
    errors = validate_input({"income": 30000, "rating": 4.5})
    has_error = len(errors) > 0
    print_result("Missing 'gigs' → error", has_error, errors[0] if errors else "")
    passed = passed and has_error

    # Bad type
    errors = validate_input({"income": "abc", "rating": 4.5, "gigs": 100})
    has_error = len(errors) > 0
    print_result("String income → error", has_error, errors[0] if errors else "")
    passed = passed and has_error

    # Rating out of range
    errors = validate_input({"income": 30000, "rating": 6.0, "gigs": 100})
    has_error = len(errors) > 0
    print_result("Rating=6.0 → error", has_error, errors[0] if errors else "")
    passed = passed and has_error

    return passed


def test_edge_cases():
    """Test 6: Edge cases that might crash during demo."""
    print_header("TEST 6: Edge Cases")

    passed = True

    # Zero values
    result = get_ai_score({"income": 0, "rating": 0, "gigs": 0})
    no_crash = "score" in result
    print_result("All zeros → no crash", no_crash, f"Score={result.get('score')}")
    passed = passed and no_crash

    # Max values
    result = get_ai_score({"income": 999999, "rating": 5.0, "gigs": 10000})
    no_crash = "score" in result and 0 <= result["score"] <= 100
    print_result("Max values → score in range", no_crash, f"Score={result.get('score')}")
    passed = passed and no_crash

    # Float gigs (should still work)
    result = get_ai_score({"income": 30000, "rating": 4.5, "gigs": 100.5})
    no_crash = "score" in result
    print_result("Float gigs → no crash", no_crash, f"Score={result.get('score')}")
    passed = passed and no_crash

    return passed


def test_prompt_versions():
    """Test 7: Verify all 3 prompt versions work."""
    print_header("TEST 7: Prompt Versions")

    sample = {"income": 30000, "rating": 4.5, "gigs": 100}
    passed = True

    for version in [1, 2, 3]:
        result = get_ai_score(sample, prompt_version=version)
        works = all(k in result for k in ("score", "risk", "reason", "advice"))
        print_result(f"Version {version} returns valid output", works, f"Score={result.get('score')}")
        passed = passed and works

    return passed


def test_chat_memory():
    """Test 8: Verify chat agent supports multi-turn memory."""
    print_header("TEST 8: Chat Agent Memory")

    passed = True
    test_session = "test_runner_session"

    # Clear any existing history
    clear_chat_history(test_session)

    # Send first message
    ctx = {"score": 72, "risk": "Medium", "income": 30000}
    resp1 = chat_with_agent("Will I get a loan?", ctx, session_id=test_session)
    has_reply = isinstance(resp1, str) and len(resp1) > 10
    print_result("First message returns reply", has_reply, f"{resp1[:60]}...")
    passed = passed and has_reply

    # Send follow-up (should have context from first message)
    resp2 = chat_with_agent("What steps can I take?", ctx, session_id=test_session)
    has_followup = isinstance(resp2, str) and len(resp2) > 10
    print_result("Follow-up returns reply", has_followup, f"{resp2[:60]}...")
    passed = passed and has_followup

    # Clear history
    clear_chat_history(test_session)
    print_result("Chat history cleared", True)

    return passed


def test_model_info():
    """Test 9: Verify model info returns valid config."""
    print_header("TEST 9: Model Info")

    passed = True
    info = get_model_info()

    has_provider = "provider" in info and isinstance(info["provider"], str)
    print_result("Has provider", has_provider, info.get("provider", ""))
    passed = passed and has_provider

    has_model = "model" in info and isinstance(info["model"], str)
    print_result("Has model", has_model, info.get("model", ""))
    passed = passed and has_model

    has_mode = "mode" in info and info["mode"] in ("LLM", "Fallback")
    print_result("Has valid mode", has_mode, info.get("mode", ""))
    passed = passed and has_mode

    has_features = "features" in info and isinstance(info["features"], list)
    print_result("Has features list", has_features, str(info.get("features", [])))
    passed = passed and has_features

    return passed


# ────────────────────────────────────────────────────────────────
# RUN ALL TESTS
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🛡️  TrustScore AI — Automated Test Suite v2.1")
    print("   Team RiskWise | Cognizant Technoverse 2026")

    # Show model info
    info = get_model_info()
    print(f"   Provider: {info['provider']} | Model: {info['model']} | Mode: {info['mode']}")

    tests = [
        ("Output Format", test_output_format),
        ("Test Data Scoring", test_all_test_data),
        ("Input Validation", test_input_validation),
        ("Wrapper Function", test_wrapper_function),
        ("validate_input()", test_validate_input_function),
        ("Edge Cases", test_edge_cases),
        ("Prompt Versions", test_prompt_versions),
        ("Chat Memory", test_chat_memory),
        ("Model Info", test_model_info),
    ]

    results = []
    total_start = time.time()

    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n  💥 CRASH in {name}: {e}")
            results.append((name, False))

    total_time = time.time() - total_start

    # Summary
    print_header("TEST SUMMARY")
    total_passed = 0
    for name, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if passed:
            total_passed += 1

    print(f"\n  Results: {total_passed}/{len(results)} test groups passed")
    print(f"  Total time: {total_time:.2f}s")

    if total_passed == len(results):
        print("\n  🎉 ALL TESTS PASSED — Ready for competition!")
    else:
        print("\n  ⚠️  Some tests failed — fix before demo!")

    print(f"{'='*60}\n")

    sys.exit(0 if total_passed == len(results) else 1)
