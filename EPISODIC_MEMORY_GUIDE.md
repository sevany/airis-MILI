# AIRIS EPISODIC MEMORY - USAGE EXAMPLES

## 🎯 SYSTEM OVERVIEW

Episodic Memory is a **meeting and conversation logger** that:
1. Takes raw text input (meeting notes, discussions)
2. Uses Ollama to structure into JSON
3. Stores in ChromaDB with semantic search
4. Automatically injects into chat context when relevant

---

## 📋 API ENDPOINTS

### 1. POST /api/log_memory
**Log a new meeting/conversation**

```bash
curl -X POST http://localhost:5000/api/log_memory \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Meeting with Petronas upstream team. Discussed PRSB simulation challenges. Main issue: synthetic data from forward modeling not matching real seismic data. They need inverse modeling to tune parameters. Mentioned budget constraints - prefer hybrid cloud approach. Decision: Prepare POC with 3-month timeline. Risk: Competitor HPE already engaged.",
    "tag": "Petronas"
  }'
```

**Response:**
```json
{
  "status": "ok",
  "memory_id": "episodic_Petronas_20260511_143022",
  "structured": {
    "type": "meeting",
    "topic": "Petronas PRSB simulation challenges and POC proposal",
    "summary": "Discussion with Petronas upstream about PRSB simulation mismatch between synthetic and real data. Decided on 3-month POC with hybrid cloud approach due to budget constraints. HPE already engaged as competitor.",
    "key_points": [
      "Synthetic data from forward modeling not matching real seismic",
      "Need inverse modeling to tune geological parameters",
      "Budget constraints favor hybrid over full cloud",
      "HPE is active competitor in this engagement"
    ],
    "decisions": "Prepare POC with 3-month delivery timeline, hybrid cloud architecture",
    "action_items": [
      "Draft POC proposal with hybrid approach",
      "Estimate compute requirements",
      "Competitive analysis vs HPE"
    ],
    "risks": "HPE already engaged, timeline pressure, budget limitations",
    "opportunities": "Long-term partnership if POC successful, potential for other upstream projects",
    "people_mentioned": [],
    "companies_mentioned": ["Petronas", "HPE"],
    "importance": "high"
  },
  "message": "Memory logged with tag: Petronas"
}
```

---

### 2. POST /api/episodic_memory/search
**Search stored memories**

```bash
curl -X POST http://localhost:5000/api/episodic_memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PRSB challenges with synthetic data",
    "n_results": 3,
    "tag_filter": "Petronas"
  }'
```

**Response:**
```json
{
  "results": [
    {
      "structured": {
        "topic": "Petronas PRSB simulation challenges",
        "summary": "...",
        "key_points": [...]
      },
      "metadata": {
        "tag": "Petronas",
        "importance": "high",
        "timestamp": "2026-05-11T14:30:22"
      },
      "distance": 0.23
    }
  ],
  "count": 1
}
```

---

### 3. GET /api/episodic_memory/by_tag/{tag}
**Get all memories with specific tag**

```bash
curl http://localhost:5000/api/episodic_memory/by_tag/PRSB?limit=5
```

**Response:**
```json
{
  "tag": "PRSB",
  "memories": [
    {
      "structured": {...},
      "metadata": {...}
    }
  ],
  "count": 3
}
```

---

### 4. GET /api/episodic_memory/tags
**Get all available tags**

```bash
curl http://localhost:5000/api/episodic_memory/tags
```

**Response:**
```json
{
  "tags": ["Petronas", "PRSB", "Boustead", "MINDEF", "Personal"]
}
```

---

### 5. GET /api/episodic_memory/stats
**Get memory statistics**

```bash
curl http://localhost:5000/api/episodic_memory/stats
```

**Response:**
```json
{
  "total_memories": 15,
  "tags": {
    "Petronas": 5,
    "PRSB": 3,
    "Boustead": 4,
    "MINDEF": 2,
    "Personal": 1
  },
  "importance_distribution": {
    "low": 2,
    "medium": 8,
    "high": 5
  },
  "with_decisions": 10,
  "with_risks": 7
}
```

---

### 6. DELETE /api/episodic_memory/{memory_id}
**Delete a specific memory**

```bash
curl -X DELETE http://localhost:5000/api/episodic_memory/episodic_Petronas_20260511_143022
```

---

## 🔄 CHAT INTEGRATION

Episodic memories are **automatically injected** into chat context when relevant.

### Example 1: Asking about past meetings

**You:**
```
What did we discuss with Petronas about PRSB?
```

**Backend process:**
1. Query triggers episodic memory search: "Petronas PRSB"
2. Retrieves top 3 relevant meetings
3. Injects into context:
```
=== RELEVANT PAST MEETINGS & DISCUSSIONS ===

[Petronas - MEETING]
Topic: Petronas PRSB simulation challenges and POC proposal
Summary: Discussion with Petronas upstream about PRSB simulation mismatch...
Key Points:
  • Synthetic data not matching real seismic
  • Need inverse modeling
  • Budget constraints favor hybrid
Decisions: Prepare POC with 3-month timeline, hybrid architecture
Risks: HPE already engaged, timeline pressure
Importance: HIGH

=== END EPISODIC MEMORY ===
```
4. Ollama responds with context

