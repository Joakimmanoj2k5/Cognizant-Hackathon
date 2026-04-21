# 🛡️ TrustScore AI — Team RiskWise

> **AI-powered credit scoring for gig workers**
> Cognizant Technoverse 2026 — Agent Builder Challenge

---

## 🎯 Problem Statement

Millions of gig workers (delivery drivers, freelancers, ride-share operators) lack traditional credit history, making them **invisible to banks**. TrustScore bridges this gap by analyzing **alternative data** — platform ratings, income patterns, and work volume — to generate a **creditworthiness score (0-100)** using AI.

## 🧠 How It Works

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  User Input  │ ──▶ │  AI Agent    │ ──▶ │  TrustScore +    │
│  (income,    │     │  (LLM +      │     │  Risk Level +    │
│   rating,    │     │   fallback)  │     │  Advice + Loan   │
│   gigs)      │     │              │     │  Eligibility     │
└──────────────┘     └──────────────┘     └──────────────────┘
       │                    ▲                      │
       ▼                    │                      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  File Upload │     │  Chat Agent  │     │  Document        │
│  (PDF/CSV)   │ ──▶ │  "Will I get │ ◀── │  Analysis +      │
│              │     │   a loan?"   │     │  Auto-Scoring    │
└──────────────┘     └──────────────┘     └──────────────────┘
```

### Scoring Framework
| Factor            | Weight | Thresholds                                    |
|-------------------|--------|-----------------------------------------------|
| Monthly Income    | 40%    | <₹15K weak → ₹15-30K moderate → ₹30-60K strong → >₹60K excellent |
| Platform Rating   | 30%    | <3.5 poor → 3.5-4.2 okay → 4.2-4.7 good → >4.7 excellent |
| Gigs Completed    | 30%    | <20 new → 20-80 building → 80-200 established → >200 veteran |

### Risk Levels & Loan Eligibility
| Score   | Risk   | Loan Eligibility                              |
|---------|--------|-----------------------------------------------|
| 75-100  | Low    | ✅ Eligible up to ₹1,00,000                   |
| 50-74   | Medium | ⚠️ Conditionally eligible up to ₹30,000       |
| 0-49    | High   | ❌ Not eligible — retry in 3 months            |

## ✨ Key Features

### 📊 AI Credit Scoring
- Slider-based input for income, rating, and gigs
- Animated score gauge with color-coded risk levels
- Detailed AI reasoning and actionable improvement advice

### 📄 Document Upload & Analysis
- **Drag-and-drop** file upload (PDF, CSV, TXT)
- AI-powered document text extraction and analysis
- Automatic financial data detection (income, rating, gigs)
- Auto-generates TrustScore from uploaded documents

### 💬 AI Chat Agent (Multi-Turn)
- Conversational AI credit advisor with **multi-turn memory**
- Context-aware responses based on your last score
- Quick suggestion chips: "Will I get a loan?", "How to improve?"
- Typing indicators and smooth chat experience
- Remembers conversation history for follow-up questions

### 📋 Batch Analysis
- Score multiple worker profiles concurrently (up to 50)
- Sample data loading for quick demos
- Tabular results with risk and loan badges

### 🔧 Reliability
- **Retry with exponential backoff** — resilient to API rate limits
- **Request timeouts** — demo never hangs (12s max per call)
- **Rule-based fallback** — works even without internet
- **Graceful error handling** — never crashes during demo

### 🎨 Premium UI
- Dark glassmorphism design with animated particle background
- Tabbed navigation with glowing indicator
- Mobile-first responsive layout
- Micro-animations and smooth transitions throughout
- Model info badge showing active LLM

## 📂 Project Structure

```
trustscore-agent/
├── agent.py           # 🧠 AI Core — scoring + chat + document analysis + retry
├── main.py            # ⚙️ Backend Wrapper — generate_score + analyze_document + chat
├── app.py             # 🌐 Server (FastAPI) — UI + API + file upload + batch
├── test_runner.py     # 🧪 Test Suite — 9 automated test groups
├── test_data.json     # 📊 Test cases with expected outcomes
├── input_samples.json # 📋 Sample inputs for reference
├── requirements.txt   # 📦 Python dependencies
├── .env.example       # 🔑 Environment variable template
├── .gitignore         # Git ignore rules
├── README.md          # 📖 This file
└── static/
    ├── index.html     # 🎨 Web UI — tabbed interface
    ├── styles.css     # 💅 Premium design system
    └── app.js         # ⚡ Frontend — tabs, upload, chat, particles
