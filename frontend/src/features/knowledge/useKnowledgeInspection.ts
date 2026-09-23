import { useState } from "react";
import { knowledgeApi } from "./api";
import type { SourceChunk, SourceDetail, SourceSummary } from "../../types/api";

export interface KnowledgeInspectionState {
  selectedSource: SourceDetail | null;
  sourceLoadingId: string | null;
  sourceError: string | null;
  selectedChunk: SourceChunk | null;
  chunkError: string | null;
  inspectSource: (source: SourceSummary) => Promise<void>;
  inspectKnownChunk: (chunk: SourceChunk) => void;
  inspectCitation: (citation: string) => Promise<void>;
  closeSource: () => void;
  closeChunk: () => void;
  dismissSourceError: () => void;
  dismissChunkError: () => void;
}

/** Keeps source/chunk inspection state out of the product shell. */
export function useKnowledgeInspection(): KnowledgeInspectionState {
  const [selectedSource, setSelectedSource] = useState<SourceDetail | null>(null);
  const [sourceLoadingId, setSourceLoadingId] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<SourceChunk | null>(null);
  const [chunkError, setChunkError] = useState<string | null>(null);

  async function inspectSource(source: SourceSummary) {
    setSourceLoadingId(source.source_id);
    setSourceError(null);
    try {
      setSelectedSource(await knowledgeApi.getSource(source.source_id));
    } catch (cause) {
      setSelectedSource(null);
      setSourceError(cause instanceof Error ? cause.message : "Unable to load this source");
    } finally {
      setSourceLoadingId(null);
    }
  }

  function inspectKnownChunk(chunk: SourceChunk) {
    setChunkError(null);
    setSelectedChunk(chunk);
  }

  async function inspectCitation(citation: string) {
    setChunkError(null);
    setSelectedChunk(null);
    try {
      setSelectedChunk(await knowledgeApi.getChunk(citation));
    } catch (cause) {
      setChunkError(cause instanceof Error ? cause.message : "Unable to load this source context");
    }
  }

  return {
    selectedSource,
    sourceLoadingId,
    sourceError,
    selectedChunk,
    chunkError,
    inspectSource,
    inspectKnownChunk,
    inspectCitation,
    closeSource: () => setSelectedSource(null),
    closeChunk: () => setSelectedChunk(null),
    dismissSourceError: () => setSourceError(null),
    dismissChunkError: () => setChunkError(null),
  };
}
