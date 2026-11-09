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
- Owner chose **free models only**. Benchmark (4 hard messages): flint-v1.0 4/4, lfm-3-1.7b 3/4 (its miss escalated safely), nemotron-3.5-super-vl 3/4, Gemma rate-limited. Fixes needed for free models: `max_tokens` 1500 + `reasoning: {effort: low, exclude: true}` (reasoning models used to burn the budget), and accepting numeric order numbers. Paid alternative tested: `anthropic/claude-haiku-5.5` (all correct, ~$0.0001/msg).
- Attack 10 (`manipulated_reader`) uses a simulated compromised model, so it needs no key.
- Tests never use the real key (`tests/conftest.py` strips it). 146 tests.

## Free provider chain (added 2026-11-09)
- `ProviderChain` in `reader.py`: Groq → Gemini → OpenRouter, one key each (`GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`); per-model and per-provider cooldowns shared across sessions; User-Agent header required (Groq's CDN returned 403/1010 without it).
- Benchmark: Groq gpt-oss-120b and qwen3.8-27b, and Gemini flash-lite read all 3 genuine hard messages and *obeyed* the injection (caught by grounding); Gemini 2.5 Flash got 4/4 (~2 s). Groq answers in 0.3–0.8 s.
- 159 tests, all with faked network.

## Conversation layer (added 2026-11-09)
- `conversation.py`: per-sender memory (customer text only, after verification), pending request + clarifying questions, small talk, language detection; `replies.Replier` writes AI replies checked by `consistent()`.
- Merchant order records carry EN/AR keywords so items ("vases", "الشمعة") identify orders.
- Attack 11 `forged_transcript`. Live-tested multi-turn flows in English and Arabic on the free Groq chain. 182 tests.

## Left for the owner
1. Review `docs/THESIS.md` in your own voice.
2. Record the 90 s video using `docs/loom-script.md` on the live URL.
3. Submit: repo URL, live demo URL, video link, notes (paste from `docs/NOTES.md`).
Then write `output/check.md` → `pass`.
