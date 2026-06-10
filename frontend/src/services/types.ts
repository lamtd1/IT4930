// ---------------------------------------------------------------------------
// Types phía Frontend — align 1-1 với Pydantic schemas ở backend
// ---------------------------------------------------------------------------

export interface Book {
  isbn13: string;
  title: string;
  authors: string;
  description: string;
  thumbnail: string | null;
  categories: string;
  published_year: number;
  average_rating: number;
  ratings_count: number;
  emotion_scores: Record<string, number>;
  top_emotions: string[];
  // Các trường chỉ có trong BookDetail (GET /books/{isbn13})
  tag_clean?: string | null;
  num_pages?: number | null;
  description_length?: number | null;
  book_age?: number | null;
}

export interface BookResult {
  isbn13: string;
  title: string;
  authors: string;
  description: string;
  thumbnail: string | null;
  categories: string;
  published_year: number;
  average_rating: number;
  ratings_count: number;
  top_emotions: string[];
  similarity_score: number;
  emotion_scores: Record<string, number> | null;
  _method?: string; // transient — gán phía FE để hiển thị
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  method?: string;
  filter_emotions?: string[] | null;
}

export interface SearchResponse {
  results: BookResult[];
  method_used: string;
  total_results: number;
  query_time_ms: number;
}

export interface StatsResponse {
  total_books: number;
  total_categories: number;
  avg_rating?: number;
  emotion_distribution: Record<string, number>;
}

export interface EvaluationModel {
  method: string;
  p_at_5: number;
  p_at_10: number;
  mrr: number;
  ndcg_at_10?: number | null;
  map_score?: number | null;
  ms_per_query: number;
}

export interface GenreScores {
  genre: string;
  scores: Record<string, number>;
}

export interface VocabMismatchBook {
  isbn13: string;
  title: string;
  authors: string;
  description: string;
  thumbnail: string | null;
  categories: string;
  published_year: number;
  top_emotions: string[];
  emotion_scores: Record<string, number>;
}

export interface VocabMismatchItem {
  query: string;
  tfidf_top1: VocabMismatchBook | null;
  semantic_top1: VocabMismatchBook | null;
}

export interface EvaluationResponse {
  models: EvaluationModel[];
  by_genre: GenreScores[];
  vocabulary_mismatch_demo: VocabMismatchItem[];
  meta?: Record<string, unknown> | null;
}

export interface RetrievalMethod {
  id: string;
  label: string;
  short: string;
  type: string;
  avgMs: number;
  color: string;
}

export interface EmotionMeta {
  label: string;
  color: string;
}
