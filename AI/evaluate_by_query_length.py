"""
Evaluate retrievers on SHORT vs LONG queries separately.

This splits the evaluation to see which models perform best on:
- Short keyword-like queries (≤3 words) → TF-IDF should excel
- Long semantic queries (>3 words) → Semantic models should excel
"""

import json
import logging
from pathlib import Path

import pandas as pd

from src.config.settings import get_settings
from src.evaluation.evaluator import Evaluator
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.hybrid_rrf_retriever import HybridRRFRetriever
from src.retrieval.rerank_retriever import RerankRetriever
from src.retrieval.tfidf_retriever import TFIDFRetriever
from src.utils.text_utils import clean_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_qrels_split(qrel_path: str):
    """Load and split qrels into short and long queries."""
    with open(qrel_path, 'r') as f:
        qrels = json.load(f)
    
    short = []
    long = []
    for q in qrels:
        if len(q['query'].split()) <= 3:
            short.append(q)
        else:
            long.append(q)
    
    return short, long

def load_dataframe(settings):
    """Load and clean the books dataset."""
    dataset_path = Path(settings.dataset_path)
    df = pd.read_csv(dataset_path, dtype={"isbn13": str})
    df = df.dropna(subset=["description", "isbn13"])
    df = df.drop_duplicates(subset=["isbn13"], keep="first")

    # Capping corpus cap removed so query length evaluation always runs on the full dataset

    df["description"] = df["description"].apply(lambda t: clean_text(str(t)))
    df = df[df["description"].str.split().str.len() >= 10].reset_index(drop=True)
    df["isbn13"] = df["isbn13"].astype(str)
    for col in ["title", "authors", "categories", "thumbnail"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")
    return df

def serialize_results(results_dict):
    """Convert EvaluationResult objects to serializable dicts."""
    serialized = {}
    for name, result in results_dict.items():
        serialized[name] = {
            "precision_at_5": float(result.precision_at_5),
            "precision_at_10": float(result.precision_at_10),
            "recall_at_5": float(result.recall_at_5),
            "recall_at_10": float(result.recall_at_10),
            "mrr": float(result.mrr),
            "ndcg_at_10": float(result.ndcg_at_10),
            "map_score": float(result.map_score),
            "latency_ms": float(result.latency_ms),
        }
    return serialized

def main():
    settings = get_settings()
    
    logger.info("Loading data...")
    df = load_dataframe(settings)
    
    logger.info("Loading retrievers...")
    tfidf = TFIDFRetriever.load(
        model_path=Path(settings.tfidf_model_path),
        matrix_path=Path(settings.tfidf_matrix_path),
        df=df,
    )
    bm25 = BM25Retriever.load(
        index_path=Path(settings.bm25_index_path),
        df=df,
    )
    dense = DenseRetriever.load(
        chroma_path=Path(settings.chroma_path),
        embedding_model=settings.embedding_model,
        collection_name=settings.chroma_collection_name,
    )
    
    hybrid = HybridRRFRetriever(
        bm25_retriever=bm25,
        dense_retriever=dense,
        candidate_pool=settings.hybrid_candidate_pool,
        rrf_k=settings.rrf_k,
    )
    
    rerank = RerankRetriever(
        dense_retriever=dense,
        rerank_model=settings.rerank_model,
        candidate_pool=settings.rerank_candidate_pool,
    )
    
    retrievers = {
        "tfidf": tfidf,
        "bm25": bm25,
        "dense": dense,
        "hybrid_rrf": hybrid,
        "rerank": rerank,
    }
    
    # Load qrels splits
    short_qrels, long_qrels = load_qrels_split("data/eval/qrels.json")
    
    logger.info(f"\nEvaluating on SHORT queries ({len(short_qrels)} queries ≤3 words)")
    logger.info("=" * 70)
    
    evaluator_short = Evaluator(
        retrievers=retrievers,
        qrels=short_qrels,
        settings=settings,
    )
    short_results = evaluator_short.run()
    short_results_dict = serialize_results(short_results.results)
    
    logger.info(f"\nEvaluating on LONG queries ({len(long_qrels)} queries >3 words)")
    logger.info("=" * 70)
    
    evaluator_long = Evaluator(
        retrievers=retrievers,
        qrels=long_qrels,
        settings=settings,
    )
    long_results = evaluator_long.run()
    long_results_dict = serialize_results(long_results.results)
    
    # Save results
    output = {
        "short_queries": {
            "count": len(short_qrels),
            "description": "≤3 words (keyword-like)",
            "results": short_results_dict,
        },
        "long_queries": {
            "count": len(long_qrels),
            "description": ">3 words (semantic)",
            "results": long_results_dict,
        },
    }
    
    with open("data/eval/evaluation_by_query_length.json", "w") as f:
        json.dump(output, f, indent=2)
    
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY - MODEL PERFORMANCE BY QUERY LENGTH")
    logger.info("=" * 70)
    
    for split_name, split_data in [("SHORT QUERIES", output["short_queries"]), 
                                    ("LONG QUERIES", output["long_queries"])]:
        logger.info(f"\n{split_name} ({split_data['count']} queries)")
        results = split_data['results']
        
        mrr_scores = {name: metrics['mrr'] for name, metrics in results.items()}
        sorted_models = sorted(mrr_scores.items(), key=lambda x: x[1], reverse=True)
        
        for i, (model, mrr) in enumerate(sorted_models, 1):
            ndcg = results[model]['ndcg_at_10']
            map_score = results[model]['map_score']
            logger.info(f"  {i}. {model:15} | MRR={mrr:.4f} | NDCG@10={ndcg:.4f} | MAP={map_score:.4f}")
    
    logger.info("\n✓ Saved results to data/eval/evaluation_by_query_length.json")

if __name__ == "__main__":
    main()