```

## 🚀 Run Locally

### Prerequisites
- Python 3.10 or newer
- `pip3`

### 1. Install dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Configure environment variables
```bash
cp .env.example .env
```

Edit `.env` and set `USE_PROVIDER` to one of `groq`, `openai`, or `mock`.

If you want LLM-backed scoring, add your provider key in `.env`. If you do not want to configure an API key, set:
```bash
USE_PROVIDER=mock
```

The app defaults to `mock` in `.env.example` so uploaded document text is not sent to an external LLM unless you explicitly opt in. The app also falls back automatically when no key is available or the provider is temporarily unreachable, so the demo still runs.

For deployment, set:
```bash
TRUSTSCORE_ALLOWED_ORIGINS=https://your-frontend.example
```

The API ships with restricted CORS, security headers, upload size/type checks, bounded chat memory, and pinned runtime dependencies.

### 3. Run the tests
```bash
python3 test_runner.py
```

### 4. Start the server
```bash
python3 app.py
```

Open:
```text
http://localhost:8000
```

## 🔧 API Endpoints

| Method | Endpoint         | Description                        |
|--------|------------------|------------------------------------|
| GET    | `/`              | Web UI                             |
| POST   | `/api/score`     | Score a single profile             |
| POST   | `/api/batch`     | Score multiple profiles (≤50)      |
| POST   | `/api/upload`    | Upload PDF/CSV/TXT for analysis    |
| POST   | `/api/chat`      | Chat with AI credit advisor        |
| POST   | `/api/chat/clear`| Clear chat session history         |
| GET    | `/api/info`      | Get AI model configuration         |
| GET    | `/api/test-data` | Get sample test data               |
| GET    | `/health`        | Health check + feature list        |

### Quick API Test
```bash
# Score a worker
curl -X POST http://localhost:8000/api/score \
  -H "Content-Type: application/json" \
  -d '{"income": 35000, "rating": 4.5, "gigs": 120}'

# Chat with the agent
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Will I get a loan?", "context": {"score": 80, "risk": "Low"}}'

# Upload a document
curl -X POST http://localhost:8000/api/upload \
  -F "file=@your_document.pdf"

# Check model info
curl http://localhost:8000/api/info
```

## 🎬 Demo Walkthrough

For judges — here's the recommended demo flow:

1. **Score Tab** → Adjust sliders → Click "Analyze" → See animated gauge + risk + loan eligibility
2. **Upload Tab** → Drag a gig worker PDF → AI extracts data → Auto-generates score
3. **Chat Tab** → Ask "Will I get a loan?" → Follow up with "How can I improve?" → Note multi-turn memory
4. **Batch Tab** → Load sample data → Score All → See all 10 profiles scored concurrently
5. **Health Check** → `http://localhost:8000/health` → Show LLM provider info

## ✅ Verification

9/9 automated test groups pass:

```
✅ Output Format Validation
✅ Test Data Scoring (10 profiles + timing)
✅ Input Validation (5 edge cases)
✅ Wrapper Function (loan eligibility)
✅ validate_input() Function
✅ Edge Cases (zeros, max values, floats)
✅ Prompt Versions (v1, v2, v3)
✅ Chat Memory (multi-turn conversation)
✅ Model Info (provider, model, features)
```

## 🧩 Architecture

### AI Core (`agent.py`)
- **3 Prompt Versions**: Basic → Reasoning → Suggestions
- **LLM Integration**: Groq (Llama 3.3 70B) or OpenAI (GPT-4o-mini)
- **Retry + Backoff**: Resilient to rate limits and transient failures
- **Request Timeout**: 12s max — demo never hangs
- **Chat Agent**: Multi-turn conversational AI with session memory
- **Document Analyzer**: Extracts financial data from uploaded files
- **Fallback Scorer**: Rule-based engine — demo never crashes
- **Output**: Standardized `{score, risk, reason, advice}`

### Backend Wrapper (`main.py`)
- `generate_score()` — wraps AI core + adds loan eligibility
- `analyze_document()` — document text → data extraction → auto-scoring
- `chat_response()` — wraps chat agent with context + session passing
- `validate_input()` — checks missing fields, wrong types, range errors

### Server (`app.py`)
- **FastAPI** with Pydantic validation
- **Concurrent batch scoring** using `asyncio.gather`
- **File upload** with streaming + size validation
- **Chat sessions** with multi-turn memory
- **Model info API** for UI display

### Web UI (`static/`)
- Dark glassmorphism design with particle animations
- **4 tabs**: Score, Upload, Chat Agent, Batch
- File drag-and-drop with progress indicators
- AI chat with typing animation, suggestion chips, and session memory
- Animated score gauge with color-coded risk
- Model info badge showing active LLM
- Fully responsive (mobile, tablet, desktop)

## 👥 Team RiskWise

| Member | Role                     | Deliverable          |
|--------|--------------------------|----------------------|
| M3     | 🧠 AI Core Lead          | `agent.py`           |
| M2     | ⚙️ Backend Builder        | `main.py`            |
| M1     | 🎨 UI / Input Simulation | `static/`, `input_samples.json` |
| M4     | 🧪 Testing + GitHub       | `test_runner.py`, `test_data.json` |

## 📜 License

Built for Cognizant Technoverse 2026 — Agent Builder Challenge.
