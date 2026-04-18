# TrustScore Agent — Team RiskWise

AI-based credit scoring for gig workers. Converts income + rating + gig count
into a TrustScore (0-100) with risk level and reasoning.

## Setup
1. `python -m venv venv && source venv/bin/activate` (Mac) or `venv\Scripts\activate` (Win)
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your API key
4. `python agent.py`

## Usage
```python
from agent import get_ai_score
result = get_ai_score({"income": 30000, "rating": 4.5, "gigs": 100})
```