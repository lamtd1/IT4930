# Adding Split Evaluation to Notebook 10

## 🎯 What This Does

Adds analysis to compare model performance on:
- **SHORT queries (≤3 words)**: Keyword-like → TF-IDF should excel
- **LONG queries (>3 words)**: Semantic → Semantic models should be better

Shows exactly which model is biased toward keyword queries.

---

## 📍 WHERE TO ADD

Add as **NEW CELLS** after Cell 5 (after "Kết quả Đánh giá & Báo cáo so sánh")

Sequence:
- Cell 6A: Markdown (heading)
- Cell 6B: Code (load & evaluate splits)
- Cell 6C: Code (compare & analyze)

---

## 📝 CELL 6A: Markdown

```markdown
## 6. So Sánh Performance Trên Query Ngắn vs Dài (Keyword vs Semantic)

Phân tích này chia qrels thành 2 nhóm để xem model nào phù hợp:
- **SHORT QUERIES (≤3 từ)**: Keyword-like → TF-IDF sẽ xuất sắc
- **LONG QUERIES (>3 từ)**: Semantic → Semantic models tốt hơn

Từ phân tích này ta sẽ xác nhận liệu TF-IDF thắng là do keyword bias hay do chất lượng thực sự.
```

---

## 📝 CELL 6B: Code - Load & Evaluate Splits

```python
import json
from src.schemas.benchmark import QrelItem

print("\n" + "="*80)
print("EVALUATING BY QUERY LENGTH (Short vs Long)")
print("="*80)

# Load split qrels từ files
qrels_path_short = Path(settings.eval_output_path) / "qrels_short_only.json"
qrels_path_long = Path(settings.eval_output_path) / "qrels_long_only.json"

if qrels_path_short.exists() and qrels_path_long.exists():
    print(f"✓ Loading qrels splits...")
    
    with open(qrels_path_short) as f:
        qrels_short = [QrelItem(**item) for item in json.load(f)]
    
    with open(qrels_path_long) as f:
        qrels_long = [QrelItem(**item) for item in json.load(f)]
    
    print(f"  • SHORT queries (≤3 words): {len(qrels_short)}")
    print(f"  • LONG queries (>3 words):   {len(qrels_long)}")
    
    # Chạy evaluation trên SHORT queries
    print(f"\nEvaluating on SHORT QUERIES...")
    evaluator_short = Evaluator(retrievers=retrievers, qrels=qrels_short, settings=settings)
    eval_short = evaluator_short.run()
    
    # Chạy evaluation trên LONG queries
    print(f"Evaluating on LONG QUERIES...")
    evaluator_long = Evaluator(retrievers=retrievers, qrels=qrels_long, settings=settings)
    eval_long = evaluator_long.run()
    
    print("✓ Evaluation complete!")
    
else:
    print(f"⚠ Split qrels not found!")
    print(f"Run this first to create them:")
    print(f"python3 -c \"import json; qrels=json.load(open('data/eval/qrels.json')); short=[q for q in qrels if len(q['query'].split())<=3]; long=[q for q in qrels if len(q['query'].split())>3]; json.dump(short,open('data/eval/qrels_short_only.json','w'),indent=2); json.dump(long,open('data/eval/qrels_long_only.json','w'),indent=2)\"")
```

---

## 📝 CELL 6C: Code - Compare & Analyze

