import type { RunStatus } from "../types/api";

interface StatusBadgeProps {
  status?: RunStatus;
  compact?: boolean;
}

const labels: Record<string, string> = {
  EMPTY: "Empty",
  COMPLETE: "Complete",
  PARTIAL: "Partial",
  NO_EVIDENCE: "No evidence",
  FAILED: "Failed",
};

export function StatusBadge({ status, compact = false }: StatusBadgeProps) {
  const normalized = status ?? "READY";
  const tone = normalized.toLowerCase().replace(/_/g, "-");
  return (
    <span className={`status-badge status-${tone}${compact ? " status-compact" : ""}`}>
      <span className="status-dot" aria-hidden="true" />
      {labels[normalized] ?? (normalized === "READY" ? "Ready" : normalized)}
    </span>
  );
}
