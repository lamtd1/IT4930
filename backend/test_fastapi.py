"""Kiểm tra nhanh các endpoint API sau khi cập nhật."""
from fastapi.testclient import TestClient
import sys, json

print("Khởi động TestClient...")
from main import app

with TestClient(app) as client:
    # 1. /health
    r = client.get("/health")
    print(f"\n1. /health → {r.status_code}")
    print(json.dumps(r.json(), indent=2))

    # 2. /stats
    r = client.get("/stats")
    print(f"\n2. /stats → {r.status_code}")
    print(json.dumps(r.json(), indent=2))

    # 3. /search
    r = client.post("/search", json={"query": "lonely person searching for meaning", "top_k": 3, "method": "tfidf"})
    print(f"\n3. /search → {r.status_code}")
    data = r.json()
    print(f"   total_results: {data['total_results']}, query_time_ms: {data['query_time_ms']}")
    for b in data['results']:
        print(f"   - {b['title']} (rating={b.get('average_rating')}, score={b['similarity_score']})")

    # 4. /evaluation
    r = client.get("/evaluation")
    print(f"\n4. /evaluation → {r.status_code}")
    ev = r.json()
    print(f"   models: {[m['method'] for m in ev['models']]}")
    print(f"   by_genre: {[g['genre'] for g in ev.get('by_genre', [])]}")
    vocab = ev.get('vocabulary_mismatch_demo', [])
    print(f"   vocab_demo: {len(vocab)} items")
    for v in vocab[:2]:
        print(f"     query: '{v['query'][:50]}'")
        print(f"     semantic: {v['semantic_top1']['title'] if v.get('semantic_top1') else 'None'}")

print("\n✅ Tất cả kiểm tra hoàn tất!")
