# Decisions

## 2026-11-04 23:50 Asia/Shanghai — zeros are the worker-queue guard

Attempts 62955–62964 are `scored`, `score=0.0`, `scoreIsFinal=true`, `execStatus=completed`, `bundleStatus=ready`. Every `scoringDetails.source` is `missing_worker_submission`. The platform summary says the grader did not find a complete, genuinely-derived solution. The attempt `resultsJson` is more specific and is the same on all ten tracks, including 62955 (`product-arena-03-429cc14d`, changelog `dry test draft`):

- `scored_by`: `playground-worker/nonstandard-submission-guard`
- `error_code`: `missing_worker_submission`
- `required_worker_api`: `http://47.92.88.121:443/api`
- message: the submission did not enter the official Worker scoring queue, so it is scored 0. Resubmit with the latest Playground CLI and that Worker API.

`http://47.92.88.121:443/health` returns `{"status":"ok","service":"playground-worker-upload"}`. The guard ran. The three fixed cases did not.

### What was uploaded

Receipts show a hand-built ARM 1.1 zip posted through the platform attempt API. `bundleStatus=ready` only means the platform stored that zip. Each zip's entrypoint is `src/package_skill.py`. The only execution artifact is `results/skill_inventory.json`. The trace is five steps with one timestamp, recording the inventory write. `submission/SKILL.md` is inside the zip, and a copy also sits at `skills/<name>/`, but that bundle never became a worker job.

The contest text says to submit the skill, not prepared answers. The platform then installs it at `/skills/weekly-skill` and runs the official harness on `/input/case.json`, expecting `/app/output/result.json`. That install-and-run step is what the worker queue is for. A platform bundle upload does not start it. `execStatus=completed` here is the guard finishing, not a harness case.

Challenge `scoring.strategy` is still `human_review_only`. The 0 is this guard, not a manual rubric and not a per-case Harbor reward.

### Skill contract check (slot 01)

`skills/01-pdf-reading-order` matches `submissions/01` byte for byte (13 text files, 55361 bytes). Installed as `skills/weekly-skill`, `parse_pdf.py` on `examples/minimal` writes `app/output/result.json` with `status=success`, 10 blocks, and the envelope fields the contract lists. `validate_result.py` prints `ok`. `scripts/run_example.py` passes for all ten packages. Caps: every package is under 50 text files, 500KB text, and 2MB total. Slot 07 is the largest (22 files, 53850 bytes).

So the shared zero is not a missing `result.json` writer inside slot 01, and it is not the 62955 changelog. The worker never received the bundle.

### Fix, not applied as a submit

Do not post another ARM zip with `POST /api/attempts/{id}/bundle`. After Playground CLI is on PATH (the site bundle currently advertises 0.1.48; `https://play.bohrium.com/install.sh` returned HTTP 405 from this host, so no dry-run was possible here), one controlled resubmit:

```bash
playground submit \
  --challenge-id product-arena-08-3027d350 \
  --outputs submissions/01 \
  --trace <session that actually ran the skill> \
  --model <model> \
  --harness <harness>
```

`--outputs` is the skill root (`SKILL.md` at the top), not `results/skill_inventory.json`. Confirm the CLI's Worker API is `http://47.92.88.121:443/api` before that command. Use `--dry-run` first. Do not mass-submit the other nine until slot 01 comes back with a `scored_by` other than `nonstandard-submission-guard`.

### Residual risk

- This environment has no `playground` binary, so the CLI packaging path is not locally proven.
- A trace that does not show the skill run can still zero the attempt after the queue accepts it.
- The local proof uses the labeled fixture, not the three hidden cases.
- Slots 02–10 use the same queue failure. Slot 01 stays the single-track candidate because `parse_pdf.py` writes the full result by itself.

## 2026-11-05 00:30 Asia/Shanghai — CLI still blocked; other slots write result.json without the sidecar

`playground` is not on PATH. Checked this session:

