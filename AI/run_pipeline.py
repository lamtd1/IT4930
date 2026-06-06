import pandas as pd
import numpy as np
import pickle, json, time, re
import scipy.sparse as sp
from pathlib import Path
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb
from chromadb.config import Settings
import matplotlib.pyplot as plt
import seaborn as sns

# Setup paths
DATA_RAW = Path('data/raw/books.csv')
DATA_CLEAN = Path('data/processed/books_clean.csv')
EVAL_PATH = Path('data/eval/test_queries.json')
MODEL_PATH = Path('models')
CHROMA_PATH = Path('data/chroma_db')
REPORT_PATH = Path('reports')
FIGURE_PATH = Path('reports/figures')

for p in [DATA_CLEAN.parent, EVAL_PATH.parent, MODEL_PATH, CHROMA_PATH, REPORT_PATH, FIGURE_PATH]:
    p.mkdir(parents=True, exist_ok=True)

MODEL_COLORS = {
    'TF-IDF'   : '#6B8CBA',
    'BM25'     : '#F4A261',
    'Semantic' : '#2A9D8F',
    'Hybrid'   : '#E76F51',
    'Reranking': '#8338EC',
}

# --- 1. PREPROCESSING ---
print("\n--- 1. PREPROCESSING ---")
df = pd.read_csv(DATA_RAW)
df = df.dropna(subset=['description', 'isbn13'])

# Lọc mô tả boilerplate public-domain
BOILERPLATE = [
    "this work has been selected by scholars",
    "this is a reproduction of",
    "we appreciate your understanding of the imperfections",
]
_low = df["description"].str.lower()
is_boiler = _low.apply(lambda s: any(p in s for p in BOILERPLATE))
df = df[~is_boiler]

# Keep first occurrence of isbn13
df = df.drop_duplicates(subset=['isbn13'], keep='first')

# Khử trùng lặp edition (tác phẩm) theo title + author
_dlen = df["description"].str.split().str.len()
_key = df["title"].str.lower().str.strip() + "::" + df["authors"].str.lower().str.strip()
df = (
    df.assign(_dlen=_dlen, _key=_key)
      .sort_values("_dlen", ascending=False)
      .drop_duplicates("_key", keep="first")
      .drop(columns=["_dlen", "_key"])
      .sort_index()
)

# Đổi 0 thành NaN (Google Books dùng 0 làm ký hiệu "không rõ số trang")
df['num_pages'] = df['num_pages'].replace(0, pd.NA)

mask_pages = (df['num_pages'].isna() | ((df['num_pages'] >= 10) & (df['num_pages'] <= 1500)))
df = df[mask_pages]

mask_year = (df['published_year'].isna() | ((df['published_year'] >= 1800) & (df['published_year'] <= 2026)))
df = df[mask_year]

df['thumbnail'] = df['thumbnail'].fillna('https://via.placeholder.com/128x192.png?text=No+Cover')
df['average_rating'] = df['average_rating'].fillna(df['average_rating'].median())
df['categories'] = df['categories'].fillna('Unknown')
df['authors'] = df['authors'].fillna('Unknown')
df['num_pages'] = df['num_pages'].fillna(df['num_pages'].median())
df['published_year'] = df['published_year'].fillna(df['published_year'].median()).astype(int)

df['description_length'] = df['description'].str.split().str.len()
df['book_age'] = 2026 - df['published_year']
df['tag_clean'] = df['categories'].str.lower().str.strip()

def clean_text(text):
    if not isinstance(text, str): return ''
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

df['description'] = df['description'].apply(clean_text)
df['description_length'] = df['description'].str.split().str.len()
df = df[df['description_length'] >= 10].reset_index(drop=True)
df['isbn13'] = df['isbn13'].astype(str)
df.to_csv(DATA_CLEAN, index=False)
print(f"Cleaned data saved: {len(df)} rows")


