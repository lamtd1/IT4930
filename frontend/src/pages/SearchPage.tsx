import React, { useState, useEffect, useCallback, useRef } from 'react';
import { METHODS, EMOTIONS, EMOTION_META, EXAMPLE_QUERIES, apiSearch, apiStats } from '../services/api';
import { METHOD_EXPLAIN } from '../components/common/Popover';
import { CoverImage } from '../components/common/CoverImage';
import { StarRating, EmotionBadge, MethodChip } from '../components/common/Badge';
import { Icon } from '../components/common/Icon';
import { Button } from '../components/common/Button';
import { Spinner, EmptyState, ErrorState } from '../components/common/StateViews';
import { useAsync } from '../hooks/useAsync';
import type { BookResult } from '../services/types';

interface BookCardProps {
  book: BookResult;
  method: string;
  onOpen: (book: BookResult) => void;
  index?: number;
}

export const BookCard: React.FC<BookCardProps> = ({ book, method, onOpen, index = 0 }) => {
  const [hover, setHover] = useState(false);
  return (
    <button onClick={() => onOpen({ ...book, _method: method })}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        textAlign: "left",
        border: "1px solid var(--line)",
        background: "var(--surface)",
        cursor: "pointer",
        borderRadius: "var(--r-lg)",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        fontFamily: "inherit",
        boxShadow: hover ? "var(--shadow-md)" : "var(--shadow-sm)",
        transform: hover ? "translateY(-3px)" : "none",
        transition: "transform .18s cubic-bezier(.2,.7,.2,1), box-shadow .18s",
        animation: `fadeUp .4s ${index * 0.03}s both`
      }}
    >
      <div style={{ position: "relative" }}>
        <CoverImage book={book} size="card" />
        {book.similarity_score != null && (
          <span className="mono" style={{
            position: "absolute",
            top: 8,
            right: 8,
            fontSize: 11,
            fontWeight: 600,
            padding: "3px 7px",
            borderRadius: 6,
            background: "oklch(1 0 0 / 0.92)",
            color: "var(--accent-ink)",
            border: "1px solid var(--accent-line)",
            boxShadow: "var(--shadow-sm)"
          }}>{book.similarity_score.toFixed(2)}</span>
        )}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
        <div className="serif" style={{
          fontSize: 16.5,
          fontWeight: 600,
          lineHeight: 1.2,
          letterSpacing: "-0.01em",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden"
        }}>{book.title}</div>
        <div style={{ fontSize: 12.5, color: "var(--ink-mute)" }}>{book.authors} · <span className="mono">{book.published_year}</span></div>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginTop: 1 }}>
          <StarRating value={book.average_rating} size={12} />
          <span className="mono" style={{ fontSize: 11.5, color: "var(--ink-mute)" }}>{book.average_rating.toFixed(2)}</span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: "auto", paddingTop: 6 }}>
          {book.top_emotions.map(em => <EmotionBadge key={em} emotion={em} />)}
        </div>
      </div>
    </button>
  );
};

export const SkeletonGrid: React.FC<{ n?: number }> = ({ n = 10 }) => {
  return (
    <div className="results-grid">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} style={{ border: "1px solid var(--line)", background: "var(--surface)", borderRadius: "var(--r-lg)", padding: 14 }}>
          <div className="skel" style={{ width: "100%", aspectRatio: "2 / 3" }} />
          <div className="skel" style={{ height: 15, width: "85%", marginTop: 12 }} />
          <div className="skel" style={{ height: 12, width: "60%", marginTop: 8 }} />
          <div className="skel" style={{ height: 18, width: "45%", marginTop: 12, borderRadius: 99 }} />
        </div>
      ))}
    </div>
  );
};

interface MethodSelectorProps {
  value: string;
  onChange: (method: string) => void;
}

const MethodSelector: React.FC<MethodSelectorProps> = ({ value, onChange }) => {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {METHODS.map(m => {
        const active = value === m.id;
        return (
          <button key={m.id} onClick={() => onChange(m.id)} title={METHOD_EXPLAIN[m.id]}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 13px",
              cursor: "pointer",
              borderRadius: "var(--r-md)",
              fontFamily: "inherit",
              fontSize: 13,
              fontWeight: 600,
              border: active ? "1px solid var(--accent-line)" : "1px solid var(--line)",
              background: active ? "var(--accent-wash)" : "var(--surface)",
              color: active ? "var(--accent-ink)" : "var(--ink-soft)",
              transition: "all .14s"
            }}
          >
            <span style={{ width: 9, height: 9, borderRadius: 3, background: m.color }} />
            {m.label}
          </button>
        );
      })}
    </div>
  );
};

