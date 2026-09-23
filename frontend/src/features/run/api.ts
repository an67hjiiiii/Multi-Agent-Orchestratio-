import { api } from "../../lib/api";

/** Run, runtime, and bounded planning routes owned by the run feature. */
export const runApi = {
  health: api.health,
  config: api.config,
  localModelHealth: api.localModelHealth,
  listRuns: api.listRuns,
  getRun: api.getRun,
  chat: api.chat,
  decompose: api.decompose,
};
