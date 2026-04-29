"""
ElectWise — Election Guide App v3.0
FastAPI Backend · Google Gemini AI · Multi-Agent RAG Pipeline
"""
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s — %(message)s')
logger = logging.getLogger("electwise")
import os
import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from ai_layer.knowledge_base import kb
from ai_layer.agents import MultiAgentPipeline

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(title="ElectWise API", version="3.0.0", description="Multi-agent election guide powered by Google Gemini AI and RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Pydantic Models ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []
    api_key: Optional[str] = None

class FlashcardRequest(BaseModel):
    topic: Optional[str] = "general election process"
    count: Optional[int] = 6
    api_key: Optional[str] = None

class QuizRequest(BaseModel):
    topic: Optional[str] = "voting process"
    api_key: Optional[str] = None

class AgentRequest(BaseModel):
    question: str
    experience_level: Optional[str] = "beginner"  # beginner | intermediate | expert
    api_key: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3

# ── System Prompts ────────────────────────────────────────────────────────────
CHAT_SYSTEM_PROMPT = """You are ElectWise, a friendly, knowledgeable, and non-partisan election guide assistant.
Your mission is to help first-time voters and curious citizens understand the election process clearly and confidently.

Guidelines:
- Be friendly, encouraging, and approachable — never condescending
- Keep answers concise but complete (150–250 words max)
- Use simple language, avoid legal jargon
- Use emojis sparingly but effectively
- Structure with **bold** for key terms and numbered lists for steps
- Always recommend official sources like vote.gov for state-specific details
- Never take political sides or favor any party/candidate
- If asked about non-election topics, gently redirect back to elections

Answer directly and clearly. Use markdown formatting (bold, lists).
"""

FLASHCARD_SYSTEM_PROMPT = """You are an election education expert creating flashcard content.
Generate {count} flashcards about "{topic}" for first-time voters.

Return ONLY a valid JSON array (no markdown, no code blocks, no extra text):
[
  {{
    "id": 1,
    "category": "Category Name",
    "question": "Clear, specific question",
    "answer": "Concise answer in 2-3 sentences.",
    "emoji": "relevant emoji",
    "difficulty": "beginner",
    "fact": "One surprising related fact"
  }}
]

Use these categories: Registration, Voting Process, Ballot Types, Vote Counting, Electoral College, Election Officials, Results & Certification
Vary difficulty: beginner, intermediate, advanced. Make questions practical for real voters."""

QUIZ_SYSTEM_PROMPT = """Create a 5-question multiple choice quiz about "{topic}" for first-time voters.

Return ONLY a valid JSON array (no markdown, no code blocks, no extra text):
[
  {{
    "id": 1,
    "question": "Question text?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Why this answer is correct in 1-2 sentences.",
    "emoji": "📋"
  }}
]

The "correct" field is the 0-based index of the correct option. Make it educational and cover varied election topics."""

# ── Helper ────────────────────────────────────────────────────────────────────
def get_client(api_key: Optional[str] = None):
    key = api_key or GEMINI_API_KEY
    if not key:
        raise HTTPException(
            status_code=401,
            detail="No API key provided. Please enter your Gemini API key in the app settings."
        )
    return genai.Client(api_key=key)

def safe_parse_json(text: str):
    """Try to parse JSON from model output, stripping markdown fences if present."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    text = text.strip()
    return json.loads(text)

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "3.0.0",
        "gemini_configured": bool(GEMINI_API_KEY),
        "knowledge_base_docs": len(kb.docs),
        "features": ["multi-agent-rag", "flashcards", "quiz", "timeline", "semantic-search"]
    }

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Conversational AI endpoint with multi-turn history support."""
    try:
        client = get_client(req.api_key)

        history_text = ""
        if req.history:
            for h in req.history[-8:]:
                role = "User" if h.get("role") == "user" else "ElectWise"
                history_text += f"\n{role}: {h.get('content', '')}"

        prompt = f"""{CHAT_SYSTEM_PROMPT}

Conversation so far:{history_text}

User: {req.message}
ElectWise:"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        answer = response.text.strip()
        return {"reply": answer, "status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")


@app.post("/api/flashcards")
async def generate_flashcards(req: FlashcardRequest):
    """Generate AI-powered flashcards on an election topic."""
    try:
        client = get_client(req.api_key)
        prompt = FLASHCARD_SYSTEM_PROMPT.format(count=req.count, topic=req.topic)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        cards = safe_parse_json(response.text)
        return {"flashcards": cards, "topic": req.topic, "status": "ok"}
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse flashcard data from AI response.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")


@app.post("/api/quiz")
async def generate_quiz(req: QuizRequest):
    """Generate a multiple-choice quiz on a given election topic."""
    try:
        client = get_client(req.api_key)
        prompt = QUIZ_SYSTEM_PROMPT.format(topic=req.topic)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        questions = safe_parse_json(response.text)
        return {"questions": questions, "topic": req.topic, "status": "ok"}
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse quiz data from AI response.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")


@app.get("/api/timeline")
async def get_timeline():
    """Return the static election timeline data."""
    timeline = [
        {
            "id": 1, "icon": "✅", "phase": "Pre-Election",
            "title": "Check Your Eligibility",
            "subtitle": "Are you eligible to vote?",
            "color": "#10b981",
            "detail": "To vote in the US you must be: (1) a US citizen, (2) at least 18 by Election Day, and (3) a resident of the state where you register. Some states allow 17-year-olds to vote in primaries if they'll be 18 by the general election. Felony conviction rules vary widely by state.",
            "tips": ["Check your state's specific rules at vote.gov", "17-year-olds may vote in primaries in some states"],
            "deadline": "Ongoing"
        },
        {
            "id": 2, "icon": "📝", "phase": "Pre-Election",
            "title": "Register to Vote",
            "subtitle": "Sign up before the deadline",
            "color": "#3b82f6",
            "detail": "Register online at vote.gov, by mail, or in person at your county election office or DMV. Deadlines vary by state — typically 15–30 days before the election. Some states allow same-day registration. You'll need your address, state ID or last 4 digits of your SSN.",
            "tips": ["Deadline is typically 15-30 days before election", "Some states offer same-day registration"],
            "deadline": "15–30 days before election"
        },
        {
            "id": 3, "icon": "📍", "phase": "Pre-Election",
            "title": "Find Your Polling Place",
            "subtitle": "Know exactly where to go",
            "color": "#8b5cf6",
            "detail": "After registering, you're assigned a polling place based on your address. Use vote.gov or your state's election website to find it. Polling hours are typically 6 AM–8 PM on Election Day. If you've moved since your last registration, update your address!",
            "tips": ["Confirm your polling place a week before election day", "Bring your polling place address with you"],
            "deadline": "Before Election Day"
        },
        {
            "id": 4, "icon": "📬", "phase": "Pre-Election",
            "title": "Choose How to Vote",
            "subtitle": "In-person, early, or by mail",
            "color": "#f59e0b",
            "detail": "You have 3 options: (1) Vote in person on Election Day at your assigned polling place, (2) Early voting — many states open polls 1–2 weeks early, (3) Request an absentee or mail-in ballot from your county clerk. Apply for mail-in ballots early — deadlines vary by state.",
            "tips": ["Request mail-in ballots early — deadlines vary", "Early voting often means shorter lines"],
            "deadline": "Varies by method"
        },
        {
            "id": 5, "icon": "🗳️", "phase": "Election Day",
            "title": "Cast Your Vote",
            "subtitle": "Election Day — make it count!",
            "color": "#ef4444",
            "detail": "Bring a valid photo ID (requirements vary by state — some accept multiple forms). A poll worker verifies your registration. You'll receive a ballot, mark your choices privately in a voting booth, then submit it. If you make a mistake, ask for a new ballot (a 'provisional' ballot if needed). The process takes about 5–15 minutes.",
            "tips": ["Bring valid ID — requirements vary by state", "If the line is long, stay! You have the right to vote"],
            "deadline": "Election Day"
        },
        {
            "id": 6, "icon": "🔢", "phase": "Post-Election",
            "title": "Votes Are Counted",
            "subtitle": "After the polls close",
            "color": "#06b6d4",
            "detail": "After polls close, ballots are counted by trained election officials using optical scanners and hand counts. Mail-in and absentee ballots may take additional days to process. A random sample is always hand-audited to verify machine accuracy. This process is transparent and observers from both parties are present.",
            "tips": ["Mail-in ballots may take days — this is normal", "Results on election night are unofficial preliminary counts"],
            "deadline": "Days after election"
        },
        {
            "id": 7, "icon": "📋", "phase": "Post-Election",
            "title": "Canvass & Certification",
            "subtitle": "Official results verified",
            "color": "#f59e0b",
            "detail": "Canvassing is the official process of verifying every ballot was properly counted. Election officials reconcile voter rolls with ballots cast, review provisional ballots, and finalize counts. This takes days to weeks. Both parties have legal observers. Results are then certified by state officials — this is the official, legal outcome.",
            "tips": ["Certification timelines vary by state (days to weeks)", "Recounts can be requested if margin is close enough"],
            "deadline": "Days to weeks after election"
        },
        {
            "id": 8, "icon": "🏛️", "phase": "Post-Election",
            "title": "Electoral College (President)",
            "subtitle": "For presidential elections only",
            "color": "#8b5cf6",
            "detail": "For presidential elections: states appoint Electors equal to their Congressional seats (538 total). Most states are winner-take-all. Electors meet in their state capitals in December to cast official votes. Congress counts Electoral votes in January. 270 Electoral votes needed to win the presidency.",
            "tips": ["270 Electoral votes needed to win", "Congress certifies Electoral votes in early January"],
            "deadline": "December–January"
        },
        {
            "id": 9, "icon": "🏆", "phase": "Post-Election",
            "title": "Inauguration / Taking Office",
            "subtitle": "The winner is sworn in",
            "color": "#10b981",
            "detail": "Presidential inaugurations occur on January 20th. For other offices, winners are sworn in according to state or local law — often in January as well. The peaceful transfer of power is a cornerstone of democracy. Winners begin serving their elected terms immediately after being sworn in.",
            "tips": ["Presidential inauguration is January 20th", "Local officials are sworn in per state/local law"],
            "deadline": "January 20th (President)"
        }
    ]
    return {"timeline": timeline, "status": "ok"}


@app.post("/api/agent")
async def agent_answer(req: AgentRequest):
    """
    Multi-agent RAG pipeline endpoint.
    Runs: ResearchAgent → ReasoningAgent → CriticAgent → PersonaAgent
    Returns full reasoning trace, confidence score, and RAG sources.
    """
    try:
        client = get_client(req.api_key)
        logger.info(f"Agent pipeline triggered: '{req.question[:60]}' [{req.experience_level}]")
        pipeline = MultiAgentPipeline(client=client, model="gemini-2.5-flash")
        result = pipeline.run(
            question=req.question,
            experience_level=req.experience_level or "beginner"
        )
        logger.info(f"Pipeline complete — confidence: {result['confidence_score']}")
        return {"status": "ok", **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent pipeline error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {str(e)}")


@app.post("/api/search")
async def semantic_search(req: SearchRequest):
    """RAG knowledge base semantic search endpoint."""
    try:
        results = kb.retrieve(req.query, top_k=req.top_k)
        return {
            "status": "ok",
            "query": req.query,
            "results": [
                {"title": d["title"], "category": d["category"],
                 "content": d["content"][:300] + "...",
                 "relevance_score": s}
                for d, s in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
