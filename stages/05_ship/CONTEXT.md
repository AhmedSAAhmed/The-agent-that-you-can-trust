# 05_ship - deploy, docs, thesis, video

One job: Produce every item on the submission checklist.

## Inputs
- Working (this run): `stages/04_ui/output/check.md`
- Reference (every run): `PLAN.md` (sections 0 and 7)

Do NOT load: other stages' notes, or later stages' code.

## Process
1. If an input is missing, or the previous `check.md` is not `pass`, stop and say which.
2. `README.md` (HF Spaces frontmatter, clean-clone steps)
3. `docs/architecture.md`: identity -> claims -> verification -> policy
4. `docs/THESIS.md` (300 words max), `docs/NOTES.md` (AI tools used, decisions, out of scope)
5. `docs/loom-script.md` (90 s)
6. Owner: push to GitHub + HF Space, record video, submit

## Outputs
- Code under `src/trustdesk/` and `tests/` (see AGENTS.md, deliberate break)
- `output/notes.md`: decisions made, anything cut

## Check
Owner opens the live URL in an incognito window, a fresh `git clone` passes `uv run pytest -q`, and every checklist item exists. Write `output/check.md`.
