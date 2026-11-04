# SUBMIT_CANDIDATE

Status: slot 01 is submitted and sitting in the worker queue. Do not submit slots 02–10 until attempt 62998 has `scoringDetails` and that source is not `missing_worker_submission`.

| Field | Value |
|---|---|
| Slot | 01 |
| Attempt | 62998 |
| Worker job | 39640 (`status=queued` on upload) |
| Package | `submissions/01` (identical to `skills/01-pdf-reading-order`, 13 files, 55361 bytes) |
| Challenge | `product-arena-08-3027d350` |
| Replaces | attempt 62956 |
| CLI | Playground 0.1.39. Worker API `http://47.92.88.121:443/api`. |
| Bundle sha256 | `39a0cd1ebfcd2352f779aa11742a75e8865b43b10bda911121f79ff6f99f397a` |
| What was uploaded | Skill root at `outputs/SKILL.md` and `skills/01/SKILL.md`. ARM entrypoint is the CLI stub `src/reproduce.py`. No `package_skill.py`. No `results/skill_inventory.json`. |
| Trace | Cursor session `3fed5113` (the session that built the skill). Declared model `grok-4.7`, harness `cursor`. 79 steps after CLI normalization. |
| Queue snapshot | ~20s: `stage=queued`, `queuePosition=17`. ~90s: `stage=received`, `scoringState.state=evaluating`, `workerStatus=evaluating`, `scoreIsFinal=false`, `scoringDetails` still empty. |
| Local proof | `python3 scripts/rehearse_worker_layout.py` → `status=success`, 10 blocks, validator `ok`, `submitted=false`. |

Do not mass `playground submit`.

### If 62998 comes back zero

A zero whose `scoringDetails.source` is still `missing_worker_submission` means this upload did not stick; inspect job 39640 before any new attempt. Any other source means the queue accepted the bundle. The likely follow-up is the trace: the CLI stored the cursor JSONL as thoughts, not as paired tool calls, and it recorded no token cost. Hidden cases are still unseen.
