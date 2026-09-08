# Human review checklist

Each row is one scenario-level approval unit. The four case IDs are listed so
the reviewer checks variant coverage without creating per-case gold.

| Gold ID | Group ID | Scenario label | Frozen variants | Expected role | Expected domain | Evidence refs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1F-G01 | M1F-S01 | Bearer-token to policy handoff | M1F-S01-V01, M1F-S01-V02, M1F-S01-V03, M1F-S01-V04 | Security Analyst | security | src_ecad6843b8fcb99b_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G02 | M1F-S02 | JWT claims versus server authority | M1F-S02-V01, M1F-S02-V02, M1F-S02-V03, M1F-S02-V04 | Security Analyst | security | src_ecad6843b8fcb99b_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G03 | M1F-S03 | Identity evidence and action permission | M1F-S03-V01, M1F-S03-V02, M1F-S03-V03, M1F-S03-V04 | Security Analyst | security | src_ecad6843b8fcb99b_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G04 | M1F-S04 | Protected REST call security boundary | M1F-S04-V01, M1F-S04-V02, M1F-S04-V03, M1F-S04-V04 | Security Analyst | security | src_ecad6843b8fcb99b_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G05 | M1F-S05 | Server authority with JWT claims | M1F-S05-V01, M1F-S05-V02, M1F-S05-V03, M1F-S05-V04 | Security Analyst | security | src_ecad6843b8fcb99b_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G06 | M1F-S06 | Bearer-token security review scope | M1F-S06-V01, M1F-S06-V02, M1F-S06-V03, M1F-S06-V04 | Security Analyst | security | src_ecad6843b8fcb99b_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G07 | M1F-S07 | Authentication and authorization responsibility map | M1F-S07-V01, M1F-S07-V02, M1F-S07-V03, M1F-S07-V04 | Security Analyst | security | src_ecad6843b8fcb99b_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G08 | M1F-S08 | Token-authenticated protected operation | M1F-S08-V01, M1F-S08-V02, M1F-S08-V03, M1F-S08-V04 | Security Analyst | security | src_ecad6843b8fcb99b_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G09 | M1F-S09 | Access-token lifetime evidence gap | M1F-S09-V01, M1F-S09-V02, M1F-S09-V03, M1F-S09-V04 | Security Analyst | security | NO_EVIDENCE | PENDING_HUMAN_APPROVAL |
| M1F-G10 | M1F-S10 | Multi-factor policy evidence gap | M1F-S10-V01, M1F-S10-V02, M1F-S10-V03, M1F-S10-V04 | Security Analyst | security | NO_EVIDENCE | PENDING_HUMAN_APPROVAL |
| M1F-G11 | M1F-S11 | Identifier-heavy user-record workload | M1F-S11-V01, M1F-S11-V02, M1F-S11-V03, M1F-S11-V04 | Database Analyst | database | src_1055b8f580d99531_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G12 | M1F-S12 | Relational query-path evidence | M1F-S12-V01, M1F-S12-V02, M1F-S12-V03, M1F-S12-V04 | Database Analyst | database | src_1055b8f580d99531_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G13 | M1F-S13 | Multi-write consistency risk | M1F-S13-V01, M1F-S13-V02, M1F-S13-V03, M1F-S13-V04 | Database Analyst | database | src_1055b8f580d99531_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G14 | M1F-S14 | Workload signal for index review | M1F-S14-V01, M1F-S14-V02, M1F-S14-V03, M1F-S14-V04 | Database Analyst | database | src_1055b8f580d99531_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G15 | M1F-S15 | Consistency across a write sequence | M1F-S15-V01, M1F-S15-V02, M1F-S15-V03, M1F-S15-V04 | Database Analyst | database | src_1055b8f580d99531_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G16 | M1F-S16 | Three-layer relational review | M1F-S16-V01, M1F-S16-V02, M1F-S16-V03, M1F-S16-V04 | Database Analyst | database | src_1055b8f580d99531_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G17 | M1F-S17 | Index-change justification | M1F-S17-V01, M1F-S17-V02, M1F-S17-V03, M1F-S17-V04 | Database Analyst | database | src_1055b8f580d99531_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G18 | M1F-S18 | Read workload and write integrity | M1F-S18-V01, M1F-S18-V02, M1F-S18-V03, M1F-S18-V04 | Database Analyst | database | src_1055b8f580d99531_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G19 | M1F-S19 | Database engine evidence gap | M1F-S19-V01, M1F-S19-V02, M1F-S19-V03, M1F-S19-V04 | Database Analyst | database | NO_EVIDENCE | PENDING_HUMAN_APPROVAL |
| M1F-G20 | M1F-S20 | Backup-retention evidence gap | M1F-S20-V01, M1F-S20-V02, M1F-S20-V03, M1F-S20-V04 | Database Analyst | database | NO_EVIDENCE | PENDING_HUMAN_APPROVAL |
| M1F-G21 | M1F-S21 | REST caller-facing boundary | M1F-S21-V01, M1F-S21-V02, M1F-S21-V03, M1F-S21-V04 | API/Architecture Analyst | api_architecture | src_c7f92b35e6b484c5_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G22 | M1F-S22 | Producer-consumer dependency contract | M1F-S22-V01, M1F-S22-V02, M1F-S22-V03, M1F-S22-V04 | API/Architecture Analyst | api_architecture | src_c7f92b35e6b484c5_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G23 | M1F-S23 | Input validation and failure semantics | M1F-S23-V01, M1F-S23-V02, M1F-S23-V03, M1F-S23-V04 | API/Architecture Analyst | api_architecture | src_c7f92b35e6b484c5_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G24 | M1F-S24 | Validation and authorization contract fields | M1F-S24-V01, M1F-S24-V02, M1F-S24-V03, M1F-S24-V04 | API/Architecture Analyst | api_architecture | src_c7f92b35e6b484c5_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G25 | M1F-S25 | Integration dependency trace | M1F-S25-V01, M1F-S25-V02, M1F-S25-V03, M1F-S25-V04 | API/Architecture Analyst | api_architecture | src_c7f92b35e6b484c5_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G26 | M1F-S26 | Three-part REST contract review | M1F-S26-V01, M1F-S26-V02, M1F-S26-V03, M1F-S26-V04 | API/Architecture Analyst | api_architecture | src_c7f92b35e6b484c5_c0000 | PENDING_HUMAN_APPROVAL |
| M1F-G27 | M1F-S27 | Rate-limit evidence gap | M1F-S27-V01, M1F-S27-V02, M1F-S27-V03, M1F-S27-V04 | API/Architecture Analyst | api_architecture | NO_EVIDENCE | PENDING_HUMAN_APPROVAL |
| M1F-G28 | M1F-S28 | Request-timeout evidence gap | M1F-S28-V01, M1F-S28-V02, M1F-S28-V03, M1F-S28-V04 | API/Architecture Analyst | api_architecture | NO_EVIDENCE | PENDING_HUMAN_APPROVAL |
| M1F-G29 | M1F-S29 | API-versioning evidence gap | M1F-S29-V01, M1F-S29-V02, M1F-S29-V03, M1F-S29-V04 | API/Architecture Analyst | api_architecture | NO_EVIDENCE | PENDING_HUMAN_APPROVAL |
| M1F-G30 | M1F-S30 | Request-size evidence gap | M1F-S30-V01, M1F-S30-V02, M1F-S30-V03, M1F-S30-V04 | API/Architecture Analyst | api_architecture | NO_EVIDENCE | PENDING_HUMAN_APPROVAL |

Reviewer: ____________________    Date: ____________________

Approval rule: set a row to `APPROVED` only after reviewing all four variants,
the resolved corpus evidence, and the scenario answer summary. Keep all Human
fields blank while the packet is pending. No agent may self-approve.
