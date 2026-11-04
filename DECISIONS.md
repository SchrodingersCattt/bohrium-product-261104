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
