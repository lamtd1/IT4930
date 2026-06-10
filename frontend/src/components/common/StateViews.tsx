import React from 'react';
import { Icon } from './Icon';
import { Button } from './Button';

interface SpinnerProps {
  size?: number;
}

export const Spinner: React.FC<SpinnerProps> = ({ size = 18 }) => {
  return (
    <span style={{
      width: size,
      height: size,
      border: "2.5px solid var(--line)",
      borderTopColor: "var(--accent)",
      borderRadius: "50%",
      display: "inline-block",
      animation: "spin .7s linear infinite"
    }} />
  );
};

interface StateBoxProps {
  children: React.ReactNode;
}

export const StateBox: React.FC<StateBoxProps> = ({ children }) => {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      padding: "56px 24px",
      gap: 14,
      animation: "fadeIn .3s"
    }}>
      {children}
    </div>
  );
};

interface EmptyStateProps {
  title: string;
  body: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ title, body, action }) => {
  return (
    <StateBox>
      <div style={{
        width: 46,
        height: 46,
        borderRadius: "50%",
        background: "var(--paper-2)",
        border: "1px solid var(--line)",
        display: "grid",
        placeItems: "center",
        color: "var(--ink-faint)"
      }}>
        <Icon name="search" size={20} />
      </div>
      <div>
        <div className="serif" style={{ fontSize: 20, fontWeight: 600 }}>{title}</div>
        <div style={{ color: "var(--ink-mute)", fontSize: 14, marginTop: 4, maxWidth: 380 }}>{body}</div>
      </div>
      {action}
    </StateBox>
  );
};

interface ErrorStateProps {
  error: Error | null;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry }) => {
  return (
    <StateBox>
      <div style={{
        width: 46,
        height: 46,
        borderRadius: "50%",
        background: "oklch(0.95 0.04 30)",
        color: "oklch(0.55 0.16 30)",
        display: "grid",
        placeItems: "center",
        border: "1px solid oklch(0.85 0.07 30)"
      }}>
        <Icon name="info" size={22} />
      </div>
      <div>
        <div className="serif" style={{ fontSize: 20, fontWeight: 600 }}>Something went wrong</div>
        <div style={{ color: "var(--ink-mute)", fontSize: 14, marginTop: 4, maxWidth: 420 }}>
          {(error && error.message) || "We couldn't reach the search service."} Please try again.
        </div>
      </div>
      {onRetry && <Button variant="outline" icon="refresh" onClick={onRetry}>Retry</Button>}
    </StateBox>
  );
};
