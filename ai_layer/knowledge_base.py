"""
ai_layer/knowledge_base.py
Election knowledge base for RAG — embedded documents stored in FAISS.
Uses lightweight TF-IDF style matching if sentence-transformers unavailable.
"""
from __future__ import annotations
import json
import math
import re
from typing import List, Tuple

# ── Knowledge Corpus ──────────────────────────────────────────────────────────
ELECTION_DOCS = [
    {"id": "reg-001", "category": "Registration", "title": "How to Register to Vote",
     "content": "Voter registration is the process of signing up to vote. In the US you must be a citizen, at least 18 years old by Election Day, and a resident of the state. Register online at vote.gov, by mail, or in person at the DMV or election office. Deadlines typically fall 15-30 days before an election. Some states like North Dakota require no registration. California, Colorado, and others offer same-day registration."},
    {"id": "reg-002", "category": "Registration", "title": "Voter Registration Deadlines",
     "content": "Registration deadlines vary by state. Most states require registration 15-30 days before an election. Online deadlines may differ from mail-in deadlines. Some states allow same-day voter registration at the polls. Check vote.gov for your exact state deadline. Missing the deadline means you cannot vote in that election cycle unless your state offers same-day registration."},
    {"id": "id-001", "category": "Voting Requirements", "title": "Voter ID Requirements",
     "content": "Voter ID laws vary significantly by state. Strict photo ID states include Georgia, Wisconsin, Indiana — you must show government-issued photo ID. Non-strict photo ID states allow alternative documentation. Some states like California, New York, and Illinois have no photo ID requirement for most voters. Accepted IDs often include driver's license, passport, military ID, or state ID card. Always check your specific state's requirements at vote.gov."},
    {"id": "vote-001", "category": "Voting Process", "title": "How to Vote on Election Day",
     "content": "On Election Day, go to your assigned polling place (find it at vote.gov). Bring required ID if your state requires it. A poll worker will check your registration. You'll receive a paper or electronic ballot. Mark your choices privately in a voting booth. Submit your ballot — paper ballots go into a scanner. The entire process takes 5-15 minutes. If you make a mistake, ask for a new spoiled ballot. If your name isn't on the rolls, request a provisional ballot."},
    {"id": "vote-002", "category": "Voting Process", "title": "Early Voting",
     "content": "Early voting allows registered voters to cast ballots before Election Day. Over 40 states offer in-person early voting, typically 1-2 weeks before the election. No excuse is needed in most states. Early voting reduces Election Day lines and gives you scheduling flexibility. Find your early voting locations and hours at vote.gov or your county election website. Some states call it 'advance voting' or 'in-person absentee voting'."},
    {"id": "mail-001", "category": "Mail Voting", "title": "Mail-In and Absentee Voting",
     "content": "Mail-in voting allows you to vote without going to a polling place. All states allow some form of absentee or mail-in voting. Some states like Oregon, Colorado, Washington, Utah, and Hawaii conduct all elections entirely by mail. To vote by mail: request a ballot from your county clerk, receive it by mail, mark it privately, sign the envelope, and return it by the deadline. Many states let you track your mail ballot status online. Apply early — deadlines are typically 1-2 weeks before the election."},
    {"id": "count-001", "category": "Vote Counting", "title": "How Votes Are Counted",
     "content": "After polls close, ballots are counted by trained election officials using optical scanning machines that read paper ballots. All counting is done in public observation rooms where both parties have certified poll watchers. Mail-in ballots may take several days to process because each signature must be verified against voter registration records. A random sample of ballots is always hand-audited to verify machine accuracy. Results on election night are UNOFFICIAL preliminary counts, not certified results."},
    {"id": "count-002", "category": "Certification", "title": "Election Certification Process",
     "content": "Canvassing is the official process of verifying all ballots were properly counted. Election officials reconcile voter rolls with ballots cast, process provisional ballots, and adjudicate any irregular ballots. Counties certify results first, then the state certifies. This process takes days to weeks. Recounts can be requested if the margin is within a certain threshold (varies by state). The certified results are the legal, official outcome of the election."},
    {"id": "ec-001", "category": "Electoral College", "title": "How the Electoral College Works",
     "content": "The Electoral College is the system used to elect the US President. There are 538 total Electoral Votes. A candidate needs 270 to win. Each state gets Electoral Votes equal to its total Congressional seats (House + Senate). Most states use winner-take-all — whoever wins the state's popular vote gets ALL of its Electoral Votes. Maine and Nebraska allocate Electoral Votes by congressional district. Electors meet in their state capitals in December. Congress certifies the count in January."},
    {"id": "primary-001", "category": "Election Types", "title": "Primary vs General Elections",
     "content": "A primary election is held before the general election to select each party's candidate. Primaries can be open (any registered voter may participate), closed (only registered party members can vote), or semi-open. The general election is when all candidates from all parties appear on the same ballot. The winner of the general election takes office. Presidential primaries work differently — voters select delegates who go to the national party convention to nominate the presidential candidate."},
    {"id": "ballot-001", "category": "Ballots", "title": "Understanding Your Ballot",
     "content": "Your ballot will contain races for multiple offices at federal, state, and local levels. It may also include ballot measures (also called propositions or initiatives) — these are direct votes on laws or constitutional amendments. Read the full text of measures carefully. Nonpartisan races like judges may also appear. You don't have to vote in every race — it's perfectly valid to only vote in the races you care about. Leaving a race blank (undervoting) is legal."},
    {"id": "provisional-001", "category": "Voting Rights", "title": "Provisional Ballots",
     "content": "A provisional ballot is a safeguard ensuring your vote is counted even if there's a question about your eligibility. You receive a provisional ballot if your name isn't in the poll book, you moved and didn't update registration, you requested a mail ballot but want to vote in person, or your ID is questioned. Your ballot is set aside and election officials verify your eligibility after Election Day. If confirmed eligible, your vote counts. You can usually track the status of your provisional ballot online."},
    {"id": "rights-001", "category": "Voting Rights", "title": "Your Rights at the Polling Place",
     "content": "You have the right to vote if you are in line when polls close — you must be allowed to vote. You have the right to a translated ballot or assistance in many languages. You have the right to bring notes or a marked sample ballot. You have the right to request assistance voting if you have a disability. You cannot be turned away based on your appearance or how you are dressed. Poll workers cannot tell you who to vote for. If your rights are violated, call 866-OUR-VOTE (866-687-8683)."},
    {"id": "history-001", "category": "Election History", "title": "History of US Voting Rights",
     "content": "The right to vote in America has expanded significantly over time. The 15th Amendment (1870) gave Black men the right to vote. The 19th Amendment (1920) gave women the right to vote. The 24th Amendment (1964) abolished poll taxes. The Voting Rights Act of 1965 prohibited discriminatory voting practices. The 26th Amendment (1971) lowered the voting age to 18. Today, voter suppression remains a contested issue, with ongoing legal battles over voter ID laws, polling place access, and gerrymandering."},
]

