# Skill conflict report

## Result

No blocking name collision was found in inspected discoverable roots.

| Topic | Disposition |
| --- | --- |
| Upstream workflow conflicts | Repository `AGENTS.md` and `local-mrag-governance` are higher-priority project controls. They prohibit unauthorized pilots, cloud inference, push, scope expansion, and self-approval. |
| Parallel execution | `dispatching-parallel-agents` is constrained by one production writer per wave and serial GPU/model runs. |
| Worktrees | No `using-git-worktrees` skill was installed; no worktree was created. |
| TDD | `test-driven-development` remains conditional and uninstalled because this setup changes no production behavior. |
| MCP CLI | `mcp-cli` remains skipped because no CLI is installed; adding dependencies is out of scope. |
| Duplicate-function audit | `finding-duplicate-functions` remains conditional and uninstalled; no refactor/pre-freeze audit was authorized. |

No production file, canonical project state, pilot artifact, or existing skill
was overwritten or removed.
