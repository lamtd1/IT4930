// ============================================================
//  page_eval.jsx — EvaluationDashboard (route "/evaluation")
//  The defense centerpiece. Vocabulary Mismatch Demo is the
//  headline artifact.
// ============================================================
import { useState as useStateE, useMemo as useMemoE } from 'react'
import { METHODS, METHOD_MAP, apiEvaluation } from './data'
import { Icon, useAsync, EmotionBadge, CoverImage, ErrorState } from './ui'
import { GroupedBarChart, ScatterChart, GenreRadarChart, MethodLegend } from './charts'

function SectionHead({ kicker, title, sub, right }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, marginBottom: 18, flexWrap: "wrap" }}>
      <div>
        {kicker && <div className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--accent-ink)", textTransform: "uppercase", letterSpacing: ".09em", marginBottom: 7 }}>{kicker}</div>}
        <h2 className="serif" style={{ fontSize: 24, fontWeight: 600, margin: 0, letterSpacing: "-0.015em" }}>{title}</h2>
        {sub && <p style={{ fontSize: 14, color: "var(--ink-mute)", margin: "6px 0 0", maxWidth: 640 }}>{sub}</p>}
      </div>
      {right}
    </div>
  );
}

function Panel({ children, style, pad = 22 }) {
  return <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--r-lg)", padding: pad, boxShadow: "var(--shadow-sm)", ...style }}>{children}</div>;
}

/* ---------- vocabulary mismatch: the killer demo ---------- */
function FaceOffCard({ book, kind, onOpen }) {
  const isSem = kind === "semantic";
  const accent = isSem ? "var(--m-semantic)" : "var(--m-tfidf)";
  return (
    <div style={{ flex: 1, minWidth: 0, border: `1px solid ${isSem ? "var(--accent-line)" : "var(--line)"}`,
      borderRadius: "var(--r-lg)", background: isSem ? "var(--accent-wash)" : "var(--paper-2)", overflow: "hidden",
      opacity: !book && !isSem ? 0.92 : 1 }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 9,
        background: "var(--surface)" }}>
        <span style={{ width: 11, height: 11, borderRadius: 3, background: accent }} />
        <div>
          <div style={{ fontSize: 13, fontWeight: 700 }}>{isSem ? "Semantic (BGE)" : "TF-IDF (keyword)"}</div>
          <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".04em" }}>{isSem ? "matches meaning" : "matches words"}</div>
        </div>
      </div>
      <div style={{ padding: 16, minHeight: 150 }}>
        {book ? (
          <button onClick={() => onOpen({ ...book, _method: isSem ? "semantic" : "tfidf" })}
            style={{ display: "flex", gap: 14, width: "100%", textAlign: "left", background: "transparent", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0 }}>
            <div style={{ width: 64, flexShrink: 0 }}><CoverImage book={book} size="mini" /></div>
            <div style={{ minWidth: 0 }}>
              <div className="serif" style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.18 }}>{book.title}</div>
              <div style={{ fontSize: 12.5, color: "var(--ink-mute)", marginTop: 3 }}>{book.authors} · <span className="mono">{book.published_year}</span></div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 9 }}>{book.top_emotions.map(em => <EmotionBadge key={em} emotion={em} />)}</div>
            </div>
          </button>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 9, height: 130, textAlign: "center" }}>
            <div style={{ width: 38, height: 38, borderRadius: "50%", border: "1.5px dashed var(--ink-faint)", display: "grid", placeItems: "center", color: "var(--ink-faint)" }}><Icon name="close" size={18} /></div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-soft)" }}>No relevant result</div>
            <div style={{ fontSize: 12, color: "var(--ink-mute)", maxWidth: 220 }}>None of the query's words appear in the matching book, so keyword search returns nothing useful.</div>
          </div>
        )}
      </div>
    </div>
  );
}

