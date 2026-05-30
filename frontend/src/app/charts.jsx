// ============================================================
//  charts.jsx — bespoke SVG charts (grouped bar, scatter, radar)
//  All keyed to the shared 5-method color palette.
// ============================================================
import { useState as useStateC, useRef as useRefC, useLayoutEffect } from 'react'
import { METHODS, METHOD_MAP } from './data'

function useWidth() {
  const ref = useRefC(null);
  const [w, setW] = useStateC(720);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(entries => { setW(entries[0].contentRect.width); });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

function MethodLegend({ methods = METHODS, style }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 18px", ...style }}>
      {methods.map(m => (
        <span key={m.id} style={{ display: "inline-flex", alignItems: "center", gap: 7, fontSize: 12.5, color: "var(--ink-soft)" }}>
          <span style={{ width: 11, height: 11, borderRadius: 3, background: m.color }} />
          {m.short}
        </span>
      ))}
    </div>
  );
}

/* ---------- grouped bar: 3 metric groups × 5 method bars ---------- */
function GroupedBarChart({ models }) {
  const [ref, W] = useWidth();
  const H = 320, padL = 38, padR = 12, padT = 18, padB = 46;
  const metrics = [{ key: "p_at_5", label: "P@5" }, { key: "p_at_10", label: "P@10" }, { key: "mrr", label: "MRR" }];
  const [hover, setHover] = useStateC(null);
  const innerW = Math.max(W - padL - padR, 10), innerH = H - padT - padB;
  const groupW = innerW / metrics.length;
  const barGap = 4, groupPad = 0.22;
  const barW = (groupW * (1 - groupPad)) / models.length;
  const yToPx = v => padT + innerH * (1 - v);
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  return (
    <div ref={ref} style={{ width: "100%" }}>
      <svg width={W} height={H} style={{ display: "block", overflow: "visible" }}>
        {ticks.map(t => (
          <g key={t}>
            <line x1={padL} x2={W - padR} y1={yToPx(t)} y2={yToPx(t)} stroke="var(--line-soft)" strokeWidth={1} />
            <text x={padL - 8} y={yToPx(t)} fontSize={10.5} fill="var(--ink-mute)" textAnchor="end" dominantBaseline="middle" fontFamily="var(--font-mono)">{t.toFixed(2)}</text>
          </g>
        ))}
        {metrics.map((metric, gi) => {
          const gx = padL + gi * groupW + (groupW * groupPad) / 2;
          return (
            <g key={metric.key}>
              {models.map((m, mi) => {
                const meta = METHOD_MAP[m.method];
                const v = m[metric.key];
                const x = gx + mi * barW;
                const h = innerH * v;
                const hovered = hover && hover.metric === metric.key && hover.method === m.method;
                return (
                  <g key={m.method} onMouseEnter={() => setHover({ metric: metric.key, method: m.method, v })} onMouseLeave={() => setHover(null)}>
                    <rect x={x + barGap / 2} y={yToPx(v)} width={Math.max(barW - barGap, 2)} height={h}
                      rx={2.5} fill={meta.color} opacity={hover && !hovered ? 0.4 : 1} style={{ transition: "opacity .15s" }} />
                    {hovered && <text x={x + barW / 2} y={yToPx(v) - 6} fontSize={10.5} fill="var(--ink)" textAnchor="middle" fontFamily="var(--font-mono)" fontWeight={600}>{v.toFixed(2)}</text>}
                  </g>
                );
              })}
              <text x={padL + gi * groupW + groupW / 2} y={H - padB + 20} fontSize={13} fill="var(--ink)" textAnchor="middle" fontWeight={600}>{metric.label}</text>
            </g>
          );
        })}
        <line x1={padL} x2={W - padR} y1={yToPx(0)} y2={yToPx(0)} stroke="var(--line)" strokeWidth={1.5} />
      </svg>
    </div>
  );
}

