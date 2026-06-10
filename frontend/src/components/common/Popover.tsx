import React, { useState, useEffect, useRef } from 'react';
import { METHODS } from '../../services/api';
import { Icon } from './Icon';

interface PopoverProps {
  trigger: (open: boolean) => React.ReactNode;
  children: React.ReactNode;
  align?: 'left' | 'right';
  width?: number;
}

export const Popover: React.FC<PopoverProps> = ({ trigger, children, align = "right", width = 340 }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [open]);

  return (
    <span ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <span onClick={() => setOpen(o => !o)}>{trigger(open)}</span>
      {open && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 10px)",
          [align]: 0,
          width,
          zIndex: 60,
          background: "var(--surface)",
          border: "1px solid var(--line)",
          borderRadius: "var(--r-lg)",
          boxShadow: "var(--shadow-lg)",
          padding: 16,
          animation: "pop .16s ease-out"
        }}>
          {children}
        </div>
      )}
    </span>
  );
};

export const METHOD_EXPLAIN: Record<string, string> = {
  tfidf: "Scores documents by how often query words appear, down-weighting words common across the corpus. Pure keyword matching — fast, but blind to meaning.",
  bm25: "A refined sparse ranking that adds term-frequency saturation and document-length normalization on top of TF-IDF. The strong classical baseline.",
  semantic: "Embeds query and books into a shared vector space with the BGE-small model and retrieves nearest neighbours from ChromaDB. Matches meaning, not words.",
  hybrid: "Fuses sparse (BM25) and dense (semantic) rankings with Reciprocal Rank Fusion — keyword precision plus semantic recall.",
  reranking: "Runs dense retrieval, then re-scores the top candidates with a heavier cross-encoder for the sharpest ordering. Most accurate, slowest.",
};

export const MethodsExplained: React.FC = () => {
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
};