# --- 2. EVALUATION QUERIES ---
print("\n--- 2. PREPARING QUERIES ---")
TEST_QUERIES = [
    {"query": "a heartbreaking story about family secrets in rural America", "relevant_categories": ["Fiction", "Literary Fiction", "Family & Relationships"]},
    {"query": "coming of age story with complex friendships", "relevant_categories": ["Fiction", "Young Adult Fiction", "Coming of Age"]},
    {"query": "a novel about identity and belonging in a foreign country", "relevant_categories": ["Fiction", "Literary Fiction", "Cultural"]},
    {"query": "interconnected stories about love and loss in a small town", "relevant_categories": ["Fiction", "Short Stories", "Literary Fiction"]},
    {"query": "a story about grief and moving on after tragedy", "relevant_categories": ["Fiction", "Literary Fiction", "Family & Relationships"]},
    {"query": "a thriller set in Japan with a detective protagonist", "relevant_categories": ["Mystery & Detective", "Thriller", "Fiction", "Crime"]},
    {"query": "psychological thriller about a woman who cannot trust her own memory", "relevant_categories": ["Thriller", "Mystery & Detective", "Psychological Fiction"]},
    {"query": "detective investigating a murder in a locked room", "relevant_categories": ["Mystery & Detective", "Crime", "Fiction"]},
    {"query": "spy novel set during the Cold War", "relevant_categories": ["Thriller", "Spy Stories", "Fiction", "Historical Fiction"]},
    {"query": "a crime novel with an unreliable narrator", "relevant_categories": ["Mystery & Detective", "Crime", "Thriller"]},
    {"query": "humanity's first contact with an alien civilization", "relevant_categories": ["Science Fiction", "Fiction"]},
    {"query": "dystopian society controlled by an authoritarian government", "relevant_categories": ["Science Fiction", "Dystopian", "Fiction"]},
    {"query": "a space opera with epic battles across multiple planets", "relevant_categories": ["Science Fiction", "Fiction"]},
    {"query": "artificial intelligence becomes sentient and questions its existence", "relevant_categories": ["Science Fiction", "Fiction", "Technology"]},
    {"query": "time travel causing unintended consequences in the past", "relevant_categories": ["Science Fiction", "Fiction", "Time Travel"]},
    {"query": "epic fantasy with magic systems and a chosen hero", "relevant_categories": ["Fantasy", "Fiction", "Epic Fantasy"]},
    {"query": "a world where dragons and humans coexist", "relevant_categories": ["Fantasy", "Fiction"]},
    {"query": "dark fantasy with morally ambiguous characters", "relevant_categories": ["Fantasy", "Dark Fantasy", "Fiction"]},
    {"query": "fairy tale retelling from the villain's perspective", "relevant_categories": ["Fantasy", "Fiction", "Fairy Tales"]},
    {"query": "urban fantasy set in modern day New York", "relevant_categories": ["Fantasy", "Urban Fantasy", "Fiction"]},
    {"query": "a slow burn romance between rivals forced to work together", "relevant_categories": ["Romance", "Fiction", "Love Stories"]},
    {"query": "historical romance set in Victorian England", "relevant_categories": ["Romance", "Historical Fiction", "Fiction"]},
    {"query": "second chance romance between childhood sweethearts", "relevant_categories": ["Romance", "Fiction", "Love Stories"]},
    {"query": "forbidden love story with a tragic ending", "relevant_categories": ["Romance", "Fiction", "Love Stories"]},
    {"query": "supernatural horror involving an ancient evil awakening", "relevant_categories": ["Horror", "Fiction", "Supernatural"]},
    {"query": "ghost story in an old haunted mansion", "relevant_categories": ["Horror", "Fiction", "Ghost Stories"]},
    {"query": "psychological horror where protagonist loses grip on reality", "relevant_categories": ["Horror", "Fiction", "Psychological Fiction"]},
    {"query": "a story set during World War II from a civilian perspective", "relevant_categories": ["Historical Fiction", "Fiction", "War Stories"]},
    {"query": "life in ancient Rome told through multiple characters", "relevant_categories": ["Historical Fiction", "Fiction"]},
    {"query": "a novel about the American Civil War and its aftermath", "relevant_categories": ["Historical Fiction", "Fiction", "War Stories"]},
    {"query": "how habits shape our daily lives and how to change them", "relevant_categories": ["Self-Help", "Psychology", "Personal Development"]},
    {"query": "leadership lessons from successful business executives", "relevant_categories": ["Business & Economics", "Leadership", "Management"]},
    {"query": "the science of motivation and achieving long-term goals", "relevant_categories": ["Self-Help", "Psychology", "Personal Development"]},
    {"query": "mindfulness and meditation for reducing stress and anxiety", "relevant_categories": ["Self-Help", "Health & Fitness", "Psychology"]},
    {"query": "biography of a scientist who changed our understanding of the universe", "relevant_categories": ["Biography & Autobiography", "Science"]},
    {"query": "a memoir about overcoming addiction and rebuilding life", "relevant_categories": ["Biography & Autobiography", "Self-Help", "Health"]},
    {"query": "the rise and fall of a powerful political empire", "relevant_categories": ["History", "Political Science", "Biography & Autobiography"]},
    {"query": "a young wizard discovering their magical powers", "relevant_categories": ["Juvenile Fiction", "Fantasy", "Young Adult Fiction"]},
    {"query": "a teenager dealing with bullying and finding their voice", "relevant_categories": ["Young Adult Fiction", "Juvenile Fiction"]},
    {"query": "a joyful story about unlikely friendships overcoming differences", "relevant_categories": ["Fiction", "Family & Relationships"]},
    {"query": "a deeply sad story about death and remembrance", "relevant_categories": ["Fiction", "Literary Fiction", "Family & Relationships"]},
    {"query": "an angry political narrative about social injustice", "relevant_categories": ["Political Science", "Social Science", "Fiction"]},
    {"query": "a fearful survival story in extreme wilderness conditions", "relevant_categories": ["Fiction", "Adventure", "Survival"]},
    {"query": "a philosophical novel questioning the meaning of existence", "relevant_categories": ["Philosophy", "Fiction", "Literary Fiction"]},
    {"query": "technology and ethics in a near-future surveillance state", "relevant_categories": ["Science Fiction", "Technology", "Political Science"]},
    {"query": "a road trip story about self-discovery and freedom", "relevant_categories": ["Fiction", "Travel", "Literary Fiction"]},
    {"query": "an ensemble cast of characters connected by a single event", "relevant_categories": ["Fiction", "Literary Fiction"]},
    {"query": "nature writing about the relationship between humans and wilderness", "relevant_categories": ["Nature", "Travel", "Science", "Biography & Autobiography"]},
    {"query": "a guide to personal finance and investing for beginners", "relevant_categories": ["Business & Economics", "Finance", "Self-Help"]},
    {"query": "a cookbook with traditional recipes from around the world", "relevant_categories": ["Cooking", "Food", "Non-Fiction"]}
]
with open(EVAL_PATH, 'w') as f:
    json.dump(TEST_QUERIES, f, indent=2)