/* ---------- scatter: ms/query (X, log) vs P@5 (Y) ---------- */
function ScatterChart({ models }) {
  const [ref, W] = useWidth();
  const H = 340, padL = 44, padR = 20, padT = 18, padB = 52;
  const [hover, setHover] = useStateC(null);
  const innerW = Math.max(W - padL - padR, 10), innerH = H - padT - padB;
  const xticks = [1, 5, 10, 50, 100, 200];
  const xmin = Math.log10(3), xmax = Math.log10(260);
  const xToPx = ms => padL + innerW * ((Math.log10(ms) - xmin) / (xmax - xmin));
  const yToPx = v => padT + innerH * (1 - (v - 0.3) / (0.9 - 0.3));
  const yticks = [0.3, 0.45, 0.6, 0.75, 0.9];
  const sorted = [...models].sort((a, b) => a.ms_per_query - b.ms_per_query);
  return (
    <div ref={ref} style={{ width: "100%" }}>
      <svg width={W} height={H} style={{ display: "block", overflow: "visible" }}>
        {yticks.map(t => (
          <g key={t}>
            <line x1={padL} x2={W - padR} y1={yToPx(t)} y2={yToPx(t)} stroke="var(--line-soft)" strokeWidth={1} />
            <text x={padL - 8} y={yToPx(t)} fontSize={10.5} fill="var(--ink-mute)" textAnchor="end" dominantBaseline="middle" fontFamily="var(--font-mono)">{t.toFixed(2)}</text>
          </g>
        ))}
        {xticks.map(t => (
          <g key={t}>
            <line x1={xToPx(t)} x2={xToPx(t)} y1={padT} y2={H - padB} stroke="var(--line-soft)" strokeWidth={1} strokeDasharray="2 3" />
            <text x={xToPx(t)} y={H - padB + 16} fontSize={10.5} fill="var(--ink-mute)" textAnchor="middle" fontFamily="var(--font-mono)">{t}</text>
          </g>
        ))}
        {/* tradeoff frontier */}
        <polyline points={sorted.map(m => `${xToPx(m.ms_per_query)},${yToPx(m.p_at_5)}`).join(" ")}
          fill="none" stroke="var(--ink-faint)" strokeWidth={1.4} strokeDasharray="5 4" opacity={0.6} />
        {models.map(m => {
          const meta = METHOD_MAP[m.method];
          const cx = xToPx(m.ms_per_query), cy = yToPx(m.p_at_5);
          const hv = hover === m.method;
          return (
            <g key={m.method} onMouseEnter={() => setHover(m.method)} onMouseLeave={() => setHover(null)} style={{ cursor: "default" }}>
              <circle cx={cx} cy={cy} r={hv ? 9 : 7} fill={meta.color} stroke="var(--surface)" strokeWidth={2} />
              <text x={cx} y={cy - 14} fontSize={11.5} fill="var(--ink)" textAnchor="middle" fontWeight={600}>{meta.short}</text>
              {hv && <text x={cx} y={cy + 20} fontSize={10} fill="var(--ink-mute)" textAnchor="middle" fontFamily="var(--font-mono)">{m.ms_per_query}ms · {m.p_at_5.toFixed(2)}</text>}
            </g>
          );
        })}
        <text x={padL + innerW / 2} y={H - 8} fontSize={11.5} fill="var(--ink-soft)" textAnchor="middle" fontWeight={600}>ms / query (log scale) →</text>
        <text x={14} y={padT + innerH / 2} fontSize={11.5} fill="var(--ink-soft)" textAnchor="middle" fontWeight={600} transform={`rotate(-90 14 ${padT + innerH / 2})`}>P@5 →</text>
      </svg>
    </div>
  );
}

/* ---------- radar: P@5 by genre, one polygon per method ---------- */
function GenreRadarChart({ byGenre, activeMethods }) {
  const [ref, W] = useWidth();
  const size = Math.min(W, 420);
  const H = size;
  const cx = W / 2, cy = H / 2, R = size / 2 - 54;
  const genres = byGenre.map(g => g.genre);
  const n = genres.length;
  const pt = (i, r) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
  };
  const scaleR = v => R * ((v - 0.3) / (0.9 - 0.3));
  const rings = [0.3, 0.45, 0.6, 0.75, 0.9];
  return (
    <div ref={ref} style={{ width: "100%", display: "flex", justifyContent: "center" }}>
      <svg width={W} height={H} style={{ display: "block", overflow: "visible" }}>
        {rings.map((g, gi) => (
          <polygon key={gi} points={genres.map((_, i) => pt(i, scaleR(g)).join(",")).join(" ")} fill="none" stroke="var(--line-soft)" strokeWidth={1} />
        ))}
        {genres.map((_, i) => { const [x, y] = pt(i, R); return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line-soft)" strokeWidth={1} />; })}
        {METHODS.filter(m => activeMethods.includes(m.id)).map(m => {
          const poly = byGenre.map((g, i) => pt(i, scaleR(g.scores[m.id])).join(",")).join(" ");
          return <polygon key={m.id} points={poly} fill={m.color} fillOpacity={0.08} stroke={m.color} strokeWidth={2} strokeLinejoin="round" />;
        })}
        {genres.map((g, i) => {
          const [x, y] = pt(i, R + 22);
          return <text key={i} x={x} y={y} fontSize={11.5} fill="var(--ink-soft)" textAnchor="middle" dominantBaseline="middle" fontWeight={600}>{g}</text>;
        })}
      </svg>
    </div>
  );
}

/* ---------- inline mini-bar for tables ---------- */
function MiniBar({ value, color, max = 1, width = 64 }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span style={{ width, height: 6, background: "var(--paper-2)", borderRadius: 99, overflow: "hidden", border: "1px solid var(--line-soft)" }}>
        <span style={{ display: "block", height: "100%", width: (value / max * 100) + "%", background: color, borderRadius: 99 }} />
      </span>
      <span className="mono" style={{ fontSize: 12.5, color: "var(--ink)", minWidth: 34 }}>{value.toFixed(2)}</span>
    </span>
  );
}

export { MethodLegend, GroupedBarChart, ScatterChart, GenreRadarChart, MiniBar, useWidth };
