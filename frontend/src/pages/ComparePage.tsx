import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { METHODS, METHOD_MAP, EXAMPLE_QUERIES, apiSearch } from '../services/api';
import { CoverImage } from '../components/common/CoverImage';
import { Icon } from '../components/common/Icon';
import { Button } from '../components/common/Button';
import { EmptyState } from '../components/common/StateViews';
import { useAsync } from '../hooks/useAsync';
import type { BookResult } from '../services/types';

interface CompareRowProps {
  book: BookResult;
  rank: number;
  method: string;
  onOpen: (book: BookResult) => void;
}

const CompareRow: React.FC<CompareRowProps> = ({ book, rank, method, onOpen }) => {
  const [hover, setHover] = useState(false);
  return (
    <button onClick={() => onOpen({ ...book, _method: method })}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        display: "grid",
        gridTemplateColumns: "18px 34px 1fr",
        gap: 9,
        alignItems: "center",
        width: "100%",
        textAlign: "left",
        border: "none",
        borderRadius: "var(--r-sm)",
        padding: "7px 8px",
        cursor: "pointer",
        background: hover ? "var(--paper-2)" : "transparent",
        fontFamily: "inherit",
        transition: "background .12s"
      }}
    >
      <span className="mono" style={{ fontSize: 11, color: "var(--ink-faint)", textAlign: "right" }}>{rank}</span>
      <div style={{ width: 34 }}><CoverImage book={book} size="mini" /></div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{book.title}</div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6, marginTop: 2 }}>
          <span style={{ fontSize: 11, color: "var(--ink-mute)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{book.authors.split(",")[0]}</span>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--accent-ink)", flexShrink: 0 }}>{book.similarity_score.toFixed(2)}</span>
        </div>
      </div>
    </button>
  );
};

interface CompareColumnProps {
  method: string;
  state: { data: any; loading: boolean; error: Error | null };
  onOpen: (book: BookResult) => void;
  highlightISBNs: Set<string>;
}

const CompareColumn: React.FC<CompareColumnProps> = ({ method, state, onOpen, highlightISBNs }) => {
  const m = METHOD_MAP[method] || { color: 'var(--ink-soft)', short: method, type: '' };
  return (
    <div style={{
      border: "1px solid var(--line)",
      borderRadius: "var(--r-lg)",
      background: "var(--surface)",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
      minWidth: 0
    }}>
      <div style={{ padding: "12px 12px 11px", borderBottom: "1px solid var(--line)", background: "var(--paper-2)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <span style={{ width: 10, height: 10, borderRadius: 3, background: m.color }} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>{m.short}</span>
        </div>
        <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-mute)", marginTop: 5, display: "flex", justifyContent: "space-between" }}>
          <span style={{ textTransform: "uppercase", letterSpacing: ".04em" }}>{m.type}</span>
          <span>{state.loading ? "…" : state.data ? `${state.data.query_time_ms}ms` : ""}</span>
        </div>
      </div>
      <div style={{ padding: 7, flex: 1 }}>
        {state.loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} style={{ display: "flex", gap: 9, padding: "7px 8px", alignItems: "center" }}>
              <div className="skel" style={{ width: 34, height: 51, flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div className="skel" style={{ height: 11, width: "90%" }} />
                <div className="skel" style={{ height: 9, width: "55%", marginTop: 6 }} />
              </div>
            </div>
          ))
        ) : state.error ? (
          <div style={{ padding: "20px 10px", textAlign: "center", color: "var(--ink-mute)", fontSize: 12 }}>Failed to load</div>
        ) : state.data && state.data.results.length === 0 ? (
          <div style={{ padding: "24px 10px", textAlign: "center", color: "var(--ink-faint)", fontSize: 12, fontStyle: "italic", fontFamily: "var(--font-serif)" }}>No matches</div>
        ) : state.data ? (
          state.data.results.slice(0, 5).map((b: BookResult, i: number) => (
            <div key={b.isbn13} style={{
              borderRadius: "var(--r-sm)",
              outline: highlightISBNs.has(b.isbn13) ? `1.5px solid ${m.color}` : "none",
              background: highlightISBNs.has(b.isbn13) ? "var(--paper-2)" : "transparent"
            }}>
              <CompareRow book={b} rank={i + 1} method={method} onOpen={onOpen} />
            </div>
          ))
        ) : null}
      </div>
    </div>
  );
};

