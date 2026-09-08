import type { NormalizedUiTask } from "../lib/uiAdapter";
import { StatusBadge } from "./StatusBadge";

/**
 * Group recorded tasks into dependency depth lanes. Unknown dependencies are
 * intentionally ignored here; the backend record remains the source of truth
 * and the UI must not invent an edge to a task it cannot see.
 */
export function buildTaskLayers(tasks: NormalizedUiTask[]): NormalizedUiTask[][] {
  const taskIds = new Set(tasks.map((task) => task.taskId));
  const depthById = new Map<string, number>();
  const visiting = new Set<string>();

  function depth(task: NormalizedUiTask): number {
    const cached = depthById.get(task.taskId);
    if (cached !== undefined) return cached;
    if (visiting.has(task.taskId)) return 0;

    visiting.add(task.taskId);
    const dependencies = task.dependsOn
      .filter((dependency) => taskIds.has(dependency))
      .map((dependency) => tasks.find((candidate) => candidate.taskId === dependency))
      .filter((candidate): candidate is NormalizedUiTask => Boolean(candidate));
    const value = dependencies.length === 0 ? 0 : Math.max(...dependencies.map(depth)) + 1;
    visiting.delete(task.taskId);
    depthById.set(task.taskId, value);
    return value;
  }

  const layers: NormalizedUiTask[][] = [];
  for (const task of tasks) {
    const layer = depth(task);
    layers[layer] ??= [];
    layers[layer].push(task);
  }
  return layers.filter((layer): layer is NormalizedUiTask[] => Boolean(layer?.length));
}

function evidenceLabel(task: NormalizedUiTask): string {
  const count = task.evidenceIds.length || task.citations.length;
  return `${count} ${count === 1 ? "evidence item" : "evidence items"}`;
}

function TaskNode({ task, compact }: { task: NormalizedUiTask; compact: boolean }) {
  return (
    <article className={`task-graph-node${compact ? " task-graph-node-compact" : ""}`}>
      <div className="task-node-heading">
        <code>{task.taskId}</code>
        <StatusBadge status={task.status ?? "UNKNOWN"} compact />
      </div>
      <p>{task.goal ?? "Task goal not recorded"}</p>
      <div className="task-node-meta">
        <span>{task.domain ?? "Domain not recorded"}</span>
        <span>{task.roleProfile ?? "Role not recorded"}</span>
      </div>
      <div className="task-node-footer">
        <span>{evidenceLabel(task)}</span>
        {task.dependsOn.length > 0 && (
          <span className="task-node-dependencies">
            <span aria-hidden="true">↳</span> {task.dependsOn.join(", ")}
          </span>
        )}
      </div>
    </article>
  );
}

export function TaskGraph({ tasks, compact = false }: { tasks: NormalizedUiTask[]; compact?: boolean }) {
  if (tasks.length === 0) {
    return (
      <div className="task-graph-empty" role="status">
        <strong>No task graph recorded</strong>
        <span>This run did not return decomposed task records.</span>
      </div>
    );
  }

  const layers = buildTaskLayers(tasks);

  return (
    <div className={`task-graph${compact ? " task-graph-compact" : ""}`} aria-label="Recorded task dependency graph">
      <div className="task-graph-axis" aria-hidden="true">
        <span>Entry</span>
        <span>Dependency lanes</span>
        <span>Answer</span>
      </div>
      <div className="task-graph-lanes">
        {layers.map((layer, index) => (
          <section className="task-graph-lane" key={`layer-${index}`} aria-labelledby={`task-layer-${index}`}>
            <div className="task-graph-lane-label" id={`task-layer-${index}`}>
              <span>Layer {index + 1}</span>
              <small>{layer.length} {layer.length === 1 ? "task" : "tasks"}</small>
            </div>
            <div className="task-graph-lane-nodes">
              {layer.map((task) => <TaskNode key={task.taskId} task={task} compact={compact} />)}
            </div>
          </section>
        ))}
      </div>
      <p className="task-graph-note">Dependencies are shown only when their task IDs are present in this run.</p>
    </div>
  );
}