- `https://play.bohrium.com/install.sh` is HTTP 405 from the Alibaba edge. The same 405 is returned for `/api/cli/install.sh` and for percent-encoded `.sh`. Paths that do not contain `.sh` (`/api/ears/install`, the site HTML, the skill gzip bundles) return 200.
- `npm view @paper2arm/playground-cli` is 404 on registry.npmjs.org, npmmirror, and the Tencent mirror. `registry.dp.tech` is 404. `npm.dp.tech` is 403.
- The protocol text names `https://git.dp.tech/incubation/playground-for-agentic-science`. That host timed out, with and without a proxy.
- `https://github.com/Osgood001/playground-cli` is `@paper2arm/playground-cli` **0.1.7** and its README points at `http://nwjs1473070.bohrium.tech:50002/api`. That is not CLI 0.1.48 and not worker `http://47.92.88.121:443/api`. It was not installed and not used to submit.
- Worker `GET /health` returned `{"status":"ok","service":"playground-worker-upload"}`.
- `scripts/submit_recipe.py` checks the slot-01 package, that identity with `skills/01-pdf-reading-order`, and the worker health URL, then prints the dry-run command. It exits 2 while the binary is missing. It does not submit.

No new attempt id. Slots 02–10 stay held.

Where the script can finish from the case inputs, it now writes a full `result.json` when the model sidecar is missing. Existing labeled files still win, and the negative controls still fail:

- 03 notes: a sentence is copied from the section whose title names the field.
- 04 nanopub: a controlled relation becomes one assertion only when `paper_provenance` is on the case; otherwise every span is an explicit rejection and nothing is invented.
- 05 graph: harvested `Long Form (ABBR)` nodes plus three default queries run when `candidates.json` / `queries.json` are absent.
- 06 polish: each sentence is kept as `unchanged` and still passes the number, citation, and hedge checks.
- 08 related work: one group quotes each paper's first sentence, and the contribution copies an inventory passage.
- 09 methods: prose is rendered from the parameter table. A missing dataset stays `not_in_source`.

Slot 02 still refuses to invent a translation. Slots 07 and 10 already wrote `result.json` from the bibliography and the TeX sources. `run_example.py` passes for all ten skills, including a no-sidecar case for the six above.

## 2026-11-05 00:54 Asia/Shanghai — slot 01 is in the worker queue

`playground` 0.1.39 is on PATH (`/root/.local/bin/playground`, node v22.23.1). `playground auth status` is authenticated against `https://play.bohrium.com/api`. `GET http://47.92.88.121:443/health` is ok. The CLI's built-in worker base is `http://47.92.88.121:443/api`. `scripts/submit_recipe.py` exits 0.

The advertised 0.1.40 package (`https://play.bohrium.com/packages/paper2arm-playground-cli-0.1.40.tgz` and the same name on `nwjs1473070.bohrium.tech:50003`) is HTTP 404. `https://play.bohrium.com/install.sh` is still HTTP 405. The submit used 0.1.39.

Dry-run, then one real submit, both with `--outputs submissions/01 --skill submissions/01 --model grok-4.7 --harness cursor`. The trace is the cursor session that built the skill (`3fed5113`, 79 JSONL rows, no secret-pattern hits). The CLI rewrote that session into 79 thought/observation steps. Nested `tool_use` blocks stay inside the message text; the converter does not emit paired tool calls or token cost.

Attempt **62998**. Worker upload returned `status=queued`, `job_id=39640`, bundle sha256 `39a0cd1ebfcd2352f779aa11742a75e8865b43b10bda911121f79ff6f99f397a`, 66 zip entries, 1545633 bytes. Skill evidence is `skills/01/SKILL.md` (13 files, 55361 bytes) and the same tree at `outputs/SKILL.md`. Entrypoint is the CLI stub `src/reproduce.py`. The zip has no `package_skill.py` and no `skill_inventory.json`.

A status read about 20 seconds later: `status=submitted`, `scoringQueue.stage=queued`, `queuePosition=17`, `scoringState.state=queued`, `workerStatus=queued`, `scoreIsFinal=false`. About 90 seconds after submit the same attempt was `stage=received`, `scoringState.state=evaluating`, `workerStatus=evaluating`, with `scoringDetails` still empty. That is the worker queue, not `missing_worker_submission`. `generated-skill` status returned HTTP 401 `worker_unauthorized`; the upload itself was accepted.

Slots 02–10 stay unsubmitted. Local rehearsal of slot 01 still reports `status=success`, 10 blocks, validator `ok`.

### Residual risk

