import { api } from "../../lib/api";

/** Source and corpus routes owned by the knowledge feature. */
export const knowledgeApi = {
  listSources: api.listSources,
  kbStatus: api.kbStatus,
  getSource: api.getSource,
  getChunk: api.getChunk,
  importText: api.importText,
  importFile: api.importFile,
};