# --- 3. BUILD MODELS ---
print("\n--- 3. BUILDING MODELS ---")
print("Building TF-IDF...")
vectorizer = TfidfVectorizer(max_features=15000, ngram_range=(1, 2), sublinear_tf=True, min_df=2, stop_words='english')
tfidf_matrix = vectorizer.fit_transform(df['description'])
with open(MODEL_PATH / 'tfidf_vectorizer.pkl', 'wb') as f: pickle.dump(vectorizer, f)
sp.save_npz(MODEL_PATH / 'tfidf_matrix.npz', tfidf_matrix)

print("Building BM25...")
corpus_tokenized = [desc.lower().split() for desc in df['description']]
bm25 = BM25Okapi(corpus_tokenized, k1=1.5, b=0.75)
with open(MODEL_PATH / 'bm25_index.pkl', 'wb') as f: pickle.dump(bm25, f)

print("Building BGE-small + ChromaDB...")
bi_encoder = SentenceTransformer('BAAI/bge-small-en-v1.5')
embeddings = bi_encoder.encode(df['description'].tolist(), batch_size=64, show_progress_bar=True, normalize_embeddings=True)

chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH), settings=Settings(anonymized_telemetry=False))
try:
    chroma_client.delete_collection('books')
except Exception:
    pass