function useParallelSearch(query: string, topK: number) {
  return useAsync(async () => {
    const entries = await Promise.all(METHODS.map(async m => {
      try {
        return [m.id, { data: await apiSearch({ query, top_k: topK, method: m.id, filter_emotions: null }), loading: false, error: null }];
      } catch (e) {
        return [m.id, { data: null, loading: false, error: e instanceof Error ? e : new Error(String(e)) }];
      }
    }));
    return Object.fromEntries(entries);
  }, [query, topK], { enabled: !!query });
}

function computeInsights(states: Record<string, { data: any; error: Error | null; loading: boolean }>) {
  if (!states) return [];
  const top: Record<string, Set<string>> = {};
  METHODS.forEach(m => {
    top[m.id] = new Set((states[m.id]?.data?.results || []).slice(0, 5).map((b: any) => b.isbn13));
  });

  // Tìm tiêu đề sách từ kết quả tìm kiếm thật (thay vì dùng BOOK_BY_ISBN mock)
  const titleOf = (isbn: string) => {
    for (const m of METHODS) {
      const found = (states[m.id]?.data?.results || []).find((b: any) => b.isbn13 === isbn);
      if (found) return found.title;
    }
    return isbn;
  };

  const out: Array<{ a: string | null; z: string | null; text: React.ReactNode }> = [];

  // 1. semantic vs tfidf
  const semList = (states.semantic?.data?.results || []).slice(0, 5);
  const semOnly = semList.filter((b: any) => !top.tfidf.has(b.isbn13));
  if (semOnly.length) {
    out.push({
      a: "semantic", z: "tfidf",
      text: <><b>Semantic</b> surfaces <em>{semOnly[0].title}</em>{semOnly.length > 1 ? ` and ${semOnly.length - 1} other${semOnly.length > 2 ? "s" : ""}` : ""} in its top 5 that <b>TF-IDF</b> misses entirely — books that match the query's meaning without sharing its keywords.</>
    });
  }

  // 2. reranking vs hybrid
  const rerank = (states.reranking?.data?.results || []).slice(0, 5);
  const hybrid = (states.hybrid?.data?.results || []).slice(0, 5);
  const rerankOnly = rerank.filter((b: any) => !top.hybrid.has(b.isbn13));
  if (rerankOnly.length) {
    out.push({
      a: "reranking", z: "hybrid",
      text: <><b>Reranking</b> promotes <em>{rerankOnly[0].title}</em> into the top 5, reordering the candidate pool that <b>Hybrid RRF</b> ranked lower.</>
    });
  } else if (rerank.length && hybrid.length && rerank[0].isbn13 !== hybrid[0].isbn13) {
    out.push({
      a: "reranking", z: "hybrid",
      text: <><b>Reranking</b> and <b>Hybrid</b> agree on the candidate set but disagree on order — reranking puts <em>{titleOf(rerank[0].isbn13)}</em> first where hybrid led with <em>{titleOf(hybrid[0].isbn13)}</em>.</>
    });
  }

  // 3. agreement note
  const allTop1 = METHODS.map(m => states[m.id]?.data?.results?.[0]?.isbn13).filter(Boolean);
  const uniqueTop1 = new Set(allTop1);
  out.push({
    a: null, z: null,
    text: uniqueTop1.size === 1
      ? <>All five methods agree on the same top result — <em>{titleOf(allTop1.values().next().value!)}</em> — a strong, unambiguous match.</>
      : <>The five methods return <b>{uniqueTop1.size} different</b> top results for this query, illustrating how ranking strategy shapes what a reader sees first.</>
  });
  return out;
}

interface CompareMethodsPageProps {
  onOpenBook: (book: BookResult) => void;
}

