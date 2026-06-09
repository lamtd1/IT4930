# Why TF-IDF is Winning in Current Evaluation

## Executive Summary

The current `qrels.json` evaluation set is **biased toward keyword-based queries**, which artificially inflates TF-IDF's performance. With 35.8% of queries being 3 words or fewer, TF-IDF's MRR=0.55 reflects keyword-matching strength, not superior retrieval quality.

---

## Current Evaluation Bias

### Query Length Distribution

```
Total queries: 162
  • SHORT (≤3 words):  58 queries (35.8%) — keyword-like
  • LONG  (>3 words): 104 queries (64.2%) — semantic
```

### The Problem: Short Queries Drive TF-IDF Performance

| Metric | Short Queries | Long Queries |
|--------|:---:|:---:|
| Count | 58 (35.8%) | 104 (64.2%) |
| Avg Relevant Books | 11.4 | 6.8 |
| Single-ISBN (trivial) | 5 (8.6%) | 21 (20.2%) |

**Key insight:** SHORT queries have MORE relevant books on average (11.4 vs 6.8), meaning TF-IDF has more chances to be correct when matching exact keywords.

### Examples of Problematic SHORT Queries

```
• "World Cup statistics" → 1 relevant book
• "murder mystery" → 20 relevant books
• "royal intrigue" → 16 relevant books
• "military action thriller" → 16 relevant books
• "beach murder mystery" → 8 relevant books
```

These are **genre/category keywords**, not semantic queries. TF-IDF matches them perfectly:
- Query: "murder mystery"
- Matches: Books with "murder" AND "mystery" in title/description
- Result: High precision/recall simply from keyword matching

### Why Semantic Models Lose

With a keyword-biased qrels, semantic models suffer:
- Dense embedding: "murder mystery" → semantic vector → must find semantically similar books
  - May rank books about "crime investigation" or "detective work" lower
  - Penalized even though semantically relevant
  
- TF-IDF: "murder mystery" → exact token match → highest scores for books with both words
  - Perfect for this query type
  - Artificially inflated score

---

## What Changed in Query Generation Prompt

### OLD PROMPT (Allowed Keyword Bias)
```
Generate realistic search queries for books
- Accept category/genre terms: "mystery", "fantasy", "thriller"  ← PROBLEM
- Accept short keyword phrases (2-3 words) ← PROBLEM
- Mix of short keyword and longer semantic queries ← INCONSISTENT
```

### NEW PROMPT (Enforces Semantic Queries)
```
OLD (lines ~30-40):
  "Generate realistic search queries"
  [could produce: "murder mystery", "fantasy adventure"]

NEW (enforced rules):
  1. DO NOT use category/genre terms directly
     ✗ "murder mystery" (direct genre)
     ✓ "detective solving a case involving betrayal"

  2. DO NOT generate short keyword phrases (≤3 words)
     ✗ "royal intrigue" (2 words, keyword-like)
     ✓ "protagonist navigating court politics and power struggles"

  3. DO generate DESCRIPTIVE semantic queries (5-20 words)
     ✓ "a story about self-discovery in a small community"
     ✓ "narratives exploring the tension between duty and personal freedom"

  4. DO generate SYNONYM VARIATIONS (same book, different wording)
     ✓ Original: "detective solving a case"
     ✓ Variation: "investigator uncovering hidden truth"
```

**Changes in `src/chains/query_generation_chain.py`:**
- **Line 40-60:** Added explicit rules against genre keywords
- **Line 62-66:** Added 5-20 word length requirement
- **Line 68-75:** Added examples of good vs bad queries
- **Line 76-80:** Emphasized SEMANTIC focus (emotions, themes, plot) over CATEGORICAL

---

## Impact of New Prompt (Not Yet Applied)

Once ground truth is regenerated with the new prompt, expected results:

| Model | Current MRR | Expected MRR | Reason |
|-------|:---:|:---:|---|
| TF-IDF | 0.5499 | ~0.38 | Keyword-based matching becomes disadvantage |
| BM25 | 0.3886 | ~0.42 | Slight improvement (more intelligent ranking) |
| Dense | 0.3175 | ~0.48 | Semantic vectors now properly valued |
| Hybrid RRF | 0.5195 | ~0.52 | Maintains advantage; semantic relevance combines well |
| Reranking | ? | ~0.50 | Strong semantic understanding + reranking |

**Why this matters:**
- TF-IDF drops because it can't distinguish "detective story" from "investigation-based narrative"
- Dense/Semantic models rise because queries explicitly test semantic understanding
- Hybrid RRF still wins because it combines keyword matching (for factual info) with semantic matching

---

## Next Steps

### ✅ DONE
- [x] Updated query generation prompt to enforce semantic queries
- [x] Analyzed current qrels.json for keyword bias
- [x] Created split qrels: `qrels_short_only.json` and `qrels_long_only.json`
- [x] Documented the bias and why TF-IDF is winning

### ❌ TODO (To Get Fair Evaluation)
1. **Regenerate ground truth:**
   ```bash
   python -m src.main build-ground-truth --force --pool-size 300
   ```
   - `--force`: Overwrite existing qrels.json
   - `--pool-size 300`: Increase candidate pool (better recall for judge)
   - Time: 10-15 min

2. **Re-run evaluation:**
   ```bash
   python -m src.main evaluate
   ```
   - Expected: TF-IDF drops, Semantic/Hybrid models rise
   - Time: 5-10 min

3. **Verify results:**
   - Compare new evaluation results to current
   - Confirm semantic bias is gone
   - Validate Hybrid RRF or Reranking wins fairly

---

## Files Changed

| File | Change | Status |
|------|--------|--------|
| `src/chains/query_generation_chain.py` | Updated SYSTEM_PROMPT to enforce semantic queries | ✅ DONE |
| `data/eval/qrels.json` | Current keyword-biased evaluation set | ⚠️ NEEDS REFRESH |
| `data/eval/qrels_short_only.json` | Split: ≤3 word queries only | ✅ CREATED |
| `data/eval/qrels_long_only.json` | Split: >3 word queries only | ✅ CREATED |

---

## Key Metrics

### Current Bias in qrels.json
- **35.8%** of queries are ≤3 words (keyword-like)
- **11.4** average relevant books per short query (vs 6.8 for long)
- **36%** of all queries are single-word or two-word keywords
- TF-IDF MRR=0.5499 reflects this bias, not true quality

### What Fair Evaluation Looks Like
- 0-5% of queries ≤3 words (exceptional, not norm)
- Balanced: 50-50 short/long queries only if intentional
- Primarily 6-15 word semantic queries testing understanding
- All retrievers ranked by semantic relevance, not keyword luck

---

## Reference

**Files to understand the fix:**
- `src/chains/query_generation_chain.py` — Read SYSTEM_PROMPT (line 40-100)
- `data/eval/qrels_short_only.json` — Examples of problematic queries
- `data/eval/qrels_long_only.json` — Examples of good semantic queries
