"""
ai_layer/agents.py
Multi-agent reasoning pipeline for ElectWise.

Agents:
  1. ResearchAgent   — retrieves relevant knowledge from the RAG knowledge base
  2. ReasoningAgent  — synthesizes retrieved context into a structured answer
  3. CriticAgent     — evaluates the answer quality and assigns confidence score
  4. PersonaAgent    — adapts the final answer to the user's detected experience level
"""
from __future__ import annotations
import re
import json
import time
from typing import Optional
from ai_layer.knowledge_base import kb


# ── Prompt Templates ──────────────────────────────────────────────────────────

RESEARCH_PROMPT = """You are the ResearchAgent in a multi-agent election guide system.

Your job: Identify exactly what the user is asking about and extract the 2-3 most precise search keywords to retrieve relevant knowledge.

User question: {question}

Retrieved knowledge base context:
{context}

Return a JSON object ONLY (no markdown, no explanation):
{{
  "topic": "brief topic label",
  "keywords": ["keyword1", "keyword2"],
  "relevant_sections": ["title of most relevant section"],
  "question_type": "factual|procedural|historical|legal|comparative"
}}"""

REASONING_PROMPT = """You are the ReasoningAgent in a multi-agent election guide system.

Your job: Given verified knowledge base context, produce a clear, accurate, step-by-step answer to the user's question. You must reason through the answer explicitly.

User question: {question}
Question type: {question_type}
Verified knowledge context:
{context}

Think step by step. Return a JSON object ONLY:
{{
  "reasoning_steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "core_answer": "The direct answer in 2-3 sentences",
  "key_facts": ["fact1", "fact2", "fact3"],
  "official_resource": "vote.gov or specific URL if applicable",
  "caveats": "Any important state-by-state variation or limitation"
}}"""

CRITIC_PROMPT = """You are the CriticAgent in a multi-agent election guide system.

Your job: Evaluate the ReasoningAgent's answer for accuracy, completeness, and clarity. Assign a confidence score.

User question: {question}
ReasoningAgent answer: {reasoning}
Knowledge context used: {context}

Return a JSON object ONLY:
{{
  "confidence_score": 0.0,
  "confidence_label": "High|Medium|Low",
  "accuracy_check": "brief assessment of factual accuracy",
  "missing_info": "anything important not addressed, or null",
  "approved": true,
  "improvement": "one specific improvement suggestion or null"
}}

Confidence scoring: 0.9+ = well-supported by knowledge base, 0.7-0.89 = partially supported, below 0.7 = limited support."""

PERSONA_PROMPT = """You are the PersonaAgent in a multi-agent election guide system.

Your job: Deliver the final answer to the user in a warm, clear, non-partisan tone. Adapt the complexity based on the user's experience level.

User question: {question}
User experience level: {experience_level}
Approved answer from ReasoningAgent:
- Core answer: {core_answer}
- Key facts: {key_facts}
- Reasoning steps: {reasoning_steps}
- Caveats: {caveats}
- Official resource: {official_resource}
Critic confidence: {confidence_label} ({confidence_score})

Write the final response for the user. Use markdown formatting (bold key terms, numbered lists for steps).
Keep it under 250 words. End with the official resource link.
Do NOT include JSON in your response — write natural, helpful prose."""


# ── Multi-Agent Pipeline ──────────────────────────────────────────────────────

class MultiAgentPipeline:
    """Orchestrates 4 specialized agents for election Q&A."""

    def __init__(self, client, model: str = "gemini-1.5-flash"):
        self.client = client
        self.model = model

    def _call(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text.strip()

    def _safe_json(self, text: str) -> dict:
        """Safely parse JSON from model output."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Fallback: extract JSON from text
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            return {}

    def run(self, question: str, experience_level: str = "beginner",
            user_history: Optional[list] = None) -> dict:
        """
        Run the full 4-agent pipeline.
        Returns a structured result with reasoning trace, confidence, and final answer.
        """
        trace = []

        # ── Step 1: Research Agent (RAG retrieval) ────────────────────────────
        context = kb.get_context(question, top_k=3)
        rag_results = kb.retrieve(question, top_k=3)

        research_prompt = RESEARCH_PROMPT.format(question=question, context=context)
        research_raw = self._call(research_prompt)
        research = self._safe_json(research_raw)
        trace.append({
            "agent": "ResearchAgent",
            "output": research,
            "rag_sources": [{"title": d["title"], "category": d["category"], "score": s}
                            for d, s in rag_results]
        })

        question_type = research.get("question_type", "factual")

        # ── Step 2: Reasoning Agent ───────────────────────────────────────────
        time.sleep(2)  # Prevent free-tier rate limiting
        reasoning_prompt = REASONING_PROMPT.format(
            question=question,
            question_type=question_type,
            context=context
        )
        reasoning_raw = self._call(reasoning_prompt)
        reasoning = self._safe_json(reasoning_raw)
        trace.append({"agent": "ReasoningAgent", "output": reasoning})

        # ── Step 3: Critic Agent ──────────────────────────────────────────────
        time.sleep(2)  # Prevent free-tier rate limiting
        critic_prompt = CRITIC_PROMPT.format(
            question=question,
            reasoning=json.dumps(reasoning),
            context=context[:1200]  # trim for token efficiency
        )
        critic_raw = self._call(critic_prompt)
        critic = self._safe_json(critic_raw)
        trace.append({"agent": "CriticAgent", "output": critic})

        # ── Step 4: Persona Agent (final answer) ──────────────────────────────
        time.sleep(2)  # Prevent free-tier rate limiting
        persona_prompt = PERSONA_PROMPT.format(
            question=question,
            experience_level=experience_level,
            core_answer=reasoning.get("core_answer", ""),
            key_facts=reasoning.get("key_facts", []),
            reasoning_steps=reasoning.get("reasoning_steps", []),
            caveats=reasoning.get("caveats", ""),
            official_resource=reasoning.get("official_resource", "vote.gov"),
            confidence_label=critic.get("confidence_label", "Medium"),
            confidence_score=critic.get("confidence_score", 0.75)
        )
        final_answer = self._call(persona_prompt)
        trace.append({"agent": "PersonaAgent", "output": final_answer})

        return {
            "answer": final_answer,
            "confidence_score": critic.get("confidence_score", 0.75),
            "confidence_label": critic.get("confidence_label", "Medium"),
            "reasoning_steps": reasoning.get("reasoning_steps", []),
            "key_facts": reasoning.get("key_facts", []),
            "rag_sources": trace[0]["rag_sources"],
            "missing_info": critic.get("missing_info"),
            "question_type": question_type,
            "agent_trace": trace,
            "experience_level": experience_level
        }
