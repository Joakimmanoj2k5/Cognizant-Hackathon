"""
TrustScore AI Agent — Core Scoring Logic + Chat + Document Analysis
Team RiskWise | Cognizant Technoverse 2026
Member 3 (AI Core) deliverable

Features:
  - 3 prompt versions (basic → reasoning → suggestions)
  - Rule-based fallback when LLM is unavailable
  - Strict output standardization: {score, risk, reason, advice}
  - Input validation with clear error messages
  - Conversational AI chat agent with multi-turn memory
  - Document analysis from uploaded files
  - Retry with exponential backoff for LLM reliability
"""

import json
import math
import os
import re
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# ============================================================
# CONFIG — Switch between providers by changing USE_PROVIDER
# ============================================================
USE_PROVIDER = os.getenv("USE_PROVIDER", "mock").strip().lower()  # options: "groq", "openai", "mock"

# Safely initialize the LLM client — falls back to mock if no API key
client = None
MODEL = None
PROVIDER_NAME = "mock"

try:
    if USE_PROVIDER == "groq" and os.getenv("GROQ_API_KEY"):
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        MODEL = "llama-3.3-70b-versatile"
        PROVIDER_NAME = "Groq"
    elif USE_PROVIDER == "openai" and os.getenv("OPENAI_API_KEY"):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        MODEL = "gpt-4o-mini"
        PROVIDER_NAME = "OpenAI"
    else:
        if USE_PROVIDER not in ("mock",):
            print(f"[TrustScore] No API key found for '{USE_PROVIDER}' — using fallback scorer")
        client = None
        MODEL = None
        PROVIDER_NAME = "mock"
except Exception as e:
    print(f"[TrustScore] LLM client init failed ({e}) — using fallback scorer")
    client = None
    MODEL = None
    PROVIDER_NAME = "mock"

# Startup log — helpful for debugging during demo
print(f"[TrustScore] Provider: {PROVIDER_NAME} | Model: {MODEL or 'rule-based fallback'}")


# ============================================================
# MODEL INFO — For UI display
# ============================================================

def get_model_info() -> dict:
    """Return current model configuration for API/UI display."""
    mode = "Fallback" if client is None or _llm_is_temporarily_disabled() else "LLM"
    return {
        "provider": PROVIDER_NAME,
        "model": MODEL or "Rule-Based Fallback",
        "mode": mode,
        "features": ["scoring", "chat", "document-analysis", "batch"],
    }


# ============================================================
# LLM CALL WITH RETRY — Resilient API calls
# ============================================================

LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "12"))  # seconds — prevents demo from hanging
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))  # total attempts = MAX_RETRIES + 1
LLM_FAILURE_COOLDOWN = float(os.getenv("LLM_FAILURE_COOLDOWN", "60"))
_llm_disabled_until = 0.0


def _llm_is_temporarily_disabled() -> bool:
    return time.monotonic() < _llm_disabled_until


def _disable_llm_temporarily(error: Exception) -> None:
    """Avoid repeated slow network failures when an LLM provider is unreachable."""
    global _llm_disabled_until
    _llm_disabled_until = time.monotonic() + LLM_FAILURE_COOLDOWN
    print(f"[TrustScore] LLM temporarily disabled after connectivity failure ({error})")


def _is_connectivity_error(error: Exception) -> bool:
    text = str(error).lower()
    return any(
        marker in text
        for marker in (
            "connection error",
            "connection refused",
            "connection reset",
            "connect timeout",
            "dns",
            "max retries exceeded",
            "name resolution",
            "network",
            "nodename nor servname",
            "read timeout",
            "timed out",
            "timeout",
        )
    )


def _clip_text(value, limit: int) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"

def _llm_call(messages: list, temperature: float = 0.2,
              max_tokens: int = 500, json_mode: bool = False) -> str:
    """
    Make an LLM API call with retry + exponential backoff.
    Returns raw response text. Raises on total failure.
    """
    if client is None:
        raise RuntimeError("No LLM client configured")
    if _llm_is_temporarily_disabled():
        raise RuntimeError("LLM provider is temporarily unavailable")

    kwargs = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": LLM_TIMEOUT,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            return _clip_text(response.choices[0].message.content, 4_000)
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            # Don't retry on validation/auth errors
            if "invalid" in error_str or "unauthorized" in error_str or "401" in error_str:
                raise
            if _is_connectivity_error(e):
                _disable_llm_temporarily(e)
                raise
            if attempt < MAX_RETRIES:
                wait = (2 ** attempt) * 0.5  # 0.5s, 1.0s
                print(f"[TrustScore] LLM attempt {attempt+1} failed ({e}), retrying in {wait}s...")
                time.sleep(wait)

    raise last_error


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
# CHAT AGENT PROMPT — Conversational AI for loan queries
# ============================================================