# ── Simple TF-IDF Retriever (no GPU needed) ───────────────────────────────────
class ElectionKnowledgeBase:
    """Lightweight semantic retriever using TF-IDF cosine similarity."""

    def __init__(self):
        self.docs = ELECTION_DOCS
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b[a-z]{2,}\b', text.lower())

    def _build_index(self):
        """Pre-compute TF-IDF vectors for all documents."""
        # Build vocabulary
        all_tokens = []
        self.doc_tokens = []
        for doc in self.docs:
            tokens = self._tokenize(doc["title"] + " " + doc["content"])
            self.doc_tokens.append(tokens)
            all_tokens.extend(tokens)

        # Compute IDF
        vocab = list(set(all_tokens))
        self.vocab_index = {w: i for i, w in enumerate(vocab)}
        N = len(self.docs)
        self.idf = {}
        for word in vocab:
            df = sum(1 for tokens in self.doc_tokens if word in tokens)
            self.idf[word] = math.log((N + 1) / (df + 1)) + 1

        # Pre-compute TF-IDF vectors
        self.doc_vectors = []
        for tokens in self.doc_tokens:
            vec = self._tfidf_vector(tokens)
            self.doc_vectors.append(vec)

    def _tfidf_vector(self, tokens: List[str]) -> dict:
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        total = len(tokens) or 1
        return {w: (c / total) * self.idf.get(w, 1) for w, c in tf.items()}

    def _cosine(self, v1: dict, v2: dict) -> float:
        common = set(v1) & set(v2)
        num = sum(v1[w] * v2[w] for w in common)
        d1 = math.sqrt(sum(x**2 for x in v1.values()))
        d2 = math.sqrt(sum(x**2 for x in v2.values()))
        return num / (d1 * d2 + 1e-9)

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[dict, float]]:
        """Return top_k most relevant docs with similarity scores."""
        q_tokens = self._tokenize(query)
        q_vec = self._tfidf_vector(q_tokens)
        scores = [(doc, self._cosine(q_vec, dvec))
                  for doc, dvec in zip(self.docs, self.doc_vectors)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [(doc, round(score, 4)) for doc, score in scores[:top_k] if score > 0.01]

    def get_context(self, query: str, top_k: int = 3) -> str:
        """Return formatted context string for RAG prompt injection."""
        results = self.retrieve(query, top_k)
        if not results:
            return ""
        parts = []
        for doc, score in results:
            parts.append(f"[{doc['category']} — {doc['title']} | Relevance: {score:.2f}]\n{doc['content']}")
        return "\n\n".join(parts)


# Singleton instance
kb = ElectionKnowledgeBase()