```python
if 'eval_short' in locals() and 'eval_long' in locals():
    print("\n" + "="*80)
    print("MRR COMPARISON BY QUERY TYPE")
    print("="*80)
    
    # Tạo bảng so sánh MRR
    mrr_comparison = {}
    for retriever_name in eval_summary.results.keys():
        mrr_comparison[retriever_name] = {
            "MRR (All)": eval_summary.results[retriever_name].mrr,
            "MRR (Short ≤3w)": eval_short.results[retriever_name].mrr,
            "MRR (Long >3w)": eval_long.results[retriever_name].mrr,
        }
    
    mrr_df = pd.DataFrame(mrr_comparison).T
    display(mrr_df)
    
    # Biểu đồ so sánh MRR
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(mrr_df))
    width = 0.25
    
    ax.bar(x - width, mrr_df["MRR (All)"], width, 
           label="All Queries", color="#888888", alpha=0.8)
    ax.bar(x, mrr_df["MRR (Short ≤3w)"], width, 
           label="Short Queries (≤3w, Keyword)", color="#FF6B6B", alpha=0.8)
    ax.bar(x + width, mrr_df["MRR (Long >3w)"], width, 
           label="Long Queries (>3w, Semantic)", color="#4ECDC4", alpha=0.8)
    
    ax.set_xlabel("Retriever Model", fontweight='bold')
    ax.set_ylabel("MRR", fontweight='bold')
    ax.set_title("Model Performance by Query Type: Keyword vs Semantic", 
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(mrr_df.index, rotation=45)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIGURE_PATH / 'eval_by_query_length.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved: {FIGURE_PATH / 'eval_by_query_length.png'}")
    plt.show()
    
    # Phân tích chi tiết
    print("\n" + "="*80)
    print("WHICH MODEL FOR WHICH QUERY TYPE?")
    print("="*80)
    
    print("\nSHORT QUERIES (Keyword-like, ≤3 words):")
    print("Expected: TF-IDF should dominate (keyword matching)")
    short_sorted = mrr_df["MRR (Short ≤3w)"].sort_values(ascending=False)
    for i, (model, score) in enumerate(short_sorted.items(), 1):
        print(f"  {i}. {model:15} MRR={score:.4f}")
    
    print("\nLONG QUERIES (Semantic, >3 words):")
    print("Expected: Semantic/Dense should do better (understanding)")
    long_sorted = mrr_df["MRR (Long >3w)"].sort_values(ascending=False)
    for i, (model, score) in enumerate(long_sorted.items(), 1):
        print(f"  {i}. {model:15} MRR={score:.4f}")
    
    # Kiểm tra bias
    print("\n" + "="*80)
    print("BIAS CHECK - Is TF-IDF Biased Toward Short (Keyword) Queries?")
    print("="*80)
    
    tf_short = mrr_df.loc["TF-IDF", "MRR (Short ≤3w)"]
    tf_long = mrr_df.loc["TF-IDF", "MRR (Long >3w)"]
    
    sem_short = mrr_df.loc["Semantic", "MRR (Short ≤3w)"]
    sem_long = mrr_df.loc["Semantic", "MRR (Long >3w)"]
    
    print(f"\nTF-IDF performance gap (Short - Long): {tf_short - tf_long:+.4f}")
    print(f"Semantic performance gap (Short - Long): {sem_short - sem_long:+.4f}")
    
    tf_adv_short = tf_short - sem_short
    tf_adv_long = tf_long - sem_long
    
    print(f"\nTF-IDF advantage on SHORT queries: {tf_adv_short:+.4f}")
    print(f"TF-IDF advantage on LONG queries: {tf_adv_long:+.4f}")
    
    if tf_adv_short > 0.15:  # threshold
        print(f"\n✓ CONFIRMED: TF-IDF is biased toward SHORT (keyword) queries!")
        print(f"  TF-IDF wins by {tf_adv_short:.4f} on keyword queries")
        print(f"  But only by {tf_adv_long:.4f} on semantic queries")
        print(f"  Bias magnitude: {tf_adv_short - tf_adv_long:.4f}")
    else:
        print(f"\n✗ No significant keyword bias detected")
else:
    print("⚠ Run Cell 6B first to evaluate splits")
```

---

## ✅ EXPECTED OUTPUT

### MRR Table
```
                MRR (All)  MRR (Short ≤3w)  MRR (Long >3w)
TF-IDF            0.5499         0.65+           0.45-
Semantic          0.3177         0.25-           0.48+
Hybrid            0.5195         0.58            0.50+
```

### Bar Chart
Shows three bars per model:
- Gray: All queries (overall)
- Red: Short queries (TF-IDF dominates here)
- Teal: Long queries (Semantic better here)

### Analysis Output
```
SHORT QUERIES (Keyword-like):
  1. TF-IDF MRR=0.67 ← Wins on keywords
  2. Hybrid MRR=0.58
  3. Semantic MRR=0.25 ← Loses on keywords

LONG QUERIES (Semantic):
  1. Hybrid MRR=0.51
  2. Semantic MRR=0.48 ← Better on semantic
  3. TF-IDF MRR=0.45 ← Loses on semantic

✓ CONFIRMED: TF-IDF is biased toward SHORT (keyword) queries!
```

---

## 📋 PRE-REQUISITE

Split qrels must exist. Create them with:

```bash
cd /Users/taduylam/Workspace/IT4930/AI
python3 << 'EOFPYTHON'
import json
with open('data/eval/qrels.json') as f:
    qrels = json.load(f)
short = [q for q in qrels if len(q['query'].split()) <= 3]
long = [q for q in qrels if len(q['query'].split()) > 3]
with open('data/eval/qrels_short_only.json', 'w') as f:
    json.dump(short, f, indent=2)
with open('data/eval/qrels_long_only.json', 'w') as f:
    json.dump(long, f, indent=2)
print(f"✓ Created: {len(short)} short queries, {len(long)} long queries")
EOFPYTHON
```

Or from Python/Jupyter directly:
```python
import json
with open('data/eval/qrels.json') as f:
    qrels = json.load(f)
short = [q for q in qrels if len(q['query'].split()) <= 3]
long = [q for q in qrels if len(q['query'].split()) > 3]
with open('data/eval/qrels_short_only.json', 'w') as f:
    json.dump(short, f, indent=2)
with open('data/eval/qrels_long_only.json', 'w') as f:
    json.dump(long, f, indent=2)
```

---

## 🎯 SUMMARY

This addition proves/disproves the hypothesis:
- **IF**: TF-IDF MRR >> Semantic on short queries, but similar on long queries
- **THEN**: TF-IDF bias is CONFIRMED (wins on keywords, not on understanding)

After regenerating ground truth with the new semantic-only prompt, this same analysis will show:
- TF-IDF MRR drops on short queries (fewer keywords to match)
- Semantic MRR rises on long queries (semantic actually tested)
- Hybrid RRF stays best (balanced approach)