interface EmotionFilterProps {
  value: string[];
  onChange: (emotions: string[]) => void;
}

const EmotionFilter: React.FC<EmotionFilterProps> = ({ value, onChange }) => {
  const toggle = (em: string) => onChange(value.includes(em) ? value.filter(x => x !== em) : [...value, em]);
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
      {EMOTIONS.map(em => {
        const m = EMOTION_META[em];
        if (!m) return null;
        const active = value.includes(em);
        return (
          <button key={em} onClick={() => toggle(em)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "5px 11px",
              cursor: "pointer",
              borderRadius: 99,
              fontFamily: "inherit",
              fontSize: 12.5,
              fontWeight: 600,
              transition: "all .14s",
              border: active ? `1px solid ${m.color}` : "1px solid var(--line)",
              background: active ? "var(--paper-2)" : "var(--surface)",
              color: active ? "var(--ink)" : "var(--ink-mute)"
            }}
          >
            <span style={{ width: 9, height: 9, borderRadius: 99, background: m.color, opacity: active ? 1 : 0.45 }} />
            {m.label}
          </button>
        );
      })}
    </div>
  );
};

interface FieldProps {
  label: string;
  children: React.ReactNode;
  hint?: string;
}

const Field: React.FC<FieldProps> = ({ label, children, hint }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".07em" }}>{label}</span>
        {hint && <span style={{ fontSize: 11.5, color: "var(--ink-faint)" }}>{hint}</span>}
      </div>
      {children}
    </div>
  );
};

interface ResultsHeaderProps {
  data?: any;
  committed: any;
  loading?: boolean;
  fetching?: boolean;
}

const ResultsHeader: React.FC<ResultsHeaderProps> = ({ data, committed, loading, fetching }) => {
  return (
    <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 16, marginBottom: 18, flexWrap: "wrap" }}>
      <div>
        <div style={{ fontSize: 13, color: "var(--ink-mute)" }}>Results for</div>
        <h2 className="serif" style={{ fontSize: 22, fontWeight: 600, margin: "2px 0 0", fontStyle: "italic" }}>"{committed.query}"</h2>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        {fetching && <Spinner size={15} />}
        {!loading && data && (
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 13, color: "var(--ink-soft)" }}>
            <MethodChip method={data.method_used} size="sm" />
            <span className="mono" style={{ color: "var(--ink-mute)" }}>{data.total_results} books · {data.query_time_ms}ms</span>
          </div>
        )}
      </div>
    </div>
  );
};

interface IdleStateProps {
  stats: any;
  onPick: (query: string) => void;
}

const IdleState: React.FC<IdleStateProps> = ({ stats, onPick }) => {
  return (
    <div style={{ animation: "fadeIn .4s" }}>
      <div style={{ textAlign: "center", maxWidth: 560, margin: "32px auto 36px" }}>
        <h1 className="serif" style={{ fontSize: 34, fontWeight: 600, lineHeight: 1.12, letterSpacing: "-0.015em", margin: 0 }}>
          Find your next read by <span style={{ fontStyle: "italic", color: "var(--accent-ink)" }}>what it feels like</span>
        </h1>
        <p style={{ fontSize: 15.5, color: "var(--ink-mute)", marginTop: 12, lineHeight: 1.55 }}>
          Search in plain language. Our semantic engine understands meaning, not just keywords — so "a heartbreaking story about family secrets" finds the right book even when those exact words never appear.
        </p>
      </div>

      {/* stats strip */}
      <div style={{
        display: "flex",
        justifyContent: "center",
        gap: 0,
        flexWrap: "wrap",
        border: "1px solid var(--line)",
        borderRadius: "var(--r-lg)",
        overflow: "hidden",
        maxWidth: 620,
        margin: "0 auto",
        background: "var(--surface)"
      }}>
        {stats.loading ? [0, 1, 2].map(i => <div key={i} style={{ flex: 1, padding: "18px 24px" }}><div className="skel" style={{ height: 28, width: "70%" }} /></div>)
          : stats.data && [
            { v: stats.data.total_books.toLocaleString(), l: "books indexed" },
            { v: stats.data.total_categories, l: "categories" },
            { v: stats.data.avg_rating ? stats.data.avg_rating.toFixed(2) : "4.11", l: "avg rating" },
          ].map((s, i) => (
            <div key={i} style={{
              flex: 1,
              minWidth: 140,
              padding: "18px 24px",
              textAlign: "center",
              borderLeft: i ? "1px solid var(--line)" : "none"
            }}>
              <div className="serif mono" style={{ fontSize: 26, fontWeight: 600 }}>{s.v}</div>
              <div className="mono" style={{ fontSize: 11, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".06em", marginTop: 2 }}>{s.l}</div>
            </div>
          ))}
      </div>

      <div style={{ maxWidth: 620, margin: "28px auto 0" }}>
        <div className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".07em", marginBottom: 10, textAlign: "center" }}>Start with an example</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {EXAMPLE_QUERIES.map(q => (
            <button key={q} onClick={() => onPick(q)} style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              padding: "13px 16px",
              borderRadius: "var(--r-md)",
              border: "1px solid var(--line)",
              background: "var(--surface)",
              cursor: "pointer",
              fontFamily: "var(--font-serif)",
              fontSize: 15,
              fontStyle: "italic",
              color: "var(--ink)",
              textAlign: "left",
              transition: "border-color .14s, background .14s"
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--accent-line)"; e.currentTarget.style.background = "var(--accent-wash)"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--line)"; e.currentTarget.style.background = "var(--surface)"; }}>
              "{q}" <Icon name="arrow" size={16} style={{ color: "var(--accent-ink)", flexShrink: 0 }} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

