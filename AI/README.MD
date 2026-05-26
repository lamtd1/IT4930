# Semantic Book Recommender

This project implements a semantic book recommender system comparing Sparse (TF-IDF, BM25) and Dense (BGE-small, Reranking) retrieval models.

## 1. Environment Setup

First, ensure you have Anaconda or Miniconda installed. Create and activate a new environment:

```bash
conda create -n DATA python=3.10 -y
conda activate DATA
```

Install the required packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 2. Quick Start: Run the Full Pipeline

You can run the entire ML pipeline from end-to-end (data preprocessing, index building, embedding extraction, and evaluation benchmark) using the `run_pipeline.py` script.

> **Note:** The script will automatically download the required transformer models (`BAAI/bge-small-en-v1.5` and `cross-encoder/ms-marco-MiniLM-L-6-v2`) on the first run.

```bash
# Make sure you are in the project root directory
conda activate DATA
python run_pipeline.py
```

### What does the pipeline do?
1. Cleans raw data in `data/raw/books.csv` and outputs `data/processed/books_clean.csv`.
2. Generates test queries and saves them to `data/eval/test_queries.json`.
3. Builds **TF-IDF** and **BM25** models and saves them to `models/`.
4. Extracts dense embeddings using **BGE-small** and builds a vector store in `data/chroma_db/`.
5. Evaluates 5 approaches: **TF-IDF**, **BM25**, **Semantic (Dense)**, **Hybrid RRF**, and **Cross-Encoder Reranking**.
6. Outputs the final benchmark to the console, saves it to `reports/evaluation_final.json`, and generates visualizations in `reports/figures/`.