**AIRIS:**
```
In our meeting with Petronas, we discussed PRSB simulation challenges. The main issue was synthetic data from forward modeling not matching their real seismic data. They need inverse modeling to tune geological parameters.

We decided to prepare a POC with a 3-month timeline using a hybrid cloud approach due to budget constraints. The key risks are that HPE is already engaged, and we're under timeline pressure.

Would you like me to help draft that POC proposal?
```

---

### Example 2: Strategic planning

**You:**
```
What are our biggest risks with current client engagements?
```

**Backend:**
- Searches ALL episodic memories with `has_risks: yes`
- Aggregates across tags
- Provides comprehensive context

**AIRIS:**
```
Based on our logged meetings, here are the key risks:

Petronas:
- HPE already engaged as competitor
- Tight 3-month POC timeline
- Budget limitations

Boustead:
- Unclear decision-making process
- Multiple stakeholders with different priorities

MINDEF:
- Security clearance requirements
- Long procurement cycles

Should we prioritize mitigation strategies for any of these?
```

---

## 🧪 TESTING WORKFLOW

### Step 1: Log a meeting
```bash
curl -X POST http://localhost:5000/api/log_memory \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Boustead defense meeting. Discussed INTAI drone intelligence capabilities. They are interested in real-time video manipulation for deception ops. Mentioned integration with existing surveillance systems. Decision: Demo in 2 weeks. Risk: Need security clearance. Opportunity: Multi-year contract potential.",
    "tag": "Boustead"
  }'
```

### Step 2: Verify storage
```bash
curl http://localhost:5000/api/episodic_memory/stats
```

### Step 3: Search
```bash
curl -X POST http://localhost:5000/api/episodic_memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "INTAI capabilities", "n_results": 1}'
```

### Step 4: Test chat integration
Open chat UI and ask:
```
What did we discuss with Boustead about INTAI?
```

AIRIS should recall the meeting details!

---

## 📊 RECOMMENDED TAGS

```
- Petronas       → Oil & Gas client engagements
- PRSB           → PRSB simulation project
- Boustead       → Defense collaboration
- MINDEF         → Defense ministry engagements
- INTAI          → INTAI project discussions
- ADAM           → ADAM infrastructure topics
- Personal       → Personal notes
- Strategy       → Strategic planning sessions
- Technical      → Technical deep dives
- Financial      → Budget/pricing discussions
```

---

## 🔧 INTEGRATION POINTS

### In app.py:

**Initialization:**
```python
episodic_memory = EpisodicMemory(ollama_client=ollama)
```

**Chat context injection (line ~240):**
```python
# Get EPISODIC MEMORY context
episodic_stats = episodic_memory.get_stats()
if episodic_stats['total_memories'] > 0:
    episodic_context_raw = episodic_memory.get_context_for_query(user_message, max_memories=3)
    if episodic_context_raw:
        episodic_context = f"\n\n{episodic_context_raw}\n"
```

**Context combination:**
```python
combined_context = xauusd_context
if profile_context:
    combined_context = (combined_context or "") + profile_context
if document_context:
    combined_context = (combined_context or "") + document_context
if episodic_context:
    combined_context = (combined_context or "") + episodic_context  # ← NEW
if vector_context:
    combined_context = (combined_context or "") + vector_context
```

---

## ⚠️ IMPORTANT NOTES

1. **Ollama requirement:** Summarization uses Ollama (qwen2.5:235b)
2. **Separate collection:** Episodic memory uses its own ChromaDB collection
3. **No conflicts:** Does NOT interfere with existing VectorMemory or DocumentRAG
4. **Automatic retrieval:** Memories injected automatically when relevant
5. **Production-ready:** Includes error handling, fallbacks, and structured logging

---

## 🎯 USE CASES

### For Myra:

1. **After client meetings:**
   - Log meeting notes immediately
   - AIRIS structures and stores them
   - Reference in future conversations

2. **Strategic planning:**
   - "What are common objections from clients?"
   - AIRIS aggregates across all logged meetings

3. **Preparation:**
   - "What did we discuss with Petronas last time?"
   - Instant recall with full context

4. **Risk management:**
   - "Show me all high-risk engagements"
   - Filter by importance level

5. **Knowledge building:**
   - Over time, builds institutional memory
   - No more lost context from past discussions

---

## 🔥 PRODUCTION DEPLOYMENT

**Files modified:**
- `backend/core/episodic_memory.py` (NEW)
- `backend/app.py` (EXTENDED)

**No files broken:**
- All existing memory systems intact
- All existing endpoints functional
- Modular addition only

**Testing:**
```bash
# 1. Copy files
cp episodic_memory.py backend/core/
cp app.py backend/

# 2. Clear cache
rm -rf backend/core/__pycache__/
rm -rf backend/__pycache__/

# 3. Restart
python3 -m backend.app

# 4. Test health
curl http://localhost:5000/api/health

# 5. Log first memory
curl -X POST http://localhost:5000/api/log_memory \
  -H "Content-Type: application/json" \
  -d '{"text": "Test meeting", "tag": "Test"}'
```

---

**SYSTEM IS PRODUCTION-READY!** 🚀