interface SearchPageProps {
  onOpenBook: (book: BookResult) => void;
}

export const SearchPage: React.FC<SearchPageProps> = ({ onOpenBook }) => {
  const [query, setQuery] = useState("");
  const [committed, setCommitted] = useState<{ query: string; method: string; emotions: string[]; topK: number } | null>(null);
  const [method, setMethod] = useState("semantic");
  const [emotions, setEmotions] = useState<string[]>([]);
  const [topK, setTopK] = useState(10);
  const inputRef = useRef<HTMLInputElement>(null);

  // Parse URL hash parameters on mount and hash change
  useEffect(() => {
    const parseHash = () => {
      const hash = window.location.hash || "";
      const qIdx = hash.indexOf("?");
      if (qIdx === -1) {
        // If route is just #/ without params, reset states
        if (hash === "#/" || hash === "#") {
          setQuery("");
          setCommitted(null);
          setMethod("semantic");
          setEmotions([]);
          setTopK(10);
        }
        return;
      }
      
      const params = new URLSearchParams(hash.slice(qIdx));
      const q = params.get("query") || "";
      const m = params.get("method") || "semantic";
      const ems = params.get("emotions") ? params.get("emotions")!.split(",") : [];
      const k = parseInt(params.get("topK") || "10", 10);

      setQuery(q);
      setMethod(m);
      setEmotions(ems);
      setTopK(k);

      if (q.trim()) {
        setCommitted({ query: q.trim(), method: m, emotions: ems, topK: k });
      } else {
        setCommitted(null);
      }
    };

    parseHash();
    window.addEventListener("hashchange", parseHash);
    return () => window.removeEventListener("hashchange", parseHash);
  }, []);

  // Update hash when search details change
  const updateHash = (q: string, m: string, ems: string[], k: number) => {
    const params = new URLSearchParams();
    if (q.trim()) params.set("query", q.trim());
    if (m !== "semantic") params.set("method", m);
    if (ems.length) params.set("emotions", ems.join(","));
    if (k !== 10) params.set("topK", k.toString());

    const pStr = params.toString();
    const newHash = pStr ? `#/?${pStr}` : "#/";

    if (window.location.hash !== newHash) {
      window.location.hash = newHash;
    }
  };

  const stats = useAsync(() => apiStats(), []);

  const search = useAsync(
    () => apiSearch({
      query: committed!.query,
      top_k: committed!.topK,
      method: committed!.method,
      filter_emotions: committed!.emotions.length ? committed!.emotions : null
    }),
    [
      committed && committed.query,
      committed && committed.method,
      committed && committed.topK,
      committed && (committed.emotions || []).join(",")
    ],
    { enabled: !!committed }
  );

  const submit = useCallback((q?: string) => {
    const qq = (q != null ? q : query).trim();
    if (!qq) return;
    if (q != null) setQuery(qq);
    setCommitted({ query: qq, method, emotions, topK });
    updateHash(qq, method, emotions, topK);
  }, [query, method, emotions, topK]);

  useEffect(() => {
    if (committed) {
      setCommitted(c => c ? { ...c, method, emotions, topK } : null);
      updateHash(committed.query, method, emotions, topK);
    }
  }, [method, emotions, topK]);

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => { if (e.key === "Enter") submit(); };

  return (
    <div style={{ maxWidth: "var(--maxw)", margin: "0 auto", padding: "28px 24px 80px", width: "100%" }}>
      {/* search panel */}
      <div style={{
        background: "var(--surface)",
        border: "1px solid var(--line)",
        borderRadius: "var(--r-lg)",
        padding: 22,
        boxShadow: "var(--shadow-sm)"
      }}>
        <div style={{ display: "flex", gap: 10, alignItems: "stretch", flexWrap: "wrap" }}>
          <div style={{ position: "relative", flex: 1, minWidth: 260 }}>
            <span style={{ position: "absolute", left: 15, top: "50%", transform: "translateY(-50%)", color: "var(--ink-faint)" }}><Icon name="search" size={19} /></span>
            <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)} onKeyDown={onKey}
              placeholder="Describe the book you're looking for — a mood, a theme, a feeling…"
              style={{
                width: "100%",
                height: 52,
                padding: "0 16px 0 46px",
                fontSize: 15.5,
                fontFamily: "var(--font-serif)",
                borderRadius: "var(--r-md)",
                border: "1px solid var(--line)",
                background: "var(--paper)",
                color: "var(--ink)",
                outline: "none"
              }}
              onFocus={e => e.target.style.borderColor = "var(--accent-line)"} onBlur={e => e.target.style.borderColor = "var(--line)"} />
          </div>
          <Button size="lg" icon="search" onClick={() => submit()} disabled={!query.trim()}>Search</Button>
        </div>

        {/* example chips */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "var(--ink-mute)" }}>Try:</span>
          {EXAMPLE_QUERIES.slice(0, 4).map(q => (
            <button key={q} onClick={() => submit(q)} style={{
              fontFamily: "var(--font-serif)",
              fontStyle: "italic",
              fontSize: 13,
              color: "var(--accent-ink)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: 0,
              borderBottom: "1px solid var(--accent-line)"
            }}>"{q}"</button>
          ))}
        </div>

        <div style={{ height: 1, background: "var(--line-soft)", margin: "20px 0" }} />

        {/* controls */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
          <Field label="Retrieval method" hint="how results are ranked">
            <MethodSelector value={method} onChange={setMethod} />
          </Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 24, alignItems: "start" }} className="search-lower">
            <Field label="Emotion filter" hint="optional · keep books that evoke these">
              <EmotionFilter value={emotions} onChange={setEmotions} />
            </Field>
            <Field label="Results">
              <div style={{ display: "inline-flex", background: "var(--paper-2)", borderRadius: "var(--r-md)", padding: 3, border: "1px solid var(--line)" }}>
                {[5, 10, 20].map(k => (
                  <button key={k} onClick={() => setTopK(k)} className="mono" style={{
                    border: "none",
                    cursor: "pointer",
                    padding: "7px 15px",
                    borderRadius: 6,
                    fontSize: 13,
                    fontWeight: 600,
                    background: topK === k ? "var(--surface)" : "transparent",
                    color: topK === k ? "var(--ink)" : "var(--ink-mute)",
                    boxShadow: topK === k ? "var(--shadow-sm)" : "none"
                  }}>{k}</button>
                ))}
              </div>
            </Field>
          </div>
        </div>
      </div>

      {/* results region */}
      <div style={{ marginTop: 28 }}>
        {!committed ? (
          <IdleState stats={stats} onPick={submit} />
        ) : search.loading ? (
          <>
            <ResultsHeader loading committed={committed} />
            <SkeletonGrid n={committed.topK} />
          </>
        ) : search.error ? (
          <ErrorState error={search.error} onRetry={search.refetch} />
        ) : !search.data ? (
          <>
            <ResultsHeader loading committed={committed} />
            <SkeletonGrid n={committed.topK} />
          </>
        ) : search.data.results.length === 0 ? (
          <EmptyState title="No books matched" body={`Nothing came back for "${committed.query}" with the current filters. Try removing an emotion filter or rephrasing.`}
            action={emotions.length ? <Button variant="outline" onClick={() => setEmotions([])}>Clear emotion filters</Button> : null} />
        ) : (
          <>
            <ResultsHeader data={search.data} committed={committed} fetching={search.fetching} />
            <div className="results-grid">
              {search.data.results.map((b, i) => (
                <BookCard key={b.isbn13} book={b} method={committed.method} index={i} onOpen={onOpenBook} />
              ))}
            </div>
          </>
        )}
      </div>

      <style>{`
        .results-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; }
        @media (max-width: 1080px){ .results-grid{ grid-template-columns: repeat(4,1fr); } }
        @media (max-width: 880px){ .results-grid{ grid-template-columns: repeat(3,1fr); } .search-lower{ grid-template-columns: 1fr !important; } }
        @media (max-width: 560px){ .results-grid{ grid-template-columns: repeat(2,1fr); } }
      `}</style>
    </div>
  );
};
