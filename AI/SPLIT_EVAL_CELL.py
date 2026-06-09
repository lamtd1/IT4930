# 
# ============================================================================
# ADD THIS CELL AFTER CELL 5 (After "Kết quả Đánh giá & Báo cáo so sánh")
# ============================================================================
#

# %% MD
"""
## 6. So Sánh Performance Trên Query Ngắn vs Dài (Keyword vs Semantic)

Phân tích này chia qrels thành 2 nhóm để xem model nào thích hợp với loại query nào:
- SHORT QUERIES (≤3 từ): Keyword-like → TF-IDF sẽ xuất sắc
- LONG QUERIES (>3 từ): Semantic → Semantic models sẽ tốt hơn
"""

# %% CODE - Load split qrels và chạy evaluation riêng
import json

print("\n" + "="*80)
print("EVALUATING BY QUERY LENGTH (Short vs Long)")
print("="*80)

# Load split qrels từ files
qrels_path_short = Path(settings.eval_output_path) / "qrels_short_only.json"
qrels_path_long = Path(settings.eval_output_path) / "qrels_long_only.json"

if qrels_path_short.exists() and qrels_path_long.exists():
    print(f"✓ Loading qrels splits...")
    with open(qrels_path_short) as f:
        qrels_short = [__import__('src.schemas.benchmark', fromlist=['QrelItem']).QrelItem(**item) for item in json.load(f)]
    with open(qrels_path_long) as f:
        qrels_long = [__import__('src.schemas.benchmark', fromlist=['QrelItem']).QrelItem(**item) for item in json.load(f)]
    
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
    
    # Tạo bảng so sánh MRR
    print("\n" + "="*80)
    print("MRR COMPARISON BY QUERY TYPE")
    print("="*80)
    
    mrr_comparison = {}
    for retriever_name in eval_summary.results.keys():
        mrr_all = eval_summary.results[retriever_name].mrr
        mrr_short = eval_short.results[retriever_name].mrr
        mrr_long = eval_long.results[retriever_name].mrr
        
        mrr_comparison[retriever_name] = {
            "MRR (All)": mrr_all,
            "MRR (Short ≤3w)": mrr_short,
            "MRR (Long >3w)": mrr_long,
        }
    
    mrr_df = pd.DataFrame(mrr_comparison).T
    display(mrr_df)
    
    # Biểu đồ so sánh MRR
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(mrr_df))
    width = 0.25
    
    ax.bar(x - width, mrr_df["MRR (All)"], width, label="All Queries", color="#888888", alpha=0.8)
    ax.bar(x, mrr_df["MRR (Short ≤3w)"], width, label="Short Queries (≤3w, Keyword)", color="#FF6B6B", alpha=0.8)
    ax.bar(x + width, mrr_df["MRR (Long >3w)"], width, label="Long Queries (>3w, Semantic)", color="#4ECDC4", alpha=0.8)
    
    ax.set_xlabel("Retriever Model", fontweight='bold')
    ax.set_ylabel("MRR", fontweight='bold')
    ax.set_title("Model Performance by Query Type: Keyword vs Semantic", fontsize=14, fontweight='bold')
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
    print("DETAILED ANALYSIS - Which Model for Which Query Type?")
    print("="*80)
    
    print("\nSHORT QUERIES (≤3 words, Keyword-like):")
    print("  Expected winner: TF-IDF (keyword matching)")
    short_sorted = mrr_df["MRR (Short ≤3w)"].sort_values(ascending=False)
    for i, (model, score) in enumerate(short_sorted.items(), 1):
        print(f"  {i}. {model:15} MRR={score:.4f}")
    
    print("\nLONG QUERIES (>3 words, Semantic):")
    print("  Expected winner: Semantic/Dense (understanding meaning)")
    long_sorted = mrr_df["MRR (Long >3w)"].sort_values(ascending=False)
    for i, (model, score) in enumerate(long_sorted.items(), 1):
        print(f"  {i}. {model:15} MRR={score:.4f}")
    
    # Kiểm tra bias
    print("\n" + "="*80)
    print("BIAS CHECK - TF-IDF Advantage on Short Queries?")
    print("="*80)
    
    tfidf_short = mrr_df.loc["TF-IDF", "MRR (Short ≤3w)"]
    tfidf_long = mrr_df.loc["TF-IDF", "MRR (Long >3w)"]
    
    semantic_short = mrr_df.loc["Semantic", "MRR (Short ≤3w)"]
    semantic_long = mrr_df.loc["Semantic", "MRR (Long >3w)"]
    
    print(f"\nTF-IDF performance gap (Short - Long): {tfidf_short - tfidf_long:.4f}")
    print(f"Semantic performance gap (Short - Long): {semantic_short - semantic_long:.4f}")
    
    tfidf_dominance_short = tfidf_short - semantic_short
    tfidf_dominance_long = tfidf_long - semantic_long
    
    print(f"\nTF-IDF advantage on SHORT queries: {tfidf_dominance_short:+.4f}")
    print(f"TF-IDF advantage on LONG queries: {tfidf_dominance_long:+.4f}")
    
    if tfidf_dominance_short > tfidf_dominance_long:
        print(f"\n✓ CONFIRMED: TF-IDF is biased toward SHORT (keyword) queries")
        print(f"  Bias margin: {tfidf_dominance_short - tfidf_dominance_long:.4f}")
    else:
        print(f"\n✗ TF-IDF not significantly biased toward keyword queries")

else:
    print(f"⚠ Split qrels not found. Create them first:")
    print(f"  python3 << 'EOF'")
    print(f"  import json")
    print(f"  with open('data/eval/qrels.json') as f:")
    print(f"      qrels = json.load(f)")
    print(f"  short = [q for q in qrels if len(q['query'].split()) <= 3]")
    print(f"  long = [q for q in qrels if len(q['query'].split()) > 3]")
    print(f"  with open('data/eval/qrels_short_only.json', 'w') as f: json.dump(short, f, indent=2)")
    print(f"  with open('data/eval/qrels_long_only.json', 'w') as f: json.dump(long, f, indent=2)")
    print(f"  EOF")
