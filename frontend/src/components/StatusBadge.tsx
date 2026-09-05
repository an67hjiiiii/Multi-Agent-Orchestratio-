import type { RunStatus } from "../types/api";

interface StatusBadgeProps {
  status?: RunStatus;
  compact?: boolean;
}

const labels: Record<string, string> = {
  READY: "Ready",
  CONNECTING: "Connecting",
  RUNNING: "Running",
  COMPLETE: "Complete",
  PARTIAL: "Partial",
  NO_EVIDENCE: "No evidence",
  FAILED: "Failed",
};

const tones: Record<string, string> = {
  READY: "ready",
  CONNECTING: "connecting",
  RUNNING: "running",
  COMPLETE: "complete",
  PARTIAL: "partial",
  NO_EVIDENCE: "no-evidence",
  FAILED: "failed",
};

export function normalizeStatus(status?: RunStatus): string {
  const value = String(status ?? "READY").trim().toUpperCase();
  return value || "READY";
}

export function getStatusLabel(status?: RunStatus): string {
  const normalized = normalizeStatus(status);
  return labels[normalized] ?? normalized.replace(/_/g, " ");
}

export function getStatusTone(status?: RunStatus): string {
  return tones[normalizeStatus(status)] ?? "unknown";
}

export function StatusBadge({ status, compact = false }: StatusBadgeProps) {
  const normalized = normalizeStatus(status);
  const tone = getStatusTone(normalized);
  return (
    <span
      className={`status-badge status-${tone}${compact ? " status-compact" : ""}`}
      role="status"
      aria-label={`Status: ${getStatusLabel(normalized)}`}
    >
      <span className="status-dot" aria-hidden="true" />
      {getStatusLabel(normalized)}
    </span>
  );
}
