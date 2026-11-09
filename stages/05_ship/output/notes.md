# 05_ship - notes

## Done (2026-11-09)
- Live demo: https://huggingface.co/spaces/SalQ/TrustDesk (direct: https://salq-trustdesk.hf.space). Verified live: greeting + mutual check, AED 380 → ESCALATE, Attack Lab 9/9 defended.
- Docs: `docs/architecture.md`, `docs/THESIS.md` (292 words), `docs/NOTES.md`, `docs/loom-script.md`, final `README.md`.
- Clean clone: `git clone` → `uv sync` → 117 tests pass; CLI demo and app run.

## Deploy lessons
- `requirements.txt` must list direct dependencies only (full pins clashed with gradio[mcp]'s pydantic<=2.12.5).
- The Space runs on ZeroGPU hardware (CPU basic can't be selected without PRO); `app.py` defines an unused `@spaces.GPU` marker so it boots. Nothing ever uses a GPU.
- Push: `git push space main` (the owner's token is stored in Windows Git Credential Manager).

## Optional AI reader (added 2026-11-09)
- `src/trustdesk/reader.py`: OpenRouter → pydantic `ExtractedRequest` → grounding → policy (`reader_must_be_grounded` escalates). Falls back to `parser.py` with no key, on errors, empty/invalid output, or after 25 AI reads per session.
- Live-tested: the free `google/gemma-4-31b-it:free` was rate-limited upstream (HTTP 429); `anthropic/claude-haiku-5.5` read all test messages correctly at ~$0.0001 each.
- Attack 10 (`manipulated_reader`) uses a simulated compromised model, so it needs no key.
- Tests never use the real key (`tests/conftest.py` strips it). 146 tests.

## Left for the owner
1. Review `docs/THESIS.md` in your own voice.
2. Record the 90 s video using `docs/loom-script.md` on the live URL.
3. Submit: repo URL, live demo URL, video link, notes (paste from `docs/NOTES.md`).
Then write `output/check.md` → `pass`.