collection = chroma_client.create_collection(name='books', metadata={'hnsw:space': 'cosine'})

metadatas = [
    {
        'title': str(row['title']),
        'authors': str(row['authors']),
        'categories': str(row['categories']),
        'thumbnail': str(row['thumbnail']),
        'average_rating': float(row['average_rating']),
        'published_year': int(row['published_year']),
    } for _, row in df.iterrows()
]
ids = df['isbn13'].tolist()

BATCH_SIZE = 500
for start in range(0, len(df), BATCH_SIZE):
    end = min(start + BATCH_SIZE, len(df))
    collection.upsert(ids=ids[start:end], embeddings=embeddings[start:end].tolist(), documents=df['description'].tolist()[start:end], metadatas=metadatas[start:end])

print("Loading Cross-Encoder...")
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)


# --- 4. SEARCH & EVALUATION FUNCTIONS ---
print("\n--- 4. EVALUATING MODELS ---")
BGE_PREFIX = 'Represent this sentence for searching relevant passages: '

def search_tfidf(query, top_k=10):
    q_vec = vectorizer.transform([query])
    scores = cosine_similarity(q_vec, tfidf_matrix).flatten()
    idx = np.argsort(scores)[::-1][:top_k]
    res = df.iloc[idx].copy()
    res['score'] = scores[idx]
    return res.reset_index(drop=True)

def search_bm25(query, top_k=10):
    scores = bm25.get_scores(query.lower().split())
    idx = np.argsort(scores)[::-1][:top_k]
    res = df.iloc[idx].copy()
    res['score'] = scores[idx]
    return res.reset_index(drop=True)

def search_semantic(query, top_k=10):
    q_emb = bi_encoder.encode([BGE_PREFIX + query], normalize_embeddings=True)
    results = collection.query(query_embeddings=q_emb.tolist(), n_results=top_k, include=['metadatas', 'distances'])
    rows = [{'isbn13': results['ids'][0][i], 'categories': results['metadatas'][0][i].get('categories', '')} for i in range(len(results['ids'][0]))]
    return pd.DataFrame(rows)

def search_hybrid(query, top_k=10, candidate_pool=50):
    bm25_res = search_bm25(query, top_k=candidate_pool)
    dense_res = search_semantic(query, top_k=candidate_pool)
    
    rrf_scores = defaultdict(float)
    for rank, doc_id in enumerate(bm25_res['isbn13']):
        rrf_scores[doc_id] += 1.0 / (60 + rank + 1)
    for rank, doc_id in enumerate(dense_res['isbn13']):
        rrf_scores[doc_id] += 1.0 / (60 + rank + 1)
        
    top_ids = [doc_id for doc_id, _ in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]]
    subset = df[df['isbn13'].isin(top_ids)].copy()
    order = {isbn: i for i, isbn in enumerate(top_ids)}
    subset['_order'] = subset['isbn13'].map(order)
    return subset.sort_values('_order').drop(columns='_order').reset_index(drop=True)

def search_reranking(query, top_k=10, candidate_pool=20):
    q_emb = bi_encoder.encode([BGE_PREFIX + query], normalize_embeddings=True)
    results = collection.query(query_embeddings=q_emb.tolist(), n_results=candidate_pool, include=['documents', 'metadatas'])
    
    candidates = []
    for i in range(len(results['ids'][0])):
        candidates.append({'isbn13': results['ids'][0][i], 'description': results['documents'][0][i], 'categories': results['metadatas'][0][i].get('categories', '')})
    df_cand = pd.DataFrame(candidates)
    
    pairs = [(query, desc) for desc in df_cand['description']]
    scores = cross_encoder.predict(pairs, show_progress_bar=False)
    df_cand['rerank_score'] = scores
    return df_cand.sort_values('rerank_score', ascending=False).head(top_k).reset_index(drop=True)