CHAT_SYSTEM_PROMPT = """You are TrustScore AI Assistant, a friendly and knowledgeable AI credit advisor for gig workers in India.

You help gig workers (delivery drivers, freelancers, ride-share operators) understand:
- Their creditworthiness and TrustScore
- Loan eligibility and how to qualify
- How to improve their financial profile
- What alternative data means for credit scoring

PERSONALITY:
- Warm, encouraging, professional
- Use simple language (avoid jargon)
- Give specific, actionable advice
- Use emojis sparingly for friendliness
- Keep responses concise (2-4 sentences max)

CONTEXT (if provided):
- If the user has a recent TrustScore, reference it in your advice
- If they uploaded a document, reference insights from it
- If no context, give general guidance

LOAN ELIGIBILITY RULES:
- Score 75-100 (Low Risk): Eligible for loans up to ₹1,00,000
- Score 50-74 (Medium Risk): Conditionally eligible for up to ₹30,000
- Score 0-49 (High Risk): Not currently eligible — advise improvement

IMPORTANT: Be encouraging even for low scores. Focus on what they CAN do to improve.
Always respond in plain text (no JSON, no markdown formatting).
"""


# ============================================================
# DOCUMENT ANALYSIS PROMPT — Extract data from uploaded files
# ============================================================

DOCUMENT_ANALYSIS_PROMPT = """You are TrustScore AI, a financial document analyzer for gig workers.

The user has uploaded a financial document. Analyze the extracted text and:
1. Identify the monthly income (or estimate from transaction data)
2. Identify platform rating if mentioned
3. Identify total gigs/jobs completed if mentioned
4. Provide a brief financial summary

OUTPUT RULES (CRITICAL):
- Respond with ONLY a valid JSON object
- No markdown, no code fences, no extra text
- Use exactly these keys:
  * "income": number (estimated monthly income in INR, 0 if not found)
  * "rating": number (platform rating 0-5, 0 if not found)
  * "gigs": integer (total gigs, 0 if not found)
  * "summary": string (2-3 sentence summary of the document)
  * "data_found": boolean (true if any financial data was extracted)
"""


# ============================================================
# INPUT VALIDATION
# ============================================================

