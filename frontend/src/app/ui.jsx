// ============================================================
//  ui.jsx — primitives + shared components + async hooks
// ============================================================
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { EMOTION_META, METHODS, METHOD_MAP, EMOTIONS } from './data'

/* ---------- icons ---------- */
const ICON_PATHS = {
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 17-4.35-4.35",
  compare: "M9 3v18M4 7h5M4 12h5M4 17h5M15 3v18M20 7h-5M20 12h-5M20 17h-5",
  chart: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  star: "M12 3.5l2.6 5.27 5.82.85-4.21 4.1.99 5.78L12 16.77 6.8 19.5l.99-5.78-4.21-4.1 5.82-.85z",
  close: "M6 6l12 12M18 6 6 18",
  sun: "M12 4V2M12 22v-2M5 5 3.5 3.5M20.5 20.5 19 19M4 12H2M22 12h-2M5 19l-1.5 1.5M20.5 3.5 19 5M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  moon: "M21 12.5A8.5 8.5 0 1 1 11.5 3 6.5 6.5 0 0 0 21 12.5z",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5M12 7.5h.01",
  arrow: "M5 12h14M13 6l6 6-6 6",
  refresh: "M21 12a9 9 0 1 1-2.64-6.36M21 4v5h-5",
  book: "M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4zM5 4a3 3 0 0 0 0 6h0",
  sliders: "M4 6h11M19 6h1M4 12h1M9 12h11M4 18h7M15 18h5M15 4v4M9 10v4M11 16v4",
  check: "M5 12.5l4.5 4.5L19 7",
  external: "M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
  spark: "M12 3v6M12 15v6M3 12h6M15 12h6",
  grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
};
function Icon({ name, size = 18, stroke = 1.7, fill = false, style }) {
  const d = ICON_PATHS[name];
  return (
    <svg width={size} height={size} viewBox="0 0 24 24"
      fill={fill ? "currentColor" : "none"} stroke={fill ? "none" : "currentColor"}
      strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
      style={{ flexShrink: 0, ...style }}>
      <path d={d} />
    </svg>
  );
}

/* ---------- async hooks (TanStack-Query stand-in) ---------- */
function useAsync(fn, deps, { enabled = true } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: enabled, fetching: false });
  const idRef = useRef(0);
  const run = useCallback(() => {
    const id = ++idRef.current;
    setState(s => ({ ...s, loading: s.data == null, fetching: true, error: null }));
    Promise.resolve().then(fn).then(
      data => { if (id === idRef.current) setState({ data, error: null, loading: false, fetching: false }); },
      error => { if (id === idRef.current) setState(s => ({ ...s, error, loading: false, fetching: false })); }
    );
  }, deps); // eslint-disable-line
  useEffect(() => { if (enabled) run(); }, [run, enabled]);
  return { ...state, refetch: run };
}

/* ---------- buttons ---------- */
function Button({ children, variant = "primary", size = "md", icon, iconRight, onClick, disabled, type = "button", style, title, ...rest }) {
  const [hover, setHover] = useState(false);
  const sizes = {
    sm: { padding: "6px 11px", fontSize: 13, gap: 6, height: 32 },
    md: { padding: "9px 16px", fontSize: 14, gap: 7, height: 40 },
    lg: { padding: "12px 22px", fontSize: 15, gap: 8, height: 48 },
  }[size];
  const variants = {
    primary: { background: hover ? "var(--accent-ink)" : "var(--accent)", color: "#fff", border: "1px solid transparent", boxShadow: "var(--shadow-sm)" },
    secondary: { background: hover ? "var(--paper-2)" : "var(--surface)", color: "var(--ink)", border: "1px solid var(--line)" },
    ghost: { background: hover ? "var(--paper-2)" : "transparent", color: "var(--ink-soft)", border: "1px solid transparent" },
    outline: { background: hover ? "var(--accent-wash)" : "transparent", color: "var(--accent-ink)", border: "1px solid var(--accent-line)" },
  }[variant];
  return (
    <button type={type} onClick={onClick} disabled={disabled} title={title}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: sizes.gap,
        padding: sizes.padding, fontSize: sizes.fontSize, height: sizes.height, fontWeight: 600,
        borderRadius: "var(--r-md)", cursor: disabled ? "not-allowed" : "pointer", whiteSpace: "nowrap",
        opacity: disabled ? 0.5 : 1, transition: "background .16s, transform .1s, box-shadow .16s",
        fontFamily: "var(--font-sans)", ...variants, ...style }} {...rest}>
      {icon && <Icon name={icon} size={size === "sm" ? 15 : 17} />}
      {children}
      {iconRight && <Icon name={iconRight} size={size === "sm" ? 15 : 17} />}
    </button>
  );
}

