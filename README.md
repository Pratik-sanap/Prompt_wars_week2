# 🗳️ ElectWise — AI-Powered Election Intelligence Platform

> **A production-grade, multi-agent AI system that makes election education radically transparent.**

![ElectWise Screenshot](screenshot_placeholder.png)

[![Deploy](https://img.shields.io/badge/Live%20Demo-Google%20Cloud%20Run-4285F4?logo=googlecloud)](https://electwise-1020411827743.us-central1.run.app)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-2.0%20Flash-EA4335?logo=google)](https://ai.google.dev)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions)](https://github.com/Pratik-sanap/Prompt_wars_week2/actions)

---

## 🧩 Problem Statement

Millions of first-time voters are confused about the election process. Existing tools offer static FAQs or simple chatbots — they can't explain *why* an answer is correct, *how confident* they are, or *which verified sources* they used. Misinformation thrives in this vacuum.

**ElectWise solves this** by running every question through a 4-agent AI reasoning pipeline, backed by a RAG knowledge base, that shows its work transparently — including a confidence score, reasoning trace, and cited sources.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER BROWSER                           │
│  Timeline │ Flashcards │ Quiz │ 🔬 Deep Dive │ 💬 Chat     │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTP/REST
┌───────────────────▼─────────────────────────────────────────┐
│                   FastAPI Backend (v3.0)                     │
│  /api/agent  /api/chat  /api/flashcards  /api/quiz          │
│  /api/timeline  /api/search  /health                        │
└──────┬────────────────────────────────┬──────────────────────┘
       │                                │
┌──────▼──────────┐           ┌─────────▼──────────────────────┐
│   AI Layer      │           │   Knowledge Base (RAG)          │
│                 │           │                                 │
│ 1. ResearchAgent│◄──────────│  TF-IDF Semantic Search        │
│    (RAG lookup) │           │  14 curated election docs      │
│                 │           │  Topic: Reg, Voting, EC, Law   │
│ 2. ReasoningAgent           └─────────────────────────────────┘
│    (step-by-step│
│     synthesis)  │           ┌─────────────────────────────────┐
│                 │           │   Google Gemini 2.0 Flash API   │
│ 3. CriticAgent  ├──────────►│   4 calls per Deep Dive query  │
│    (confidence  │           │   1 call per Chat message      │
│     scoring)    │           └─────────────────────────────────┘
│                 │
│ 4. PersonaAgent │
│    (user-level  │
│     adaptation) │
└─────────────────┘
```

---

## ⚡ What Makes This Different from VotePath-AI

| Feature | VotePath-AI | **ElectWise** |
|---|---|---|
| AI Architecture | Single prompt-response | **4-agent reasoning pipeline** |
| Knowledge grounding | None | **RAG with 14 curated docs** |
| Transparency | ❌ Black box | **✅ Full reasoning trace** |
| Confidence scoring | ❌ | **✅ CriticAgent evaluates every answer** |
| Source citations | ❌ | **✅ RAG sources shown with relevance %** |
| Personalization | ❌ | **✅ Beginner / Intermediate / Expert mode** |
| Explainable AI | ❌ | **✅ Step-by-step reasoning shown to user** |
| Backend | Static/Vercel | **FastAPI + Google Cloud Run** |
| CI/CD | ❌ | **✅ GitHub Actions → Cloud Run** |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, Vanilla CSS (Glassmorphism), JavaScript ES2022 |
| **Backend** | Python 3.11, FastAPI 0.110, Uvicorn |
| **AI Models** | Google Gemini 2.0 Flash (via `google-genai` SDK) |
| **RAG Engine** | Custom TF-IDF semantic retriever (zero GPU dependency) |
| **Agent Framework** | Custom multi-agent orchestrator (`ai_layer/agents.py`) |
| **Deployment** | Google Cloud Run (Dockerized) |
| **CI/CD** | GitHub Actions (test → build → deploy) |

---

## 📁 Project Structure

```
electwise/
├── main.py                    # FastAPI app — all API routes
├── requirements.txt
├── Dockerfile
├── .env                       # GEMINI_API_KEY (not committed)
│
├── ai_layer/
│   ├── __init__.py
│   ├── knowledge_base.py      # RAG corpus + TF-IDF retriever (14 docs)
│   └── agents.py              # 4-agent pipeline orchestrator
│
├── static/
│   ├── index.html             # Single-page app shell
│   ├── style.css              # Premium glassmorphic UI (~1300 lines)
│   └── app.js                 # All frontend logic (~480 lines)
│
└── .github/
    └── workflows/
        └── deploy.yml         # CI/CD: test → Docker → Cloud Run
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.11+
- Gemini API Key — [Get one free](https://aistudio.google.com/apikey)

```bash
# 1. Clone
git clone https://github.com/Pratik-sanap/Prompt_wars_week2.git
cd Prompt_wars_week2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API key
echo "GEMINI_API_KEY=your_key_here" > .env

# 4. Run
python -m uvicorn main:app --reload --port 8000

# 5. Open
# http://localhost:8000
```

---

## 🔬 How the Multi-Agent Pipeline Works

When you click **Deep Dive** and submit a question, four agents run in sequence:

```
Question: "How does the Electoral College work?"

[ResearchAgent]   → Searches knowledge base via TF-IDF
                    Returns: top 3 matching docs + relevance scores

[ReasoningAgent]  → Synthesizes a step-by-step answer from retrieved context
                    Returns: reasoning_steps[], key_facts[], core_answer

[CriticAgent]     → Evaluates accuracy, assigns confidence 0.0–1.0
                    Returns: confidence_score: 0.92, label: "High"

[PersonaAgent]    → Adapts tone for user level (Beginner/Intermediate/Expert)
                    Returns: final markdown answer shown to user
```

The UI shows every layer: answer, confidence meter, RAG sources with relevance %, and the reasoning trace.

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server status + feature list |
| `POST` | `/api/agent` | 🔬 Full 4-agent RAG pipeline |
| `POST` | `/api/chat` | 💬 Conversational AI with history |
| `POST` | `/api/flashcards` | 🃏 AI-generated flashcards |
| `POST` | `/api/quiz` | 🧠 AI-generated quiz |
| `GET` | `/api/timeline` | 📋 Election steps data |
| `POST` | `/api/search` | 🔍 RAG knowledge base search |

Interactive API docs: [`/docs`](https://electwise-1020411827743.us-central1.run.app/docs)

---

## ☁️ Deployment (Google Cloud Run)

```bash
# One-command deploy from Cloud Shell
gcloud run deploy electwise \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key
```

**CI/CD via GitHub Actions:**  
Every push to `main` automatically:
1. Runs import + syntax tests
2. Builds and smoke-tests the Docker image
3. Deploys to Google Cloud Run

---

## 💡 Future Scope

1. **Pinecone/ChromaDB** — Replace TF-IDF with dense vector embeddings for higher RAG accuracy
2. **Multilingual support** — Translate UI + AI responses into Spanish, Hindi, French
3. **State-specific timelines** — Integrate Google Civic Information API for personalized deadlines
4. **Feedback loop** — Users rate answers; low-rated responses trigger agent re-runs
5. **Voice interface** — Web Speech API for accessibility

---

## 🏅 Hackathon: Prompt Wars Week 2

- **Vertical:** Civic Tech / Education
- **Challenge:** Build an AI-powered civic tool using Google Gemini
- **Live Demo:** [electwise-1020411827743.us-central1.run.app](https://electwise-1020411827743.us-central1.run.app)
- **Repo:** [github.com/Pratik-sanap/Prompt_wars_week2](https://github.com/Pratik-sanap/Prompt_wars_week2)

---

*Built with ❤️ using Google Gemini AI · FastAPI · Google Cloud Run*
