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

## 📂 Project Structure

```
trustscore-agent/
├── agent.py           # 🧠 AI Core (M3) — scoring logic, 3 prompt versions
├── main.py            # ⚙️ Backend Wrapper (M2) — generate_score() + validation
├── app.py             # 🌐 Server (FastAPI) — serves UI + API endpoints
├── test_runner.py     # 🧪 Test Suite (M4) — automated validation
├── test_data.json     # 📊 Test cases with expected outcomes
├── input_samples.json # 📋 Sample inputs for UI/testing reference
├── requirements.txt   # 📦 Python dependencies
├── .env.example       # 🔑 Environment variable template
├── .gitignore         # Git ignore rules
├── README.md          # 📖 This file
└── static/
    ├── index.html     # 🎨 Web UI (M1)
    ├── styles.css     # 💅 Design system
    └── app.js         # ⚡ Frontend logic
```

## 🚀 Run Locally

### Prerequisites
- Python 3.9 or newer
- `pip`

### 1. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows, use:
```bash
venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
```

Edit `.env` and set `USE_PROVIDER` to one of `groq`, `openai`, or `mock`.

If you want LLM-backed scoring, add your provider key in `.env`. If you do not want to configure an API key, set:
```bash
USE_PROVIDER=mock
```

The app also falls back automatically when no key is available, so the demo still runs.

### 4. Run the tests
```bash
python3 test_runner.py
```

### 5. Start the server
```bash
python3 app.py
```

Open:
```text
http://localhost:8000
```

### 6. Use the API directly
```bash
curl -X POST http://localhost:8000/api/score \
  -H "Content-Type: application/json" \
  -d '{"income": 35000, "rating": 4.5, "gigs": 120}'
```

### 7. Use it as a Python function
```python
from agent import get_ai_score

result = get_ai_score({"income": 30000, "rating": 4.5, "gigs": 100})
print(result)
```

## 🔧 API Endpoints

| Method | Endpoint        | Description                  |
|--------|-----------------|------------------------------|
| GET    | `/`             | Web UI                       |
| POST   | `/api/score`    | Score a single profile       |
| POST   | `/api/batch`    | Score multiple profiles (≤50)|
| GET    | `/api/test-data`| Get sample test data         |
| GET    | `/health`       | Health check                 |

## ✅ Verification

The repository includes an automated test runner. A successful local run should show all 7 test groups passing:

```bash
python3 test_runner.py
```

If the server is already running, you can also verify it with:

```bash
curl -s http://localhost:8000/health
```

## 🧩 Architecture

### AI Core (`agent.py`)
- **3 Prompt Versions**: Basic → Reasoning → Suggestions
- **LLM Integration**: Groq (Llama 3.3 70B) or OpenAI (GPT-4o-mini)
- **Fallback Scorer**: Rule-based engine — demo never crashes
- **Output**: Standardized `{score, risk, reason, advice}`

### Backend Wrapper (`main.py`)
- `generate_score()` — wraps AI core + adds loan eligibility
- `validate_input()` — checks missing fields, wrong types, range errors
- Clean import: `from main import generate_score`

### Web UI (`static/`)
- Dark glassmorphism design
- Animated score gauge with color-coded risk
- Batch analysis with sample data
- Analysis history with localStorage
- Fully responsive

## 👥 Team RiskWise

| Member | Role                    | Deliverable        |
|--------|-------------------------|--------------------|
| M3     | 🧠 AI Core Lead         | `agent.py`         |
| M2     | ⚙️ Backend Builder       | `main.py`          |
| M1     | 🎨 UI / Input Simulation | `static/`, `input_samples.json` |
| M4     | 🧪 Testing + GitHub      | `test_runner.py`, `test_data.json` |

## 📜 License

Built for Cognizant Technoverse 2026 — Agent Builder Challenge.