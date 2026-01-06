# Product Requirements Document (PRD)
## AI Academic Writing Agent - Simplified Version

**Project Timeline:** 30 Days  
**Goal:** Generate structured, citation-grounded academic papers from minimal user input (topic + template structure)

---

## 1. Problem Statement

Students need to write academic papers (5,000+ words) with:
- Proper structure and academic tone
- Valid, verifiable citations (no hallucinations)
- Coherent arguments across sections
- Minimal manual research effort

**Key Challenge:** Existing LLMs hallucinate citations and lose coherence across long documents.

---

## 2. User Input (Simplified)

Users provide a simple JSON with:
1. **Topic:** The research subject
2. **Template:** Section names only (e.g., Introduction, Literature Review, Methodology, Findings, Conclusion)
3. **Style Guidelines (Optional):** Writing tone and approach preferences
4. **Citation Style (Optional):** Formatting standard for references
5. **Custom Criteria (Optional):** Additional evaluation requirements

### Example Input
```json
{
  "topic": "Impact of microplastics on marine biodiversity",
  "template": [
    "Introduction",
    "Statement of Research Problem", 
    "Research Objectives",
    "Key Concepts in Literature",
    "Methodology",
    "Key Findings",
    "Conclusion",
    "Recommendations",
    "Selected References"
  ],
  "style_guidelines": {
    "tone": "professional",
    "clarity": "accessible_to_undergraduates",
    "voice": "active",
    "sentence_complexity": "moderate",
    "technical_depth": "intermediate"
  },
  "citation_style": "APA-7",
  "custom_criteria": {
    "max_section_length": 1500,
    "min_citations_per_section": 5,
    "require_counterarguments": true,
    "avoid_jargon": ["anthropogenic", "phytoplankton"],
    "preferred_terminology": {
      "plastic pollution": "microplastic contamination"
    }
  }
}
```

---

## 3. System Workflow

### Phase 1: Planning (Human-in-the-Loop)
1. **Outline Agent** analyzes topic and generates key research questions
2. **Human + Supervisor Review** the questions (most critical checkpoint)
3. Questions become the "contract" that guides the entire paper

### Phase 2: Research
4. **Research Agent** gathers academic sources (papers, articles) relevant to each question
5. Sources are stored with metadata and embeddings

### Phase 3: Drafting (Section-by-Section)
6. **Planning Agent** creates detailed outline mapping research to template sections
7. **Context Manager** assembles relevant context for current section:
   - Key research questions
   - Previous section (for continuity)
   - Relevant older sections (via embeddings)
   - Retrieved research materials
8. **Drafting Agent** writes the section (1,000-1,500 words)

### Phase 4: Evaluation (Quality Loop)
9. **Evaluator Agent** checks draft against key questions and citation validity
10. If issues found → trigger rewrite (max 5 attempts)
11. If passes → move to next section

### Phase 5: Export
12. **Exporter** formats complete paper to PDF/Word with bibliography

---

## 4. Core Modules

| Module | Input | Output | Key Responsibility |
|--------|-------|--------|-------------------|
| **Orchestrator** | User JSON | Completed paper | Coordinates all agents, manages retry loops, tracks state |
| **Outline Agent** | Topic | Research questions | Generates 5-10 key questions the paper must answer |
| **Research Agent** | Topic + questions | Annotated bibliography | Searches academic APIs, extracts relevant snippets |
| **Planning Agent** | Research + questions | Section outline | Maps research to template sections |
| **Context Manager** | Section ID | Assembled context | Retrieves relevant previous content + research |
| **Drafting Agent** | Context + section goal | Draft section | Writes 1,000-1,500 words with citations |
| **Evaluator Agent** | Draft + questions | Pass/Fail + feedback | Validates citations, checks question coverage |
| **Exporter** | Complete draft | PDF/Word | Formats final document |

---

## 5. Anti-Hallucination Strategy

### Problem
LLMs frequently fabricate citations that don't exist.

### Solutions
1. **Source-Grounded Writing:** Drafting agent can ONLY cite snippets from Research Agent's database
2. **Citation Validation:** Evaluator cross-checks every citation against research database
3. **Forced Attribution:** Every claim must trace back to a specific source
4. **Research Database as Single Source of Truth:** No external knowledge allowed

---

## 6. Context Management Strategy

### Problem
5,000-word papers exceed LLM context windows. How to maintain coherence?

### Solution: Multi-Layer Context Assembly
For each section being drafted, Context Manager provides:

1. **Always Include:**
   - Key research questions (the "contract")
   - Immediately previous section (for continuity)
   - Current section goal

2. **Conditionally Include (via embeddings):**
   - Older sections that are topically relevant
   - Query-aware summaries (focused on what current section needs)

3. **Prioritize:**
   - Thesis → Recent sections → Relevant old sections → Research materials

---

## 7. Retry & Quality Control

### Bounded Iteration
- Each section gets **max 5 rewrite attempts**
- After 5 failures: Review evaluation criteria or escalate to human
- Track retry reason (missing citations vs wrong structure vs research gaps)

### Evaluation Criteria (Base + Custom)

#### Base Criteria (Always Applied)
- ✓ Does section answer assigned research questions?
- ✓ Are all citations valid (exist in research database)?
- ✓ Word count within bounds?
- ✓ Maintains terminology/tone from previous sections?

#### Style Guidelines Evaluation
If user provides style guidelines, also check:
- ✓ **Tone Match:** "professional" vs "conversational" vs "formal"
- ✓ **Clarity Level:** "accessible_to_undergraduates" vs "graduate_level" vs "expert"
- ✓ **Voice:** Active vs passive voice usage
- ✓ **Sentence Complexity:** Simple vs moderate vs complex sentence structures
- ✓ **Technical Depth:** Layman terms vs intermediate vs highly technical