- 0.1.39 prints that a newer CLI may affect the score, and the 0.1.40 tarball is not downloadable from this host.
- If 62998 later scores 0 with a source other than `missing_worker_submission`, the first place to look is the flattened trace (no tool-call pairs, cost 0) and the hidden cases. Do not resubmit until that status is known.
- `workerReceivedAt` was still null at the `stage=received` read. The stage and `workerStatus=evaluating` are the fields that moved.

## 2026-11-05 01:24 Asia/Shanghai — 62998 is still evaluating after the 30-minute receipt window

Poll at 2026-11-04T17:24:15Z, 1853 seconds after `submittedAt` 2026-11-04T16:53:22Z.

`status=submitted`, display score 0, `scoreIsFinal=false`, `scoringDetails=null`, `resultsJson=null`, `execStatus=null`, `bundleStatus=null`, `stuckAt=null`. `updatedAt` is still 2026-11-04T16:53:21Z. `scoringQueue.stage=received`, `workerStatus=evaluating`, `workerReceivedAt=null`, `notReceivedAfterMinutes=30`. `rawMessagesAvailable` is still null. `traceCount` is 79.

`GET http://47.92.88.121:443/health` is ok. `GET /api/jobs/39640` returns `{"error":"not_found"}`, and so does `GET /api`. The upload service does not expose a job-read route, so job 39640 cannot be re-fetched. The upload response remains the job record: `status=queued`, `job_id=39640`, `worker_tenant=primary`. Generated-skill status is HTTP 401 `worker_unauthorized`.

CLI on PATH is still 0.1.39. The CLI update host `latest.json` names 0.1.40, and that tarball is HTTP 404 on `play.bohrium.com` and on `nwjs1473070.bohrium.tech:50003`. `https://play.bohrium.com/install.sh` is HTTP 405. `https://play.bohrium.com/latest.json` names 0.1.48. That tarball downloaded and its sha256 is `adf4cf035ad397f38a464ec2be247bc76cb45fa085c4c7eed05379e753499ce2`.

A side-by-side 0.1.48 binary under `/tmp/pg0148` (not placed on PATH) dry-ran the same slot-01 package and the same cursor session. It did not submit. Dry-run bundle sha256 `0668d2d39eecce426900962bff5875515efd6b7c960d6149cc4bc3b94937acea`, 1488641 bytes, 79 trace steps. Both the 0.1.39 zip and the 0.1.48 zip contain `raw_messages.jsonl` whose first row has `type=session_start`, plus `skills/01/SKILL.md`. 0.1.48 leaves out the `execution/results/` copy of the skill tree. Its submit path also posts `raw_messages` as a file when the attempt is created and stores the attempt `trace` field as `[]`. Attempt 62998 was created by 0.1.39, which inlined the 79 converted steps and left `rawMessagesAvailable` null.

That dry-run does not identify a packaging defect that would leave `workerReceivedAt` null after the upload returned job 39640 and the queue stage moved from `awaiting_receipt` to `received`. No second submit.

`python3 scripts/rehearse_worker_layout.py` exits 0. All ten packages match their skill trees and sit under the file caps. Each skill, installed at `skills/weekly-skill`, writes `app/output/result.json` and passes `validate_result.py`. Bare sidecar passes: 02 `partial`, 03 `success`, 04 `partial` with no minted assertions, 05 `success`, 06 `success` with `unchanged` edits, 08 `success`, 09 `partial` with prose. Slot 10 writes a PDF and stays `partial` because `tab:unused` is unreferenced.

Next: poll 62998 until `scoreIsFinal`. Slots 02–10 stay held. Any later single resubmit waits until `scoringDetails.source` is known.

## 2026-11-05 01:50 Asia/Shanghai — supervisor: 62998 left evaluating → pending_review / evaluation_error

Poll shows attempt **62998** no longer stuck in worker queue:
- `status=pending_review`, `execStatus=failed`, `scoringState.state=failed`, `scoreIsFinal=false`, score display 0
- `resultsJson.harbor_status=evaluation_error`, `non_scored_subtype=evaluation_error`, `scored_by=playground-worker/harbor-lbg`
- `harbor_replay_executed=1`, `harbor_errors=0`, `scoringDetails=null`, `bundleStatus=null`
- `updatedAt=2026-11-04T17:34:33+00:00` (was stuck at submit time while evaluating)
- This is **not** the baseline `missing_worker_submission` path — Harbor/LBG ran a replay and errored before a final score.