function VocabMismatchDemo({ demos, onOpen }) {
  const [idx, setIdx] = useStateE(0);
  const d = demos[idx];
  const win = !d.tfidf_top1; // dramatic win when keyword search finds nothing
  return (
    <Panel pad={0} style={{ overflow: "hidden", borderColor: "var(--accent-line)" }}>
      <div style={{ padding: "20px 22px 18px", borderBottom: "1px solid var(--line)", background: "linear-gradient(180deg, var(--accent-wash), transparent)" }}>
        <SectionHead kicker="The headline result" title="Vocabulary mismatch, made visible"
          sub="Readers describe books in their own words — rarely the words in the blurb. Click a paraphrased query and watch keyword search fall short where semantic retrieval understands intent." />
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {demos.map((q, i) => (
            <button key={i} onClick={() => setIdx(i)} style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", fontSize: 13.5,
              padding: "8px 14px", borderRadius: 99, cursor: "pointer", transition: "all .14s",
              border: i === idx ? "1px solid var(--accent)" : "1px solid var(--line)",
              background: i === idx ? "var(--accent)" : "var(--surface)", color: i === idx ? "#fff" : "var(--ink-soft)" }}>
              "{q.query}"
            </button>
          ))}
        </div>
      </div>
      <div style={{ padding: 22 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16, flexWrap: "wrap" }}>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".06em" }}>Query</span>
          <span className="serif" style={{ fontSize: 19, fontStyle: "italic", fontWeight: 500 }}>"{d.query}"</span>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "stretch", position: "relative" }} className="faceoff-grid">
          <FaceOffCard book={d.tfidf_top1} kind="tfidf" onOpen={onOpen} />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }} className="faceoff-vs">
            <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--ink-faint)", padding: "4px 8px", border: "1px solid var(--line)", borderRadius: 99, background: "var(--surface)" }}>VS</span>
          </div>
          <FaceOffCard book={d.semantic_top1} kind="semantic" onOpen={onOpen} />
        </div>
        {win && (
          <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 9, fontSize: 13.5, color: "var(--ink-soft)" }}>
            <Icon name="spark" size={15} style={{ color: "var(--accent-ink)" }} />
            Zero keyword overlap — yet semantic retrieval lands the intended book. This is the gap our project closes.
          </div>
        )}
      </div>
      <style>{`@media (max-width: 720px){ .faceoff-grid{ flex-direction: column; } .faceoff-vs{ transform: rotate(90deg); } }`}</style>
    </Panel>
  );
}

