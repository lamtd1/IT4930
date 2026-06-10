import React, { useState } from 'react';
import { Icon } from './Icon';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
  iconRight?: string;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  iconRight,
  onClick,
  disabled,
  type = 'button',
  style,
  title,
  ...rest
}) => {
  const [hover, setHover] = useState(false);

  const sizes = {
    sm: { padding: "6px 11px", fontSize: 13, gap: 6, height: 32 },
    md: { padding: "9px 16px", fontSize: 14, gap: 7, height: 40 },
    lg: { padding: "12px 22px", fontSize: 15, gap: 8, height: 48 },
  }[size];

  const variants = {
    primary: {
      background: hover ? "var(--accent-ink)" : "var(--accent)",
      color: "#fff",
      border: "1px solid transparent",
      boxShadow: "var(--shadow-sm)"
    },
    secondary: {
      background: hover ? "var(--paper-2)" : "var(--surface)",
      color: "var(--ink)",
      border: "1px solid var(--line)"
    },
    ghost: {
      background: hover ? "var(--paper-2)" : "transparent",
      color: "var(--ink-soft)",
      border: "1px solid transparent"
    },
    outline: {
      background: hover ? "var(--accent-wash)" : "transparent",
      color: "var(--accent-ink)",
      border: "1px solid var(--accent-line)"
    },
  }[variant];

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      title={title}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: sizes.gap,
        padding: sizes.padding,
        fontSize: sizes.fontSize,
        height: sizes.height,
        fontWeight: 600,
        borderRadius: "var(--r-md)",
        cursor: disabled ? "not-allowed" : "pointer",
        whiteSpace: "nowrap",
        opacity: disabled ? 0.5 : 1,
        transition: "background .16s, transform .1s, box-shadow .16s",
        fontFamily: "var(--font-sans)",
        ...variants,
        ...style
      }}
      {...rest}
    >
      {icon && <Icon name={icon} size={size === "sm" ? 15 : 17} />}
      {children}
      {iconRight && <Icon name={iconRight} size={size === "sm" ? 15 : 17} />}
    </button>
  );
};