export const CompareMethodsPage: React.FC<CompareMethodsPageProps> = ({ onOpenBook }) => {
  const [query, setQuery] = useState("");
  const [committed, setCommitted] = useState("");

  // Parse URL hash parameters on mount and hash change
  useEffect(() => {
    const parseHash = () => {
      const hash = window.location.hash || "";
      const qIdx = hash.indexOf("?");
      if (qIdx === -1) {
        if (hash === "#/compare") {
          setQuery("");
          setCommitted("");
        }
        return;
      }
      const params = new URLSearchParams(hash.slice(qIdx));
      const q = params.get("query") || "";
      setQuery(q);
      setCommitted(q.trim());
    };

    parseHash();
    window.addEventListener("hashchange", parseHash);
    return () => window.removeEventListener("hashchange", parseHash);
  }, []);

  const updateHash = (q: string) => {
    const params = new URLSearchParams();
    if (q.trim()) params.set("query", q.trim());
    const pStr = params.toString();
    const newHash = pStr ? `#/compare?${pStr}` : "#/compare";
    if (window.location.hash !== newHash) {
      window.location.hash = newHash;
    }
  };

  const states = useParallelSearch(committed, 5);

  const submit = useCallback((q?: string) => {
    const qq = (q != null ? q : query).trim();
    if (!qq) return;
    if (q != null) setQuery(qq);
    setCommitted(qq);
    updateHash(qq);
  }, [query]);

  const insights = useMemo(() => (states.data ? computeInsights(states.data) : []), [states.data]);

  const highlight = useMemo(() => {
    const map: Record<string, Set<string>> = {};
    if (!states.data) return map;
    const counts: Record<string, number> = {};
    METHODS.forEach(m => {
      (states.data![m.id]?.data?.results || []).slice(0, 5).forEach((b: any) => {
        counts[b.isbn13] = (counts[b.isbn13] || 0) + 1;
      });
    });
    METHODS.forEach(m => {
      map[m.id] = new Set(
        (states.data![m.id]?.data?.results || []).slice(0, 5).filter((b: any) => counts[b.isbn13] === 1).map((b: any) => b.isbn13)
      );
    });
    return map;
  }, [states.data]);

  return (
    <div style={{ maxWidth: "var(--maxw)", margin: "0 auto", padding: "28px 24px 80px", width: "100%" }}>
      <div style={{ marginBottom: 22 }}>
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 600, margin: 0, letterSpacing: "-0.015em" }}>Compare methods side by side</h1>
        <p style={{ fontSize: 14.5, color: "var(--ink-mute)", margin: "6px 0 0", maxWidth: 620 }}>
          One query, five retrieval strategies, run in parallel. Watch how each ranks the same corpus differently — books unique to a single method are outlined.
        </p>
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "stretch", flexWrap: "wrap", maxWidth: 720 }}>
        <div style={{ position: "relative", flex: 1, minWidth: 240 }}>
          <span style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--ink-faint)" }}><Icon name="compare" size={18} /></span>
          <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && submit()}
            placeholder="Enter a query to run across all five methods…"
            style={{
              width: "100%",
              height: 48,
              padding: "0 16px 0 44px",
              fontSize: 15,
              fontFamily: "var(--font-serif)",
              borderRadius: "var(--r-md)",
              border: "1px solid var(--line)",
              background: "var(--surface)",
              color: "var(--ink)",
              outline: "none"
            }}
            onFocus={e => e.target.style.borderColor = "var(--accent-line)"} onBlur={e => e.target.style.borderColor = "var(--line)"} />
        </div>
        <Button size="lg" icon="grid" onClick={() => submit()} disabled={!query.trim()}>Run all 5</Button>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, color: "var(--ink-mute)" }}>Try:</span>
        {EXAMPLE_QUERIES.slice(0, 3).map(q => (
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

      {!committed ? (
        <div style={{ marginTop: 40 }}>
          <EmptyState title="Run a query to compare" body="Each of the five methods will rank the corpus for the same query. The differences are where the research story lives." />
        </div>
      ) : (
        <>
          <div style={{ marginTop: 26 }} className="compare-grid">
            {METHODS.map(m => (
              <CompareColumn
                key={m.id}
                method={m.id}
                state={states.loading ? { data: null, loading: true, error: null } : (states.data ? states.data[m.id] : { data: null, loading: true, error: null })}
                onOpen={onOpenBook}
                highlightISBNs={highlight[m.id] || new Set()}
              />
            ))}
          </div>

          {/* insight */}
          <div style={{ marginTop: 24, border: "1px solid var(--accent-line)", background: "var(--accent-wash)", borderRadius: "var(--r-lg)", padding: "18px 20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <Icon name="spark" size={16} style={{ color: "var(--accent-ink)" }} />
              <span className="mono" style={{ fontSize: 11.5, fontWeight: 600, color: "var(--accent-ink)", textTransform: "uppercase", letterSpacing: ".06em" }}>What the differences tell us</span>
            </div>
            {states.loading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>{[0, 1].map(i => <div key={i} className="skel" style={{ height: 14, width: `${85 - i * 20}%` }} />)}</div>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
                {insights.map((ins, i) => (
                  <li key={i} style={{ display: "flex", gap: 10, fontSize: 14, lineHeight: 1.5, color: "var(--ink)" }}>
                    <span style={{ color: "var(--accent-ink)", marginTop: 1 }}>→</span>
                    <span style={{ textWrap: "pretty" }}>{ins.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}

      <style>{`
        .compare-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
        @media (max-width: 900px){ .compare-grid{ grid-template-columns: repeat(2,1fr); } }
        @media (max-width: 520px){ .compare-grid{ grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
};
