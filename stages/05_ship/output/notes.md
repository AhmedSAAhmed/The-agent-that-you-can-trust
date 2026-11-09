# 05_ship - notes

## Done (2026-11-09)
- Live demo: https://huggingface.co/spaces/SalQ/TrustDesk (direct: https://salq-trustdesk.hf.space). Verified live: greeting + mutual check, AED 380 → ESCALATE, Attack Lab 9/9 defended.
- Docs: `docs/architecture.md`, `docs/THESIS.md` (292 words), `docs/NOTES.md`, `docs/loom-script.md`, final `README.md`.
- Clean clone: `git clone` → `uv sync` → 117 tests pass; CLI demo and app run.

## Deploy lessons
- `requirements.txt` must list direct dependencies only (full pins clashed with gradio[mcp]'s pydantic<=2.12.5).
- The Space runs on ZeroGPU hardware (CPU basic can't be selected without PRO); `app.py` defines an unused `@spaces.GPU` marker so it boots. Nothing ever uses a GPU.
- Push: `git push space main` (the owner's token is stored in Windows Git Credential Manager).

## Left for the owner
1. Review `docs/THESIS.md` in your own voice.
2. Record the 90 s video using `docs/loom-script.md` on the live URL.
3. Submit: repo URL, live demo URL, video link, notes (paste from `docs/NOTES.md`).
Then write `output/check.md` → `pass`.