def is_relevant(book_category, relevant_categories):
    if not isinstance(book_category, str): return False
    bc = book_category.lower()
    return any(rc.lower() in bc or bc in rc.lower() for rc in relevant_categories)

def precision_at_k(results_df, relevant_cats, k):
    hits = results_df.head(k)['categories'].apply(lambda c: is_relevant(c, relevant_cats)).sum()
    return hits / k

def mrr(results_df, relevant_cats, max_k=10):
    for i, row in results_df.head(max_k).iterrows():
        if is_relevant(row['categories'], relevant_cats):
            return 1.0 / (i + 1)
    return 0.0


search_fns = {
    'TF-IDF': search_tfidf,
    'BM25': search_bm25,
    'Semantic': search_semantic,
    'Hybrid': search_hybrid,
    'Reranking': search_reranking
}

eval_records = []
speed_results = {}

for model_name, fn in search_fns.items():
    print(f"Evaluating {model_name}...")
    t0 = time.time()
    for q in TEST_QUERIES:
        res = fn(q['query'], top_k=10)
        p5 = precision_at_k(res, q['relevant_categories'], 5)
        p10 = precision_at_k(res, q['relevant_categories'], 10)
        m = mrr(res, q['relevant_categories'])
        eval_records.append({'model': model_name, 'query': q['query'], 'genres': ', '.join(q['relevant_categories']), 'P@5': p5, 'P@10': p10, 'MRR': m})
    elapsed_ms = (time.time() - t0) * 1000 / len(TEST_QUERIES)
    speed_results[model_name] = round(elapsed_ms, 1)

df_eval = pd.DataFrame(eval_records)
summary = df_eval.groupby('model')[['P@5', 'P@10', 'MRR']].mean().round(4).reindex(list(search_fns.keys()))
summary['Latency (ms)'] = [speed_results[m] for m in summary.index]
print("\n=== FINAL RESULTS ===")
print(summary)


# --- 5. PLOTTING ---
print("\n--- 5. GENERATING CHARTS ---")
x = np.arange(len(summary))
width = 0.25

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(x - width, summary['P@5'], width, label='P@5', color=[MODEL_COLORS[m] for m in summary.index], alpha=0.9)
ax.bar(x, summary['P@10'], width, label='P@10', color=[MODEL_COLORS[m] for m in summary.index], alpha=0.6)
ax.bar(x + width, summary['MRR'], width, label='MRR', color=[MODEL_COLORS[m] for m in summary.index], alpha=0.3, hatch='//')
ax.set_xticks(x)
ax.set_xticklabels(summary.index)
ax.set_title('Retrieval Model Comparison (50 queries)')
ax.legend(loc='upper left')
plt.tight_layout()
plt.savefig(FIGURE_PATH / 'eval_precision_bar.png')

fig, ax = plt.subplots(figsize=(8, 5))
for m in summary.index:
    ax.scatter(summary.loc[m, 'Latency (ms)'], summary.loc[m, 'P@5'], s=200, color=MODEL_COLORS[m], label=m)
ax.set_xscale('log')
ax.set_xlabel('Latency (ms)')
ax.set_ylabel('P@5')
ax.set_title('Quality vs Latency')
ax.legend()
plt.tight_layout()
plt.savefig(FIGURE_PATH / 'eval_latency_quality.png')

final_report = {
    'results': summary.to_dict(orient='index'),
    'per_query': df_eval.to_dict(orient='records')
}
with open(REPORT_PATH / 'evaluation_final.json', 'w') as f:
    json.dump(final_report, f, indent=2)

print("\nPipeline Complete!")
