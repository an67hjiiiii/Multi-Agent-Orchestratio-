# Skill provenance

All upstream skills were inspected from temporary read-only shallow clones
before installation. Only the listed directories were copied into the project.

| Skill | Source | Commit | License | Local path |
| --- | --- | --- | --- | --- |
| systematic-debugging | `obra/superpowers` | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` | MIT | `.agents/skills/systematic-debugging` |
| verification-before-completion | `obra/superpowers` | same | MIT | `.agents/skills/verification-before-completion` |
| requesting-code-review | `obra/superpowers` | same | MIT | `.agents/skills/requesting-code-review` |
| dispatching-parallel-agents | `obra/superpowers` | same | MIT | `.agents/skills/dispatching-parallel-agents` |
| writing-skills | `obra/superpowers` | same | MIT | `.agents/skills/writing-skills` |
| agent-architecture-analysis | `existential-birds/beagle` | `d1a74899fbfec74974d1818e4cac7c3d54d44b65` | Apache-2.0 | `.agents/skills/agent-architecture-analysis` |
| rag-retrieval | `yonatangross/orchestkit` | `4d4f547a799ce2c77b38ac65940cb23dbb24f837` | MIT | `.agents/skills/rag-retrieval` |
| local-mrag-governance | project-authored | `1.0.0` | repository policy | `.agents/skills/local-mrag-governance` |

Skipped: `mcp-cli` (`obra/superpowers-lab`, no local `mcp` executable);
`test-driven-development` (only for authorized production behavior changes);
`finding-duplicate-functions` (only audit/pre-freeze/refactor); and all
explicitly disallowed default frameworks/worktree/agent-loop skills.
