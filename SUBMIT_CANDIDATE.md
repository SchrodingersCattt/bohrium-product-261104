# SUBMIT_CANDIDATE

Status: slot 01 attempt 62998 is still in the worker queue past the 30-minute receipt window. Do not submit again, and do not submit slots 02–10, until 62998 has final `scoringDetails`.

| Field | Value |
|---|---|
| Slot | 01 |
| Attempt | 62998 |
| Worker job | 39640 (`status=queued` on upload). No job-read route: `GET /api/jobs/39640` is `not_found`, same as `GET /api`. |
| Package | `submissions/01` (identical to `skills/01-pdf-reading-order`, 13 files, 55361 bytes) |
| Challenge | `product-arena-08-3027d350` |
| Replaces | attempt 62956 |
| CLI | Playground 0.1.39 on PATH. Worker API `http://47.92.88.121:443/api`. Advertised 0.1.40 tarball is HTTP 404. `play.bohrium.com/latest.json` names 0.1.48; that tarball verifies. It was dry-run only, from `/tmp/pg0148`, and was not submitted. |
| Bundle sha256 | `39a0cd1ebfcd2352f779aa11742a75e8865b43b10bda911121f79ff6f99f397a` (the submitted 0.1.39 zip) |
| 0.1.48 dry-run sha256 | `0668d2d39eecce426900962bff5875515efd6b7c960d6149cc4bc3b94937acea` (1488641 bytes, not submitted) |
| What was uploaded | Skill root at `outputs/SKILL.md` and `skills/01/SKILL.md`. ARM entrypoint is the CLI stub `src/reproduce.py`. Zip contains `raw_messages.jsonl` (`type=session_start`). No `package_skill.py`. No `results/skill_inventory.json`. |
| Trace | Cursor session `3fed5113`. Declared model `grok-4.7`, harness `cursor`. 79 steps. Attempt field `rawMessagesAvailable` is still null. |
| Queue snapshot | 2026-11-04T17:24:15Z (1853s after submit): `stage=received`, `workerReceivedAt=null`, `scoringState.state=evaluating`, `workerStatus=evaluating`, `scoreIsFinal=false`, `scoringDetails=null`, `stuckAt=null`. |
| Local proof | `python3 scripts/rehearse_worker_layout.py` exits 0 for slots 01–10 in the `skills/weekly-skill` layout, including bare sidecar passes. `submitted=false`. |

Do not mass `playground submit`. Do not resubmit slot 01 while 62998 is `evaluating`.

### When 62998 becomes final

A zero whose `scoringDetails.source` is still `missing_worker_submission` means this upload did not stick; the job-read route cannot confirm 39640, so the upload response and this queue snapshot are the record. Any other source means the queue accepted the bundle. Read that source before proposing one next slot. Slots 02–10 stay held until then.
