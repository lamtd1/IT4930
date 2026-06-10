import React, { useState } from 'react';

interface CoverImageProps {
  book: { title: string; authors: string; thumbnail?: string | null };
  size?: 'card' | 'large' | 'mini';
}

export const CoverImage: React.FC<CoverImageProps> = ({ book, size = "card" }) => {
  const [errored, setErrored] = useState(false);

  const dims = {
    card: { w: "100%", aspect: "2 / 3", radius: "var(--r-sm)", fs: 12, label: 11 },
    large: { w: "100%", aspect: "2 / 3", radius: "var(--r-md)", fs: 17, label: 12 },
    mini: { w: "100%", aspect: "2 / 3", radius: 4, fs: 10, label: 9 },
  }[size];

  const showFallback = !book.thumbnail || errored;

  if (showFallback) {
    const primaryAuthor = book.authors ? book.authors.split(",")[0] : 'Unknown';
    return (
      <div style={{
        width: dims.w,
        aspectRatio: dims.aspect,
        borderRadius: dims.radius,
        overflow: "hidden",
        position: "relative",
        background: "var(--paper-2)",
        border: "1px solid var(--line)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: size === "mini" ? 7 : 12
      }}>
        <div style={{
          position: "absolute",
          inset: 0,
          opacity: 0.5,
          backgroundImage: "repeating-linear-gradient(135deg, var(--line-soft) 0 7px, transparent 7px 15px)"
        }} />
        <div style={{
          position: "relative",
          fontFamily: "var(--font-mono)",
          fontSize: dims.label,
          color: "var(--ink-mute)",
          textTransform: "uppercase",
          letterSpacing: ".06em"
        }}>no cover</div>
        <div style={{ position: "relative" }}>
          <div className="serif" style={{
            fontSize: dims.fs,
            fontWeight: 600,
            color: "var(--ink-soft)",
            lineHeight: 1.25,
            display: "-webkit-box",
            WebkitLineClamp: 4,
            WebkitBoxOrient: "vertical",
            overflow: "hidden"
          }}>{book.title}</div>
          <div style={{ fontSize: dims.label, color: "var(--ink-mute)", marginTop: 5 }}>{primaryAuthor}</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      width: dims.w,
      aspectRatio: dims.aspect,
      borderRadius: dims.radius,
      overflow: "hidden",
      background: "var(--paper-2)",
      border: "1px solid var(--line)"
    }}>
      <img
        src={book.thumbnail || undefined}
        alt={book.title}
        loading="lazy"
        onError={() => setErrored(true)}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
      />
    </div>
  );
};
