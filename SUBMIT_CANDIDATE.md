# SUBMIT_CANDIDATE

Status: blocked on the Playground CLI. Not submitted. `scripts/submit_recipe.py` exits 2: package and worker health are fine, `playground` is not on PATH. Do not post another ARM zip.

| Field | Value |
|---|---|
| Slot | 01 |
| Package | `submissions/01` (identical to `skills/01-pdf-reading-order`) |
| Challenge | `product-arena-08-3027d350` |
| Replaces | attempt 62956 |
| Root cause | `playground-worker/nonstandard-submission-guard` / `missing_worker_submission`. The hand-built ARM zip was stored by the platform (`bundleStatus=ready`) and never entered the Worker queue at `http://47.92.88.121:443/api`. |
| Fix | Resubmit with the current Playground CLI. `--outputs submissions/01` so the worker receives the skill root (`SKILL.md`, `scripts/`, `resources/`). Do not upload `src/package_skill.py` or `results/skill_inventory.json` as the scored artifact. |
| Local proof | `python3 scripts/rehearse_worker_layout.py` installs the skill as `skills/weekly-skill`, runs `parse_pdf.py` on the labeled example, and checks `app/output/result.json`. Expected: `status=success`, blocks present, validator `ok`, `submitted=false`. `skills/01-pdf-reading-order/scripts/run_example.py` also passes. All ten `run_example.py` scripts passed on 2026-11-04. |
| Residual risk | `https://play.bohrium.com/install.sh` returns HTTP 405 (any path containing `.sh`). `@paper2arm/playground-cli` is not on the public npm registry. `git.dp.tech` does not connect from this host. The only public GitHub tree, `Osgood001/playground-cli` 0.1.7, targets a different API and was not used. Worker `http://47.92.88.121:443/health` is ok. `--dry-run` was not executed. Hidden cases are unseen. Slots 02–10 stay unsubmitted until slot 01 is past the worker-queue guard. |

Do not mass `playground submit`.
