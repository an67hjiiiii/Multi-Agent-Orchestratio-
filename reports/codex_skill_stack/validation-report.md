# Validation report

## Static checks

- `SKILL.md` exists for every manifest `installed` entry: PASS
- Four required routine skills present: PASS
- `writing-skills` present: PASS
- project governance skill present and versioned: PASS
- manifest parses as JSON: PASS
- initial `git diff --check`: PASS
- no production files or canonical state modified: PASS

## Activation checks

These checks are intentionally non-production and do not call Ollama, a live
provider, or a pilot runner.

| ID | Trigger | Required behavior | Result |
| --- | --- | --- | --- |
| A | failing test | debug/root-cause before a fix | PASS — `systematic-debugging` |
| B | completion without tests | demand verification evidence | PASS — `verification-before-completion` |
| C | completion/code-change review | request review discipline | PASS — `requesting-code-review` |
| D | two independent + one dependent work items | parallelize only independents | PASS — `dispatching-parallel-agents` |
| E | start M2 before full M1 approval | block by governance | PASS — `local-mrag-governance` |
| F | cloud fallback | block by governance | PASS — `local-mrag-governance` |
| G | gold-answer leakage | block by governance | PASS — `local-mrag-governance` |

Runtime activation used one disposable, read-only local task after setup. It
reported all eight skills discoverable, matched skill-directory/frontmatter
names, and did not touch files, providers, pilots, worktrees, commits, or push.
