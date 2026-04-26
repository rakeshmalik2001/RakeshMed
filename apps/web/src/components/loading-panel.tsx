"use client";

type LoadingPanelProps = {
  title: string;
  description: string;
};

export function LoadingPanel({ title, description }: LoadingPanelProps) {
  return (
    <div className="loading-panel" aria-live="polite" aria-busy="true">
      <div className="loading-shimmer loading-shimmer-title" />
      <div className="loading-shimmer loading-shimmer-copy" />
      <div className="loading-shimmer loading-shimmer-copy short" />
      <div className="loading-panel-text">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}
