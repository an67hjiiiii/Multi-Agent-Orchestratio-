import type { ReactNode } from "react";
import { StatusBadge } from "./StatusBadge";

export interface TaskItem {
  task_id: string;
  title: string;
  objective: string;
  expected_output: string;
  domain: string;
  role_profile: string;
  depends_on: string[];
}

export interface DecompositionResult {
  request: string;
  tasks: TaskItem[];
  planning_evidence_ids: string[];
  status: string;
  warnings: string[];
}

export interface TaskResultPanelProps {
  result?: DecompositionResult | null;
  error?: string | null;
}

function displayValue(value: string | undefined | null) {
  return value?.trim() || "—";
}

function cleanList(values: string[]) {
  return values.filter((value) => value.trim());
}

function taskHeadingId(taskId: string, position: number) {
  const safeTaskId = taskId.trim().replace(/[^a-zA-Z0-9_-]/g, "-") || "task";
  return `task-result-${position}-${safeTaskId}-title`;
}

function TaskField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="evidence-row">
      <span>{label}</span>
      <span className="task-field-value">{children}</span>
    </div>
  );
}

function PanelState({
  title,
  copy,
  role,
}: {
  title: string;
  copy: string;
  role?: "alert" | "status";
}) {
  return (
    <div className="inspector-empty" role={role}>
      <strong>{title}</strong>
      <span>{copy}</span>
    </div>
  );
}

function Warnings({ warnings }: { warnings: string[] }) {
  const visibleWarnings = cleanList(warnings);
  if (visibleWarnings.length === 0) return null;

  return (
    <div className="answer-note" role="note" aria-labelledby="task-result-warnings-title">
      <strong id="task-result-warnings-title">Warnings</strong>
      <ul>
        {visibleWarnings.map((warning, index) => (
          <li key={`${warning}-${index}`}>{warning}</li>
        ))}
      </ul>
    </div>
  );
}

function TaskCard({ task, position }: { task: TaskItem; position: number }) {
  const dependencies = cleanList(task.depends_on);
  const headingId = taskHeadingId(task.task_id, position);

  return (
    <li className="source-card">
      <div className="source-card-heading">
        <h3 id={headingId} className="source-name">
          {displayValue(task.title)}
        </h3>
        <code className="evidence-id">{displayValue(task.task_id)}</code>
      </div>

      <div className="source-card-meta">
        {displayValue(task.domain)} · {displayValue(task.role_profile)}
      </div>

      <div aria-labelledby={headingId}>
        <TaskField label="Title">{displayValue(task.title)}</TaskField>
        <TaskField label="Objective">{displayValue(task.objective)}</TaskField>
        <TaskField label="Expected output">{displayValue(task.expected_output)}</TaskField>
        <TaskField label="Domain">{displayValue(task.domain)}</TaskField>
        <TaskField label="Role profile">{displayValue(task.role_profile)}</TaskField>
        <div className="evidence-row">
          <span>Depends on</span>
          <span className="task-field-value">
            {dependencies.length === 0 ? (
              "No dependencies"
            ) : (
              <ul aria-label={`Dependencies for ${displayValue(task.task_id)}`}>
                {dependencies.map((dependency) => (
                  <li key={dependency}>
                    <code className="evidence-id">{dependency}</code>
                  </li>
                ))}
              </ul>
            )}
          </span>
        </div>
      </div>
    </li>
  );
}

export function TaskResultPanel({ result, error }: TaskResultPanelProps) {
  const errorMessage = error?.trim();

  if (errorMessage) {
    return (
      <section className="inspector-list" aria-label="Task inspection">
        <PanelState title="Unable to load task plan" copy={errorMessage} role="alert" />
      </section>
    );
  }

  if (!result) {
    return (
      <section className="inspector-list" aria-label="Task inspection">
        <PanelState
          title="No task plan selected"
          copy="A structured task plan will appear after a planning run."
          role="status"
        />
      </section>
    );
  }

  const warnings = cleanList(result.warnings);

  return (
    <section className="inspector-list" aria-labelledby="task-result-panel-title">
      <div className="source-card">
        <div className="source-card-heading">
          <div>
            <p className="eyebrow">Task inspection</p>
            <h2 id="task-result-panel-title">Task plan</h2>
          </div>
          <StatusBadge status={result.status || "UNKNOWN"} />
        </div>

        <TaskField label="Request">{displayValue(result.request)}</TaskField>
        <Warnings warnings={warnings} />
      </div>

      {result.tasks.length === 0 ? (
        <PanelState
          title="No tasks returned"
          copy={
            warnings.length > 0
              ? "Review the warnings above for more detail."
              : "The planning result contains no task items."
          }
          role="status"
        />
      ) : (
        <ol className="inspector-list" aria-label="Decomposed tasks">
          {result.tasks.map((task, index) => (
            <TaskCard key={`${task.task_id || "task"}-${index}`} task={task} position={index + 1} />
          ))}
        </ol>
      )}
    </section>
  );
}
