// ============================================================
//  modal.jsx — BookDetailModal (overlay). Fetches full detail
//  via GET /books/:isbn13 for all 7 emotion scores.
// ============================================================
import { useState as useStateM, useEffect as useEffectM } from 'react'
import { apiBook } from './data'
import { Icon, useAsync, ErrorState, CoverImage, MethodChip, StarRating, EmotionBars, EmotionRadar, Button } from './ui'

function CategoryTags({ categories }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {categories.split("|").map(c => (
        <span key={c} style={{ fontSize: 11.5, fontWeight: 600, padding: "2px 9px", borderRadius: 99,
          background: "var(--paper-2)", border: "1px solid var(--line)", color: "var(--ink-soft)" }}>{c}</span>
      ))}
    </div>
  );
}

function BookDetailModal({ result, onClose }) {
  const [emoView, setEmoView] = useStateM("bars");
  // result carries similarity_score + method context from the search;
  // we fetch the canonical record for full emotion scores.
  const { data: book, loading, error, refetch } = useAsync(() => apiBook(result.isbn13), [result.isbn13]);

  useEffectM(() => {
    const h = e => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", h); document.body.style.overflow = ""; };
  }, []);

  const olUrl = `https://openlibrary.org/isbn/${result.isbn13}`;
  const ratingsCount = (book || result).ratings_count;

  return (
    <div onMouseDown={onClose} style={{ position: "fixed", inset: 0, zIndex: 100, background: "oklch(0.2 0.01 60 / 0.46)",
      backdropFilter: "blur(3px)", display: "flex", alignItems: "flex-start", justifyContent: "center",
      padding: "min(8vh, 64px) 20px 40px", overflowY: "auto", animation: "fadeIn .18s" }}>
      <div onMouseDown={e => e.stopPropagation()} style={{ width: "min(820px, 100%)", background: "var(--surface)",
        borderRadius: "var(--r-lg)", border: "1px solid var(--line)", boxShadow: "var(--shadow-lg)",
        animation: "pop .22s ease-out", position: "relative" }}>
        <button onClick={onClose} aria-label="Close" style={{ position: "absolute", top: 14, right: 14, zIndex: 2,
          width: 34, height: 34, borderRadius: 99, border: "1px solid var(--line)", background: "var(--surface)",
          color: "var(--ink-soft)", cursor: "pointer", display: "grid", placeItems: "center" }}>
          <Icon name="close" size={17} />
        </button>

        {error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,210px) 1fr", gap: 28, padding: 28 }} className="bdm-grid">
            {/* left: cover + meta */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <CoverImage book={result} size="large" />
              {result.similarity_score != null && (
                <div style={{ padding: 12, borderRadius: "var(--r-md)", background: "var(--accent-wash)", border: "1px solid var(--accent-line)" }}>
                  <div className="mono" style={{ fontSize: 10.5, color: "var(--accent-ink)", textTransform: "uppercase", letterSpacing: ".06em" }}>Retrieved via</div>
                  <div style={{ marginTop: 6 }}><MethodChip method={result._method || "semantic"} /></div>
                  <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginTop: 10 }}>
                    <span style={{ fontSize: 12, color: "var(--ink-soft)" }}>Similarity</span>
                    <span className="mono" style={{ fontSize: 19, fontWeight: 600, color: "var(--accent-ink)" }}>{result.similarity_score.toFixed(3)}</span>
                  </div>
                </div>
              )}
              <a href={olUrl} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm" iconRight="external" style={{ width: "100%" }}>Open Library</Button>
              </a>
            </div>

            {/* right: details */}
            <div style={{ minWidth: 0 }}>
              <CategoryTags categories={(book || result).categories} />
              <h2 className="serif" style={{ fontSize: 30, fontWeight: 600, lineHeight: 1.12, margin: "12px 0 6px", letterSpacing: "-0.01em" }}>{result.title}</h2>
              <div style={{ fontSize: 15, color: "var(--ink-soft)" }}>
                {result.authors} <span style={{ color: "var(--ink-faint)" }}>·</span> <span className="mono" style={{ fontSize: 13, color: "var(--ink-mute)" }}>{result.published_year}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
                <StarRating value={result.average_rating} size={16} />
                <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{result.average_rating.toFixed(2)}</span>
                <span style={{ fontSize: 13, color: "var(--ink-mute)" }}>· {ratingsCount.toLocaleString()} ratings</span>
              </div>

              <p style={{ fontSize: 14.5, lineHeight: 1.62, color: "var(--ink-soft)", margin: "18px 0 0", textWrap: "pretty" }}>{result.description}</p>

              <div style={{ borderTop: "1px solid var(--line)", margin: "22px 0 0", paddingTop: 18 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                  <span className="serif" style={{ fontSize: 17, fontWeight: 600 }}>Emotional profile</span>
                  <div style={{ display: "inline-flex", background: "var(--paper-2)", borderRadius: 99, padding: 3, border: "1px solid var(--line)" }}>
                    {["bars", "radar"].map(v => (
                      <button key={v} onClick={() => setEmoView(v)} style={{ border: "none", cursor: "pointer", padding: "4px 13px",
                        borderRadius: 99, fontSize: 12, fontWeight: 600, textTransform: "capitalize",
                        background: emoView === v ? "var(--surface)" : "transparent", color: emoView === v ? "var(--ink)" : "var(--ink-mute)",
                        boxShadow: emoView === v ? "var(--shadow-sm)" : "none" }}>{v}</button>
                    ))}
                  </div>
                </div>
                {loading ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {[0, 1, 2, 3, 4, 5, 6].map(i => <div key={i} className="skel" style={{ height: 16, width: `${90 - i * 9}%` }} />)}
                  </div>
                ) : emoView === "bars" ? (
                  <EmotionBars scores={book.emotion_scores} />
                ) : (
                  <EmotionRadar scores={book.emotion_scores} size={240} />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
      <style>{`@media (max-width: 640px){ .bdm-grid{ grid-template-columns: 1fr !important; } }`}</style>
    </div>
  );
}

export { BookDetailModal };