/* ---------- badges / chips ---------- */
function Badge({ children, color, tone = "neutral", style }) {
  const tones = {
    neutral: { background: "var(--paper-2)", color: "var(--ink-soft)", border: "1px solid var(--line)" },
    accent: { background: "var(--accent-wash)", color: "var(--accent-ink)", border: "1px solid var(--accent-line)" },
    good: { background: "var(--good-wash)", color: "var(--good)", border: "1px solid transparent" },
  }[tone];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "2px 9px",
      borderRadius: 99, fontSize: 12, fontWeight: 600, fontFamily: "var(--font-sans)",
      lineHeight: 1.7, ...tones, ...style }}>
      {color && <span style={{ width: 7, height: 7, borderRadius: 99, background: color, flexShrink: 0 }} />}
      {children}
    </span>
  );
}

function EmotionBadge({ emotion, score }) {
  const m = EMOTION_META[emotion];
  if (!m) return null;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "2px 8px 2px 6px",
      borderRadius: 99, fontSize: 11.5, fontWeight: 600, background: "var(--paper-2)",
      border: "1px solid var(--line)", color: "var(--ink-soft)" }}>
      <span style={{ width: 8, height: 8, borderRadius: 99, background: m.color }} />
      {m.label}{score != null && <span className="mono" style={{ color: "var(--ink-mute)", fontSize: 10.5 }}>{score.toFixed(2)}</span>}
    </span>
  );
}

function MethodChip({ method, showType = false, size = "md" }) {
  const m = METHOD_MAP[method] || method;
  const fs = size === "sm" ? 11.5 : 12.5;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
      <span style={{ width: 9, height: 9, borderRadius: 3, background: m.color, flexShrink: 0 }} />
      <span style={{ fontWeight: 600, fontSize: fs }}>{m.label}</span>
      {showType && <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".04em" }}>{m.type}</span>}
    </span>
  );
}

/* ---------- star rating ---------- */
function StarRating({ value, size = 15 }) {
  const pct = Math.max(0, Math.min(100, (value / 5) * 100));
  const id = useMemo(() => "sg" + Math.random().toString(36).slice(2, 8), []);
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
      <span style={{ position: "relative", display: "inline-flex" }}>
        <svg width={size * 5 + 8} height={size} style={{ display: "block" }}>
          <defs>
            <linearGradient id={id}>
              <stop offset={pct + "%"} stopColor="var(--accent)" />
              <stop offset={pct + "%"} stopColor="var(--line)" />
            </linearGradient>
          </defs>
          {[0, 1, 2, 3, 4].map(i => (
            <path key={i} transform={`translate(${i * (size + 2)} 0) scale(${size / 24})`}
              d={ICON_PATHS.star} fill={`url(#${id})`} />
          ))}
        </svg>
      </span>
    </span>
  );
}

