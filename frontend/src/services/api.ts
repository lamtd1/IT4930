import type {
  SearchRequest,
  SearchResponse,
  StatsResponse,
  EvaluationResponse,
  RetrievalMethod,
  EmotionMeta,
  Book,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE || '';

// ---------------------------------------------------------------------------
// Cấu hình tĩnh — metadata của 5 thuật toán tìm kiếm
// ---------------------------------------------------------------------------
export const METHODS: RetrievalMethod[] = [
  { id: "tfidf", label: "TF-IDF + Cosine", short: "TF-IDF", type: "Sparse", avgMs: 5, color: "var(--m-tfidf)" },
  { id: "bm25", label: "BM25", short: "BM25", type: "Sparse", avgMs: 10, color: "var(--m-bm25)" },
  { id: "semantic", label: "BGE-small + ChromaDB", short: "Semantic", type: "Dense", avgMs: 50, color: "var(--m-semantic)" },
  { id: "hybrid", label: "Hybrid RRF", short: "Hybrid", type: "Dense + Sparse", avgMs: 60, color: "var(--m-hybrid)" },
  { id: "reranking", label: "BGE + Reranking", short: "Reranking", type: "Dense + Rerank", avgMs: 200, color: "var(--m-reranking)" },
];

export const METHOD_MAP = Object.fromEntries(METHODS.map(m => [m.id, m]));

export const EMOTIONS = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"];

export const EMOTION_META: Record<string, EmotionMeta> = {
  joy: { label: "Joy", color: "oklch(0.80 0.085 85)" },
  sadness: { label: "Sadness", color: "oklch(0.62 0.068 250)" },
  anger: { label: "Anger", color: "oklch(0.60 0.105 28)" },
  fear: { label: "Fear", color: "oklch(0.56 0.072 300)" },
  surprise: { label: "Surprise", color: "oklch(0.71 0.092 55)" },
  disgust: { label: "Disgust", color: "oklch(0.63 0.075 135)" },
  neutral: { label: "Neutral", color: "oklch(0.70 0.012 70)" },
}

// ví dụ tìm kiếm thử nghiệm đặt trên giao diện
export const EXAMPLE_QUERIES = [
  "World Cup statistics",
  "history of soccer tournaments",
  "a chilling tale that keeps you up at night",
  "slow-burn romance with sharp banter",
];

// ---------------------------------------------------------------------------
// Helper xử lý lỗi HTTP
// ---------------------------------------------------------------------------
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      message = data.detail || data.message || message;
    } catch {
      // ignore parse errors
    }
    const err: any = new Error(message);
    err.code = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API calls — gọi trực tiếp backend FastAPI
// ---------------------------------------------------------------------------

/** Tìm kiếm sách bằng một trong 5 thuật toán */
export async function apiSearch(params: SearchRequest): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: params.query,
      top_k: params.top_k ?? 10,
      method: params.method ?? 'semantic',
    }),
  });
  return handleResponse<SearchResponse>(res);
}

/** Lấy thông tin chi tiết một quyển sách theo ISBN-13 */
export async function apiBook(isbn13: string): Promise<Book> {
  const res = await fetch(`${API_BASE}/books/${encodeURIComponent(isbn13)}`);
  return handleResponse<Book>(res);
}

/** Lấy thống kê tổng hợp của toàn bộ dataset */
export async function apiStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/stats`);
  return handleResponse<StatsResponse>(res);
}

/** Lấy kết quả đánh giá các thuật toán (metrics, by-genre, vocab mismatch demo) */
export async function apiEvaluation(): Promise<EvaluationResponse> {
  const res = await fetch(`${API_BASE}/evaluation`);
  return handleResponse<EvaluationResponse>(res);
}