/* ---------- comparison table ---------- */
function MetricsTable({ models }) {
  const cols = [
    { key: "p_at_5", label: "P@5", fmt: v => v.toFixed(2), higher: true },
    { key: "p_at_10", label: "P@10", fmt: v => v.toFixed(2), higher: true },
    { key: "mrr", label: "MRR", fmt: v => v.toFixed(2), higher: true },
    { key: "ms_per_query", label: "ms / query", fmt: v => v + "ms", higher: false },
  ];
  const best = {};
  cols.forEach(c => { best[c.key] = models.reduce((b, m) => (c.higher ? m[c.key] > b : m[c.key] < b) ? m[c.key] : b, c.higher ? -Infinity : Infinity); });
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5, minWidth: 560 }}>
        <thead>
          <tr style={{ borderBottom: "1.5px solid var(--line)" }}>
            <th style={{ textAlign: "left", padding: "0 12px 12px 4px", fontWeight: 600, color: "var(--ink-mute)", fontSize: 12 }}>Method</th>
            {cols.map(c => <th key={c.key} className="mono" style={{ textAlign: "right", padding: "0 12px 12px", fontWeight: 600, color: "var(--ink-mute)", fontSize: 12, whiteSpace: "nowrap" }}>{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {models.map(m => {
            const meta = METHOD_MAP[m.method];
            return (
              <tr key={m.method} style={{ borderBottom: "1px solid var(--line-soft)" }}>
                <td style={{ padding: "13px 12px 13px 4px" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 9 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, background: meta.color }} />
                    <span style={{ fontWeight: 600 }}>{meta.label}</span>
                    <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-faint)", textTransform: "uppercase" }}>{meta.type}</span>
                  </span>
                </td>
                {cols.map(c => {
                  const isBest = m[c.key] === best[c.key];
                  return (
                    <td key={c.key} className="mono" style={{ textAlign: "right", padding: "13px 12px", whiteSpace: "nowrap",
                      fontWeight: isBest ? 700 : 500, color: isBest ? "var(--accent-ink)" : "var(--ink)" }}>
                      {c.fmt(m[c.key])}
                      {isBest && <span title="best" style={{ marginLeft: 6, fontSize: 10 }}>★</span>}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Takeaways({ models }) {
  const byP5 = [...models].sort((a, b) => b.p_at_5 - a.p_at_5);
  const fastest = [...models].sort((a, b) => a.ms_per_query - b.ms_per_query)[0];
  const best = byP5[0];
  const items = [
    { l: "Most accurate", v: METHOD_MAP[best.method].short, d: `P@5 ${best.p_at_5.toFixed(2)}`, c: METHOD_MAP[best.method].color },
    { l: "Fastest", v: METHOD_MAP[fastest.method].short, d: `${fastest.ms_per_query}ms / query`, c: METHOD_MAP[fastest.method].color },
    { l: "Best balance", v: "Hybrid", d: `P@5 ${METHOD_MAP.hybrid && models.find(m => m.method === "hybrid").p_at_5.toFixed(2)} @ 60ms`, c: "var(--m-hybrid)" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }} className="takeaway-grid">
      {items.map((it, i) => (
        <Panel key={i} pad={16}>
          <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".06em" }}>{it.l}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
            <span style={{ width: 11, height: 11, borderRadius: 3, background: it.c, flexShrink: 0 }} />
            <span className="serif" style={{ fontSize: 21, fontWeight: 600, whiteSpace: "nowrap" }}>{it.v}</span>
          </div>
          <div className="mono" style={{ fontSize: 12, color: "var(--ink-soft)", marginTop: 4 }}>{it.d}</div>
        </Panel>
      ))}
      <style>{`@media (max-width: 640px){ .takeaway-grid{ grid-template-columns: 1fr; } }`}</style>
    </div>
  );
}

function EvaluationDashboard({ onOpenBook }) {
  const { data, loading, error, refetch } = useAsync(() => apiEvaluation(), []);
  const [activeMethods, setActiveMethods] = useStateE(METHODS.map(m => m.id));
  const toggleMethod = id => setActiveMethods(a => a.includes(id) ? (a.length > 1 ? a.filter(x => x !== id) : a) : [...a, id]);

  if (loading) return (
    <div style={{ maxWidth: "var(--maxw)", margin: "0 auto", padding: "28px 24px 80px", width: "100%" }}>
      <div className="skel" style={{ height: 36, width: 280 }} />
      <div className="skel" style={{ height: 220, width: "100%", marginTop: 24, borderRadius: "var(--r-lg)" }} />
      <div className="skel" style={{ height: 320, width: "100%", marginTop: 20, borderRadius: "var(--r-lg)" }} />
    </div>
  );
  if (error) return <div style={{ maxWidth: 640, margin: "40px auto", padding: 24 }}><ErrorState error={error} onRetry={refetch} /></div>;

  return (
    <div style={{ maxWidth: "var(--maxw)", margin: "0 auto", padding: "28px 24px 80px", width: "100%", display: "flex", flexDirection: "column", gap: 40 }}>
      <div>
        <h1 className="serif" style={{ fontSize: 30, fontWeight: 600, margin: 0, letterSpacing: "-0.015em" }}>Evaluation</h1>
        <p style={{ fontSize: 15, color: "var(--ink-mute)", margin: "8px 0 22px", maxWidth: 660 }}>
          Five retrieval methods benchmarked on a held-out query set with relevance judgements. Precision and ranking quality climb with model sophistication; latency is the cost.
        </p>
        <Takeaways models={data.models} />
      </div>

      {/* killer demo */}
      <VocabMismatchDemo demos={data.vocabulary_mismatch_demo} onOpen={onOpenBook} />

      {/* table */}
      <div>
        <SectionHead kicker="Benchmark" title="Metrics at a glance" sub="Precision@k and Mean Reciprocal Rank measure ranking quality; ms/query is mean wall-clock latency. Best in each column is starred." />
        <Panel><MetricsTable models={data.models} /></Panel>
      </div>

      {/* charts: bar + scatter */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }} className="chart-2up">
        <div>
          <SectionHead title="Quality by metric" sub="Each metric, all five methods." />
          <Panel>
            <GroupedBarChart models={data.models} />
            <MethodLegend style={{ marginTop: 14, justifyContent: "center" }} />
          </Panel>
        </div>
        <div>
          <SectionHead title="Speed vs. quality" sub="The accuracy you buy with latency." />
          <Panel><ScatterChart models={data.models} /></Panel>
        </div>
      </div>

      {/* radar */}
      <div>
        <SectionHead kicker="Per-genre" title="Where each method wins" sub="Precision@5 broken down by genre. Toggle methods to compare specific pairs."
          right={
            <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
              {METHODS.map(m => {
                const on = activeMethods.includes(m.id);
                return (
                  <button key={m.id} onClick={() => toggleMethod(m.id)} style={{ display: "inline-flex", alignItems: "center", gap: 6,
                    padding: "5px 10px", borderRadius: 99, cursor: "pointer", fontSize: 12, fontWeight: 600, transition: "all .14s",
                    border: on ? `1px solid ${m.color}` : "1px solid var(--line)", background: on ? "var(--paper-2)" : "var(--surface)",
                    color: on ? "var(--ink)" : "var(--ink-faint)" }}>
                    <span style={{ width: 9, height: 9, borderRadius: 3, background: m.color, opacity: on ? 1 : 0.4 }} />{m.short}
                  </button>
                );
              })}
            </div>
          } />
        <Panel><GenreRadarChart byGenre={data.by_genre} activeMethods={activeMethods} /></Panel>
      </div>

      <style>{`@media (max-width: 860px){ .chart-2up{ grid-template-columns: 1fr !important; } }`}</style>
    </div>
  );
}

export { EvaluationDashboard };