/* ---------- cover image with fallback ---------- */
function CoverImage({ book, size = "card" }) {
  const [errored, setErrored] = useState(false);
  const dims = {
    card: { w: "100%", aspect: "2 / 3", radius: "var(--r-sm)", fs: 12, label: 11 },
    large: { w: "100%", aspect: "2 / 3", radius: "var(--r-md)", fs: 17, label: 12 },
    mini: { w: "100%", aspect: "2 / 3", radius: 4, fs: 10, label: 9 },
  }[size];
  const show = !book.thumbnail || errored;
  if (show) {
    return (
      <div style={{ width: dims.w, aspectRatio: dims.aspect, borderRadius: dims.radius, overflow: "hidden",
        position: "relative", background: "var(--paper-2)", border: "1px solid var(--line)",
        display: "flex", flexDirection: "column", justifyContent: "space-between", padding: size === "mini" ? 7 : 12 }}>
        <div style={{ position: "absolute", inset: 0, opacity: 0.5,
          backgroundImage: "repeating-linear-gradient(135deg, var(--line-soft) 0 7px, transparent 7px 15px)" }} />
        <div style={{ position: "relative", fontFamily: "var(--font-mono)", fontSize: dims.label,
          color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".06em" }}>no cover</div>
        <div style={{ position: "relative" }}>
          <div className="serif" style={{ fontSize: dims.fs, fontWeight: 600, color: "var(--ink-soft)", lineHeight: 1.25,
            display: "-webkit-box", WebkitLineClamp: 4, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{book.title}</div>
          <div style={{ fontSize: dims.label, color: "var(--ink-mute)", marginTop: 5 }}>{book.authors.split(",")[0]}</div>
        </div>
      </div>
    );
  }
  return (
    <div style={{ width: dims.w, aspectRatio: dims.aspect, borderRadius: dims.radius, overflow: "hidden",
      background: "var(--paper-2)", border: "1px solid var(--line)" }}>
      <img src={book.thumbnail} alt={book.title} loading="lazy" onError={() => setErrored(true)}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
    </div>
  );
}

/* ---------- emotion bars (modal) ---------- */
function EmotionBars({ scores }) {
  const ordered = [...EMOTIONS].sort((a, b) => scores[b] - scores[a]);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {ordered.map(em => {
        const m = EMOTION_META[em];
        const v = scores[em] || 0;
        return (
          <div key={em} style={{ display: "grid", gridTemplateColumns: "78px 1fr 38px", alignItems: "center", gap: 12 }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 7, fontSize: 13, fontWeight: 500 }}>
              <span style={{ width: 8, height: 8, borderRadius: 99, background: m.color }} />{m.label}
            </span>
            <span style={{ height: 8, background: "var(--paper-2)", borderRadius: 99, overflow: "hidden", border: "1px solid var(--line-soft)" }}>
              <span style={{ display: "block", height: "100%", width: (v * 100) + "%", background: m.color,
                borderRadius: 99, transition: "width .5s cubic-bezier(.2,.7,.2,1)" }} />
            </span>
            <span className="mono" style={{ fontSize: 12, color: "var(--ink-mute)", textAlign: "right" }}>{v.toFixed(2)}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- emotion radar (modal alt view) ---------- */
function EmotionRadar({ scores, size = 200 }) {
  const cx = size / 2, cy = size / 2, R = size / 2 - 26;
  const n = EMOTIONS.length;
  const pt = (i, r) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const poly = EMOTIONS.map((em, i) => pt(i, R * (scores[em] || 0)).join(",")).join(" ");
  return (
    <svg width={size} height={size} style={{ display: "block", margin: "0 auto" }}>
      {[0.25, 0.5, 0.75, 1].map((g, gi) => (
        <polygon key={gi} points={EMOTIONS.map((_, i) => pt(i, R * g).join(",")).join(" ")}
          fill="none" stroke="var(--line)" strokeWidth={1} />
      ))}
      {EMOTIONS.map((em, i) => {
        const [x, y] = pt(i, R);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line-soft)" strokeWidth={1} />;
      })}
      <polygon points={poly} fill="var(--accent)" fillOpacity={0.16} stroke="var(--accent)" strokeWidth={1.8} strokeLinejoin="round" />
      {EMOTIONS.map((em, i) => {
        const [x, y] = pt(i, R * (scores[em] || 0));
        return <circle key={i} cx={x} cy={y} r={2.6} fill="var(--accent)" />;
      })}
      {EMOTIONS.map((em, i) => {
        const [x, y] = pt(i, R + 15);
        return <text key={i} x={x} y={y} fontSize={9.5} fill="var(--ink-mute)" textAnchor="middle"
          dominantBaseline="middle" fontFamily="var(--font-mono)" style={{ textTransform: "uppercase" }}>{em.slice(0, 4)}</text>;
      })}
    </svg>
  );
}

/* ---------- state views ---------- */
function Spinner({ size = 18 }) {
  return <span style={{ width: size, height: size, border: "2.5px solid var(--line)", borderTopColor: "var(--accent)",
    borderRadius: "50%", display: "inline-block", animation: "spin .7s linear infinite" }} />;
}
function StateBox({ children }) {
  return <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    textAlign: "center", padding: "56px 24px", gap: 14, animation: "fadeIn .3s" }}>{children}</div>;
}
function EmptyState({ title, body, action }) {
  return (
    <StateBox>
      <div style={{ width: 46, height: 46, borderRadius: "50%", background: "var(--paper-2)", border: "1px solid var(--line)",
        display: "grid", placeItems: "center", color: "var(--ink-faint)" }}><Icon name="search" size={20} /></div>
      <div>
        <div className="serif" style={{ fontSize: 20, fontWeight: 600 }}>{title}</div>
        <div style={{ color: "var(--ink-mute)", fontSize: 14, marginTop: 4, maxWidth: 380 }}>{body}</div>
      </div>
      {action}
    </StateBox>
  );
}
function ErrorState({ error, onRetry }) {
  return (
    <StateBox>
      <div style={{ width: 46, height: 46, borderRadius: "50%", background: "oklch(0.95 0.04 30)", color: "oklch(0.55 0.16 30)",
        display: "grid", placeItems: "center", border: "1px solid oklch(0.85 0.07 30)" }}><Icon name="info" size={22} /></div>
      <div>
        <div className="serif" style={{ fontSize: 20, fontWeight: 600 }}>Something went wrong</div>
        <div style={{ color: "var(--ink-mute)", fontSize: 14, marginTop: 4, maxWidth: 420 }}>
          {(error && error.message) || "We couldn't reach the search service."} Please try again.
        </div>
      </div>
      {onRetry && <Button variant="outline" icon="refresh" onClick={onRetry}>Retry</Button>}
    </StateBox>
  );
}

/* ---------- popover (methods explained) ---------- */
function Popover({ trigger, children, align = "right", width = 340 }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const h = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);
  return (
    <span ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <span onClick={() => setOpen(o => !o)}>{trigger(open)}</span>
      {open && (
        <div style={{ position: "absolute", top: "calc(100% + 10px)", [align]: 0, width, zIndex: 60,
          background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--r-lg)",
          boxShadow: "var(--shadow-lg)", padding: 16, animation: "pop .16s ease-out" }}>
          {children}
        </div>
      )}
    </span>
  );
}

const METHOD_EXPLAIN = {
  tfidf: "Scores documents by how often query words appear, down-weighting words common across the corpus. Pure keyword matching — fast, but blind to meaning.",
  bm25: "A refined sparse ranking that adds term-frequency saturation and document-length normalization on top of TF-IDF. The strong classical baseline.",
  semantic: "Embeds query and books into a shared vector space with the BGE-small model and retrieves nearest neighbours from ChromaDB. Matches meaning, not words.",
  hybrid: "Fuses sparse (BM25) and dense (semantic) rankings with Reciprocal Rank Fusion — keyword precision plus semantic recall.",
  reranking: "Runs dense retrieval, then re-scores the top candidates with a heavier cross-encoder for the sharpest ordering. Most accurate, slowest.",
};
function MethodsExplained() {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <Icon name="info" size={16} style={{ color: "var(--accent)" }} />
        <span className="serif" style={{ fontSize: 16, fontWeight: 600 }}>The five retrieval methods</span>
      </div>
      <p style={{ fontSize: 12.5, color: "var(--ink-mute)", margin: "0 0 12px" }}>How each ranks books for a query, fastest to most accurate.</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
        {METHODS.map(m => (
          <div key={m.id} style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 10, alignItems: "start" }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: m.color, marginTop: 4 }} />
            <div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{m.label}</span>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-mute)" }}>{m.type} · ~{m.avgMs}ms</span>
              </div>
              <div style={{ fontSize: 12.5, color: "var(--ink-soft)", lineHeight: 1.45, marginTop: 2 }}>{METHOD_EXPLAIN[m.id]}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export {
  Icon, useAsync, Button, Badge, EmotionBadge, MethodChip, StarRating, CoverImage,
  EmotionBars, EmotionRadar, Spinner, StateBox, EmptyState, ErrorState, Popover,
  MethodsExplained, METHOD_EXPLAIN,
};
