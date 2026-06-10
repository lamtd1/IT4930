import React from 'react';

const ICON_PATHS: Record<string, string> = {
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

interface IconProps {
  name: string;
  size?: number;
  stroke?: number;
  fill?: boolean;
  style?: React.CSSProperties;
}

export const Icon: React.FC<IconProps> = ({ name, size = 18, stroke = 1.7, fill = false, style }) => {
  const d = ICON_PATHS[name];
  if (!d) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24"
      fill={fill ? "currentColor" : "none"} stroke={fill ? "none" : "currentColor"}
      strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
      style={{ flexShrink: 0, ...style }}>
      <path d={d} />
    </svg>
  );
};