#### Citation Style Evaluation
- ✓ **Format Compliance:** APA-7 vs Harvard vs MLA vs Chicago
- ✓ **In-text citations:** Correct format for style (Author, Year) vs [1] vs (Author Year)
- ✓ **Bibliography format:** Matches selected style exactly
- ✓ **Consistency:** Same style throughout document

#### Custom Criteria Evaluation (User-Defined)
- ✓ Section length constraints (min/max words)
- ✓ Minimum citations per section
- ✓ Required elements (e.g., counterarguments, case studies)
- ✓ Terminology preferences (avoid certain jargon, use preferred terms)
- ✓ Structural requirements (e.g., must include data tables, figures)

### Evaluation Prompt Enhancement
```
Evaluate this section against:

BASE CRITERIA:
- Answers questions: [list questions]
- Citations valid: [check against DB]
- Word count: {actual} (target: {target_range})

STYLE GUIDELINES:
- Tone: {user.tone} → Current tone: [analyze]
- Clarity: {user.clarity} → Current level: [analyze]
- Voice: {user.voice} → Active voice %: [calculate]
- Technical depth: {user.technical_depth} → Assessment: [analyze]

CITATION STYLE: {user.citation_style}
- In-text format: [check examples]
- Bibliography: [validate format]

CUSTOM CRITERIA:
- Min citations: {user.min_citations} → Actual: [count]
- Avoided jargon: {user.avoid_jargon} → Check: [scan]
- Required elements: {user.required_elements} → Present: [verify]

Return structured feedback for each failing criterion.
```

---

## 8. System Architecture

**Pattern:** Centralized Orchestrator (all agents report to single controller)

```
┌─────────────────────────────────────┐
│         ORCHESTRATOR                │
│  - Task queue management            │
│  - Retry loop control               │
│  - State persistence                │
│  - Logging & error handling         │
└─────────────────────────────────────┘
         │
         ├──→ Outline Agent
         ├──→ Research Agent  
         ├──→ Planning Agent
         ├──→ Context Manager (Vector DB)
         ├──→ Drafting Agent
         ├──→ Evaluator Agent
         └──→ Exporter

Communication: Orchestrator ↔ Agent (no peer-to-peer)
```

---

## 9. Key Design Decisions

### 9.1 Why Centralized Orchestration?
- **Pro:** Single point of control, easy debugging, clear state transitions
- **Con:** Bottleneck (acceptable for first project)
- **Alternative Rejected:** Message-passing between agents (too complex for v1)

### 9.2 Why Human Review at Questions Stage?
- **Highest leverage point:** Sets direction before work begins
- **Prevents:** System going off-track after expensive computation
- **Low cost:** Review 10 questions vs reviewing 5,000 words

### 9.3 Why Section-by-Section Drafting?
- **Context window:** Can't fit entire 5,000-word paper in one prompt
- **Coherence:** Context Manager ensures each section knows previous context
- **Quality:** Easier to evaluate and iterate on smaller chunks

### 9.4 Why Max 5 Retries?
- **Balance:** Give system room to improve without infinite loops
- **Cost control:** Prevent runaway API costs
- **Escape hatch:** After 5 attempts, likely a systemic issue (bad research, impossible criteria)

---

## 10. Success Metrics

### Must-Have (MVP)
- ✓ Generate 5,000-word paper from topic + template
- ✓ Zero fabricated citations (all traceable to sources)
- ✓ Coherent argument flow across sections
- ✓ Complete in <4 hours runtime

### Nice-to-Have (Future)
- Multiple writing styles (formal, technical, accessible)
- Real-time progress updates
- Collaborative editing with human
- Support for non-academic writing

---

## 11. Out of Scope (v1)

- ❌ Image/figure generation
- ❌ Data analysis or statistics
- ❌ Multi-language support (English only)
- ❌ Real-time collaboration (single user)
- ❌ Version control / branching drafts
- ❌ Custom citation styles (APA only for v1)

---

## 12. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Hallucinated citations | High | Critical | Source-grounded writing + citation validator |
| Research APIs rate-limited | Medium | High | Caching + batch requests + fallback APIs |
| Context coherence failures | Medium | High | Hybrid context assembly (recency + relevance) |
| Infinite retry loops | Medium | Medium | Bounded retries (max 5) + criteria review |
| Runtime >4 hours | Low | Medium | Parallel research + optimize prompts |
| LLM API costs spike | Medium | High | Token budgets per section + free LLM fallback |

---

## 13. Non-Functional Requirements

### Performance
- Generate 1 section in <5 minutes
- Complete 8-section paper in <4 hours
- Support 10 concurrent papers (future)

### Reliability
- Graceful degradation if APIs fail
- State persistence (resume after crash)
- Comprehensive logging for debugging

### Cost
- Target: <$2 per paper (using Claude/GPT-4)
- Fallback: Free LLMs (LLaMA) if budget exhausted

### Observability
- Log every agent decision
- Track retry reasons
- Measure token usage per section
- Export trace for debugging

---

## 14. Deliverables (End of 30 Days)

1. **Functional System** that takes JSON input and produces formatted academic paper
2. **CLI Interface** for running the system
3. **Research Database** with 50+ papers for testing
4. **Test Suite** covering each module
5. **Documentation:**
   - API documentation
   - Architecture diagram
   - Example outputs
   - Troubleshooting guide
6. **Demo Video** showing end-to-end workflow

---

## 15. Future Enhancements (Post-v1)

- Web interface for non-technical users
- Support for multiple citation styles (MLA, Chicago, Harvard)
- Collaborative editing mode
- Integration with reference managers (Zotero, Mendeley)
- Export to LaTeX for academic journals
- Multi-language support
- Fine-tuned models for specific academic disciplines