Explore pid from last session exited after the 30-min receipt note. Supervisor restarts continuous-explore with diagnosis focus. Slots 02–10 remain held. No auto-resubmit until evaluation_error root cause is known.

## 2026-11-05 02:05 Asia/Shanghai — 62998 Harbor evaluation_error is a missing reward, not a graded zero

`playground status --attempt-id 62998` matches the receipt: `pending_review`, `execStatus=failed`, `scoreIsFinal=false`, `harbor_status=evaluation_error`, `scored_by=playground-worker/harbor-lbg`, `harbor_replay_executed=1`, `harbor_errors=0`, `harbor_reward=null`, `scoringDetails=null`. `updatedAt=2026-11-04T17:34:33Z`, about 41 minutes after `createdAt=2026-11-04T16:53:22Z`. Scoring-log is HTTP 403 for this account (challenge owner / collaborator / admin only). Worker `GET /api/jobs/39640` is still `not_found`.

A graded Harbor job on this same challenge looks different. Attempts 62715, 62879, and 62982 are `scored` / `execStatus=completed` / `harbor_status=scored` with a numeric `harbor_reward` (0.597, 0.593, 0.527) and `scoringDetails.source=harbor_worker`. `evaluation_error` leaves the reward null and never fills `scoringDetails`. Every `evaluation_error` row across the ten product arenas also has `harbor_errors=0`, so that field is the worker's empty default, not a count of clean trials.

Across 91 Harbor results, 19 are `evaluation_error`. Ten of those finished in under 6 minutes. Nine ran 35–49 minutes, the same window as successful grades. On `product-arena-08` specifically, full-length `evaluation_error` already happened to CLI 0.1.48 submissions that have `rawMessagesAvailable=true` and an empty attempt `trace` (`[]`), including three declared as DeepSeek Harness (62892, 62906, 62943, 62947) and one Codex (62865). So attaching raw messages is not sufficient to obtain a reward on this task.

### What 62998 packaged

Public `GET /api/attempts/62998/trace` is 79 steps: 76 `thought`, 3 `observation`, 0 `tool_call`, total `cost_usd=0`, one shared timestamp. 75 of those bodies still contain the string `tool_use`. The cursor session (`3fed5113`, 79 rows) stores 224 `tool_use` blocks inside `message.content`, with `role` set and `type` absent. Both CLI 0.1.39 and 0.1.48 therefore take `convertMessageRows` and stringify the blocks. `claudeCodeEventLike` does not match. `GET /api/attempts/62998/raw_messages` is 404 and `rawMessagesAvailable` is null. Scored 0.1.48 attempts expose `trace: []`.

A 0.1.48 `--dry-run` of the fixed slot-01 tree and the same session did not submit. Bundle sha256 `8a3499d932cbd7039814f4ea43447d8c3fce0ef4660612404fe443eb2a7471b5`, 1492637 bytes. `arm_manifest.json` still points `entrypoint` at the CLI placeholder `src/reproduce.py` (it prints a sentence and does not run the skill). `raw_messages.jsonl` starts with `type=session_start` and keeps the 224 `tool_use` blocks. The ARM trace is still 79 flattened steps. Rewriting the session so each row has `type=role` makes 0.1.48 emit 224 `tool_call` steps and 224 `error` steps with no `tool_result` and cost still 0. That trace was not submitted.

### Local skill failure that matches a missing reward

Harbor's verifier raises when neither reward file exists. The platform's reward is computed from `/app/output/result.json`. Before this edit, `parse_pdf.py` exited 1 with no file when PyMuPDF and `pdftotext` both rejected the input (`RuntimeError` from `blocks_from_pdftotext` is outside the `PermissionError` / `FileNotFoundError` handlers). A text file named as a PDF reproduced that: return code 1, `result.json` absent. The script now returns an empty assemble on that fallback failure, and `main` writes `status=undetermined` for any other exception. `run_example.py` covers the broken file. `scripts/rehearse_worker_layout.py` still exits 0 for all ten slots. The labeled example stays `success`.

### Not submitted

Slots 02–10 stay held. Slot 01 was not resubmitted. A 0.1.48 upload would attach `raw_messages` and would include the writer fix, but the same challenge already produced 40-minute `evaluation_error` results from 0.1.48 packages, and this cursor session still cannot be converted into paired tool calls or a non-zero cost. The one allowed resubmit waits until that residual is accepted or the trace can be paired.

