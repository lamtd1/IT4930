import React, { useMemo } from 'react';
import { EMOTION_META, METHOD_MAP } from '../../services/api';

interface BadgeProps {
  children: React.ReactNode;
  color?: string;
  tone?: 'neutral' | 'accent' | 'good';
  style?: React.CSSProperties;
}

export const Badge: React.FC<BadgeProps> = ({ children, color, tone = "neutral", style }) => {
  const tones = {
    neutral: { background: "var(--paper-2)", color: "var(--ink-soft)", border: "1px solid var(--line)" },
    accent: { background: "var(--accent-wash)", color: "var(--accent-ink)", border: "1px solid var(--accent-line)" },
    good: { background: "var(--good-wash)", color: "var(--good)", border: "1px solid transparent" },
  }[tone];

  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      padding: "2px 9px",
      borderRadius: 99,
      fontSize: 12,
      fontWeight: 600,
      fontFamily: "var(--font-sans)",
      lineHeight: 1.7,
      ...tones,
      ...style
    }}>
      {color && <span style={{ width: 7, height: 7, borderRadius: 99, background: color, flexShrink: 0 }} />}
      {children}
    </span>
  );
};

interface EmotionBadgeProps {
  emotion: string;
  score?: number;
}

export const EmotionBadge: React.FC<EmotionBadgeProps> = ({ emotion, score }) => {
  const m = EMOTION_META[emotion];
  if (!m) return null;
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 5,
      padding: "2px 8px 2px 6px",
      borderRadius: 99,
      fontSize: 11.5,
      fontWeight: 600,
      background: "var(--paper-2)",
      border: "1px solid var(--line)",
      color: "var(--ink-soft)"
    }}>
      <span style={{ width: 8, height: 8, borderRadius: 99, background: m.color }} />
      {m.label}
      {score != null && <span className="mono" style={{ color: "var(--ink-mute)", fontSize: 10.5, marginLeft: 2 }}>{score.toFixed(2)}</span>}
    </span>
  );
};

interface MethodChipProps {
  method: string;
  showType?: boolean;
  size?: 'sm' | 'md';
}

export const MethodChip: React.FC<MethodChipProps> = ({ method, showType = false, size = "md" }) => {
  const m = METHOD_MAP[method] || { label: method, color: 'var(--ink-soft)', type: '' };
  const fs = size === "sm" ? 11.5 : 12.5;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
      <span style={{ width: 9, height: 9, borderRadius: 3, background: m.color, flexShrink: 0 }} />
      <span style={{ fontWeight: 600, fontSize: fs }}>{m.label}</span>
      {showType && m.type && <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-mute)", textTransform: "uppercase", letterSpacing: ".04em" }}>{m.type}</span>}
    </span>
  );
};

interface StarRatingProps {
  value: number;
  size?: number;
}

const STAR_PATH = "M12 3.5l2.6 5.27 5.82.85-4.21 4.1.99 5.78L12 16.77 6.8 19.5l.99-5.78-4.21-4.1 5.82-.85z";

export const StarRating: React.FC<StarRatingProps> = ({ value, size = 15 }) => {
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
            <path
              key={i}
              transform={`translate(${i * (size + 2)} 0) scale(${size / 24})`}
              d={STAR_PATH}
              fill={`url(#${id})`}
            />
          ))}
        </svg>
      </span>
    </span>
  );
};