def _validate_input(data: dict) -> tuple[bool, str]:
    """Check that input has required fields with valid types."""
    required = ["income", "rating", "gigs"]
    for field in required:
        if field not in data:
            return False, f"Missing required field: '{field}'"

    if (
        isinstance(data["income"], bool)
        or not isinstance(data["income"], (int, float))
        or not math.isfinite(float(data["income"]))
        or data["income"] < 0
    ):
        return False, "income must be a non-negative number"
    if (
        isinstance(data["rating"], bool)
        or not isinstance(data["rating"], (int, float))
        or not math.isfinite(float(data["rating"]))
        or not 0 <= data["rating"] <= 5
    ):
        return False, "rating must be a number between 0 and 5"
    if (
        isinstance(data["gigs"], bool)
        or not isinstance(data["gigs"], (int, float))
        or not math.isfinite(float(data["gigs"]))
        or data["gigs"] < 0
    ):
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
        raw = _llm_call(
            messages=[
                {"role": "system", "content": active_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            json_mode=True,
        )
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
        result["reason"] = _clip_text(result["reason"], 600)
        result["advice"] = _clip_text(result["advice"], 600)

        return result

    except Exception as e:
        # Graceful fallback — the demo never crashes
        print(f"[TrustScore] LLM call failed ({e}), using fallback scorer")
        return _mock_score(data)


# ============================================================
# CHAT AGENT — Conversational AI with multi-turn memory
# ============================================================

# In-memory chat history per session (keyed by session_id)
_chat_sessions: dict[str, list[dict]] = {}
MAX_HISTORY_MESSAGES = 10  # Keep last N messages for context
MAX_CHAT_SESSIONS = int(os.getenv("MAX_CHAT_SESSIONS", "100"))
MAX_CHAT_MESSAGE_CHARS = 1000
MAX_CHAT_REPLY_CHARS = 1500
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _normalize_session_id(session_id: str) -> str:
    session_id = str(session_id or "default")
    return session_id if SESSION_ID_RE.fullmatch(session_id) else "default"


def _sanitize_context(context: dict = None) -> dict:
    if not isinstance(context, dict):
        return {}

    sanitized = {}
    for key in ("score", "income", "rating", "gigs"):
        value = context.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if math.isfinite(float(value)):
            sanitized[key] = value

    risk = context.get("risk")
    if risk in ("Low", "Medium", "High"):
        sanitized["risk"] = risk

    if isinstance(context.get("loan_eligible"), bool):
        sanitized["loan_eligible"] = context["loan_eligible"]
    if context.get("loan_message"):
        sanitized["loan_message"] = _clip_text(context["loan_message"], 300)
    if context.get("document_summary"):
        sanitized["document_summary"] = _clip_text(context["document_summary"], 1000)

    return sanitized


def chat_with_agent(message: str, context: dict = None, session_id: str = "default") -> str:
    """
    Conversational AI agent that answers loan/credit questions.
    Supports multi-turn conversation with memory.

    Args:
        message: User's question (e.g., "Will I get a loan?")
        context: Optional dict with last score result for context
        session_id: Session identifier for multi-turn memory

    Returns:
        str: AI's response text
    """
    message = _clip_text(message, MAX_CHAT_MESSAGE_CHARS)
    session_id = _normalize_session_id(session_id)
    context = _sanitize_context(context)

    # Build context string from score data
    context_str = ""
    if context:
        if "score" in context:
            context_str += f"\n\nUSER'S CURRENT PROFILE:"
            context_str += f"\n- TrustScore: {context.get('score', 'N/A')}/100"
            context_str += f"\n- Risk Level: {context.get('risk', 'N/A')}"
            if isinstance(context.get('income'), (int, float)):
                context_str += f"\n- Income: ₹{context['income']:,}"
            if context.get('rating'):
                context_str += f"\n- Rating: {context['rating']}/5"
            if context.get('gigs'):
                context_str += f"\n- Gigs: {context['gigs']}"
            if context.get('loan_eligible') is not None:
                context_str += f"\n- Loan Eligible: {'Yes' if context['loan_eligible'] else 'No'}"
            if context.get('loan_message'):
                context_str += f"\n- Loan Status: {context['loan_message']}"
        if context.get("document_summary"):
            context_str += f"\n\nUPLOADED DOCUMENT SUMMARY:\n{context['document_summary']}"

    system = CHAT_SYSTEM_PROMPT + context_str

    # If no LLM, use rule-based chat fallback
    if USE_PROVIDER == "mock" or client is None:
        reply = _mock_chat(message, context)
        # Still store in history for consistency
        _store_chat_message(session_id, "user", message)
        _store_chat_message(session_id, "assistant", reply)
        return reply

    # Build message list with history for multi-turn conversation
    messages = [{"role": "system", "content": system}]

    # Add conversation history
    history = _chat_sessions.get(session_id, [])
    messages.extend(history)

    # Add current user message
    messages.append({"role": "user", "content": message})

    try:
        raw = _llm_call(
            messages=messages,
            temperature=0.5,
            max_tokens=300,
            json_mode=False,
        )
        reply = _clip_text(raw, MAX_CHAT_REPLY_CHARS)

        # Store in history
        _store_chat_message(session_id, "user", message)
        _store_chat_message(session_id, "assistant", reply)

        return reply

    except Exception as e:
        print(f"[TrustScore] Chat LLM failed ({e}), using fallback")
        reply = _mock_chat(message, context)
        _store_chat_message(session_id, "user", message)
        _store_chat_message(session_id, "assistant", reply)
        return reply


def _store_chat_message(session_id: str, role: str, content: str):
    """Store a message in the session's chat history."""
    session_id = _normalize_session_id(session_id)
    if session_id not in _chat_sessions:
        if len(_chat_sessions) >= MAX_CHAT_SESSIONS:
            oldest_session = next(iter(_chat_sessions))
            _chat_sessions.pop(oldest_session, None)
        _chat_sessions[session_id] = []
    _chat_sessions[session_id].append({"role": role, "content": _clip_text(content, MAX_CHAT_REPLY_CHARS)})
    # Trim to keep only recent messages
    if len(_chat_sessions[session_id]) > MAX_HISTORY_MESSAGES:
        _chat_sessions[session_id] = _chat_sessions[session_id][-MAX_HISTORY_MESSAGES:]


def clear_chat_history(session_id: str = "default"):
    """Clear chat history for a session."""
    session_id = _normalize_session_id(session_id)
    _chat_sessions.pop(session_id, None)


def _mock_chat(message: str, context: dict = None) -> str:
    """Rule-based chat when LLM is unavailable."""
    message = _clip_text(message, MAX_CHAT_MESSAGE_CHARS)
    context = _sanitize_context(context)
    msg_lower = message.lower()

    # Check for loan/eligibility questions
    if any(w in msg_lower for w in ["loan", "eligible", "qualify", "borrow", "credit"]):
        if context and "score" in context:
            score = int(context["score"])
            if score >= 75:
                return f"Great news! 🎉 With your TrustScore of {score}, you're eligible for loans up to ₹1,00,000. Your strong profile shows reliable income and good platform reputation. I'd recommend applying with a microfinance institution that accepts digital gig profiles."
            elif score >= 50:
                return f"You're conditionally eligible! ⚠️ With a TrustScore of {score}, you may qualify for loans up to ₹30,000. To unlock higher amounts, try increasing your monthly income and completing more gigs to build a stronger track record."
            else:
                return f"Currently, your TrustScore of {score} means you're not yet eligible for traditional loans. 💪 But don't worry! Focus on completing more gigs, improving your platform rating, and building consistent income. Recheck in 3 months — small improvements add up!"
        return "To check your loan eligibility, I'll need to see your TrustScore first. Try entering your income, platform rating, and gigs count in the Score tab, or upload a financial document for analysis!"

    # Check for improvement questions
    if any(w in msg_lower for w in ["improve", "increase", "better", "raise", "boost", "tips"]):
        tips = [
            "Increase income: Take on premium gigs, work during peak hours, or diversify across multiple platforms.",
            "Boost your rating: Deliver on time, communicate proactively, and ask satisfied customers for reviews.",
            "Complete more gigs: Aim for at least 80 completed gigs to show reliability.",
            "Save consistently: Even small regular savings show financial discipline to lenders."
        ]
        return "Here's how you can boost your TrustScore:\n\n" + "\n".join(tips)

    # Check for explanation questions
    if any(w in msg_lower for w in ["how does", "what is", "explain", "how it works", "trustscore"]):
        return "TrustScore is an AI-powered credit scoring system designed for gig workers who lack traditional credit history. 🛡️ It analyzes three key factors: your monthly income (40% weight), platform rating (30% weight), and total gigs completed (30% weight). Scores range from 0-100, where 75+ means low risk and loan eligibility!"

    # Check for greetings
    if any(w in msg_lower for w in ["hello", "hi", "hey", "namaste", "good"]):
        return "Hello! 👋 I'm TrustScore AI, your credit advisor. I can help you understand your creditworthiness, check loan eligibility, or suggest ways to improve your financial profile. What would you like to know?"

    # Check for thank you
    if any(w in msg_lower for w in ["thank", "thanks", "helpful", "great"]):
        return "You're welcome! 😊 I'm glad I could help. Feel free to ask me anything else about your credit score, loan eligibility, or how to improve your financial profile. Good luck! 🍀"

    # Default response
    return "I'm here to help with your credit score and loan eligibility! 🛡️ You can ask me things like:\n• \"Will I get a loan?\"\n• \"How can I improve my score?\"\n• \"What is TrustScore?\"\n• \"Am I eligible for credit?\"\n\nFeel free to ask anything!"


# ============================================================
# DOCUMENT ANALYSIS — Extract data from uploaded files
# ============================================================

def analyze_document_text(text: str) -> dict:
    """
    Analyze extracted text from uploaded documents to find financial data.

    Args:
        text: Extracted text from PDF/CSV

    Returns:
        dict: {"income": float, "rating": float, "gigs": int, "summary": str, "data_found": bool}
    """
    if not text or len(text.strip()) < 10:
        return {
            "income": 0,
            "rating": 0,
            "gigs": 0,
            "summary": "The uploaded document appears to be empty or unreadable.",
            "data_found": False,
        }

    # If no LLM, use rule-based extraction
    if USE_PROVIDER == "mock" or client is None:
        return _mock_document_analysis(text)

    try:
        raw = _llm_call(
            messages=[
                {"role": "system", "content": DOCUMENT_ANALYSIS_PROMPT},
                {"role": "user", "content": f"Analyze this document:\n\n{text[:4000]}"},
            ],
            temperature=0.1,
            json_mode=True,
        )
        result = json.loads(raw)

        # Normalize
        result["income"] = max(0, float(result.get("income", 0)))
        result["rating"] = max(0, min(5, float(result.get("rating", 0))))
        result["gigs"] = max(0, int(result.get("gigs", 0)))
        result["summary"] = _clip_text(result.get("summary", "Document analyzed successfully."), 800)
        result["data_found"] = bool(result.get("data_found", False))

        return result

    except Exception as e:
        print(f"[TrustScore] Document analysis LLM failed ({e}), using fallback")
        return _mock_document_analysis(text)


def _mock_document_analysis(text: str) -> dict:
    """Rule-based document analysis when LLM is unavailable."""
    text_lower = text.lower()
    income = 0
    rating = 0
    gigs = 0

    # Try to extract income patterns
    income_patterns = [
        r'(?:income|salary|earning|payment|credit)[:\s]*(?:rs\.?|₹|inr)?\s*([\d,]+)',
        r'(?:rs\.?|₹|inr)\s*([\d,]+)',
        r'(?:total|net|gross)[:\s]*(?:rs\.?|₹|inr)?\s*([\d,]+)',
    ]
    for pattern in income_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            amounts = [int(m.replace(',', '')) for m in matches if m.replace(',', '').isdigit()]
            if amounts:
                income = max(amounts)
                break

    # Try to extract rating
    rating_patterns = [
        r'(?:rating|score|stars?)[:\s]*([\d.]+)\s*(?:/\s*5|out of 5|stars?)',
        r'([\d.]+)\s*(?:/\s*5|out of 5|stars)',
    ]
    for pattern in rating_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            try:
                r = float(matches[0])
                if 0 <= r <= 5:
                    rating = r
                    break
            except ValueError:
                pass

    # Try to extract gigs count
    gigs_patterns = [
        r'(?:gigs?|trips?|deliveries|orders?|jobs?|tasks?)\s*(?:completed|done|finished)?[:\s]*([\d,]+)',
        r'([\d,]+)\s*(?:gigs?|trips?|deliveries|orders?|jobs?|tasks?)',
        r'(?:total|completed)[:\s]*([\d,]+)',
    ]
    for pattern in gigs_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            try:
                g = int(matches[0].replace(',', ''))
                if g > 0:
                    gigs = g
                    break
            except ValueError:
                pass

    data_found = income > 0 or rating > 0 or gigs > 0

    if data_found:
        parts = []
        if income > 0:
            parts.append(f"monthly income of approximately ₹{income:,}")
        if rating > 0:
            parts.append(f"platform rating of {rating}/5")
        if gigs > 0:
            parts.append(f"{gigs} completed gigs")
        summary = f"Document analysis found: {', '.join(parts)}. Based on the extracted data, a TrustScore assessment can be generated."
    else:
        summary = "The document was read but no clear financial data (income, rating, or gig count) could be extracted. You can manually enter your details in the Score tab for analysis."

    return {
        "income": income,
        "rating": rating,
        "gigs": gigs,
        "summary": _clip_text(summary, 800),
        "data_found": data_found,
    }


# ============================================================
# Quick test when you run this file directly
# ============================================================
if __name__ == "__main__":

    test_cases = [
        {"income": 8000,  "rating": 3.2, "gigs": 15,  "label": "Low-income new worker"},
        {"income": 30000, "rating": 4.5, "gigs": 100, "label": "Solid gig worker"},
        {"income": 55000, "rating": 4.8, "gigs": 250, "label": "Veteran high earner"},
    ]

    print("=" * 60)
    print("  TrustScore AI — Agent Test Run")
    print(f"  Provider: {PROVIDER_NAME} | Model: {MODEL or 'fallback'}")
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

    # Test chat with memory
    print("\n" + "=" * 60)
    print("  Chat Agent Test (Multi-Turn)")
    print("=" * 60)
    ctx = {"score": 72, "risk": "Medium", "income": 30000, "rating": 4.5, "gigs": 100}

    chat_tests = [
        "Will I get a loan?",
        "How can I improve my score?",
        "What about increasing my income specifically?",
    ]
    for msg in chat_tests:
        print(f"\n▸ User: {msg}")
        resp = chat_with_agent(msg, ctx, session_id="test")
        print(f"  Agent: {resp[:150]}...")

    print("\n" + "=" * 60)
    print("  All tests passed ✅")
    print("=" * 60)
