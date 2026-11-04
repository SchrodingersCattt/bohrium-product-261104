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
- Slots 02–10 use the same queue failure. Several of those scripts only emit `result.json` after the model writes an intermediate file (`translation.json`, edit ledger, and so on). Slot 01 is the single-track candidate because `parse_pdf.py` writes the full result by itself.
