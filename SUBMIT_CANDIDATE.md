# SUBMIT_CANDIDATE

Status: slot 01 attempt **62998** is Harbor **`evaluation_error`** (no numeric reward). Diagnosis is written in `DECISIONS.md`. Do **not** submit slots 02–10. Do **not** resubmit slot 01 on this pass.

| Field | Value |
|---|---|
| Slot | 01 |
| Attempt | 62998 |
| Challenge | `product-arena-08-3027d350` |
| Replaces | 62956 |
| Package | `submissions/01` |
| CLI used | Playground **0.1.39** inlined 79 flattened steps and left `rawMessagesAvailable` null. 0.1.48 dry-run only |
| Worker job (upload) | 39640 |
| Live status | `pending_review` / `execStatus=failed` / `scoringState.state=failed` / `scoreIsFinal=false` |
| Harbor | `harbor_status=evaluation_error`, `harbor_replay_executed=1`, `harbor_errors=0`, `harbor_reward=null`, `scoringDetails=null` |
| Duration | 41 min (`2026-11-04T16:53:22Z` → `2026-11-04T17:34:33Z`) |
| Baseline contrast | 62955–62964 were `missing_worker_submission`. Graded peers on this challenge (62715, 62879, 62982) have `harbor_status=scored` and a numeric reward |

### Why this is not a resubmit yet
`evaluation_error` means the Harbor job produced no reward mean. It is not a scored zero. The same status already hit CLI 0.1.48 arena-08 attempts that did attach raw messages (62865, 62892, 62906, 62943, 62947) after 44–49 minutes. 0.1.48 dry-run of this cursor session still flattens 224 `tool_use` blocks into 79 thoughts, cost 0, one timestamp. Forcing `type=role` yields 224 unpaired tool calls and was rejected as a submit trace.

### Local fix already in the tree (not uploaded)
`parse_pdf.py` now writes `app/output/result.json` when both extractors fail. Proven: broken PDF → `status=undetermined`; `run_example.py` and `scripts/rehearse_worker_layout.py` exit 0. 0.1.48 dry-run of that tree: sha256 `8a3499d932cbd7039814f4ea43447d8c3fce0ef4660612404fe443eb2a7471b5`, 1492637 bytes, not submitted.

### Next single action (when ready)
One slot-01 `playground` **0.1.48** submit of `submissions/01` only after a trace that keeps tool-call pairs, or an explicit decision that the flattened cursor session is acceptable. Hold 02–10.
