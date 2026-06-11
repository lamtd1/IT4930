"""Quick API test script."""
import json
import requests

BASE = "http://127.0.0.1:8000"

# Test search
print("=== POST /search (semantic) ===")
r = requests.post(f"{BASE}/search", json={
    "query": "a heartbreaking story about family secrets",
    "method": "semantic",
    "top_k": 5,
})
data = r.json()
print(f"Method: {data['method_used']}, Results: {data['total_results']}, Time: {data['query_time_ms']}ms")
for i, b in enumerate(data["results"]):
    print(f"  {i+1}. {b['title']} (score={b['similarity_score']}) emotions={b['top_emotions']}")

# Test TF-IDF
print("\n=== POST /search (tfidf) ===")
r = requests.post(f"{BASE}/search", json={
    "query": "a heartbreaking story about family secrets",
    "method": "tfidf",
    "top_k": 5,
})
data = r.json()
print(f"Method: {data['method_used']}, Results: {data['total_results']}, Time: {data['query_time_ms']}ms")
for i, b in enumerate(data["results"]):
    print(f"  {i+1}. {b['title']} (score={b['similarity_score']})")

# Test book detail
print("\n=== GET /books/9780002188319 ===")
r = requests.get(f"{BASE}/books/9780002188319")
book = r.json()
print(f"Title: {book['title']}")
print(f"Authors: {book['authors']}")
print(f"Emotions: {book['emotion_scores']}")
print(f"Top: {book['top_emotions']}")
