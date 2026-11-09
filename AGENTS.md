# TrustDesk

A trust layer for AI agents (DIDs, Verifiable Credentials, revocation, scoped delegation, policy). It ships a working Gradio demo where a DOO-style support agent accepts, refuses or escalates refund requests from other agents. Submission deadline: Nov 15, 2026.

## Where things live

| Folder | What it holds |
|---|---|
| `stages/` | the build pipeline, in order; [stages/CONTEXT.md](stages/CONTEXT.md) holds the **current status line** |
| `src/trustdesk/` | product: the Python package |
| `tests/` | product: pytest suites, which are the stage checks |
| `policies/` | factory: YAML trust policies |
| `docs/` | product: architecture, thesis, notes |
| `_tools/` | scripts; `links.py` checks every link and input path |
| [PLAN.md](PLAN.md) | factory: locked decisions (section 0), scenario, schedule |

## Route by what just happened

| If | Go to | Then stop at |
|---|---|---|
| resuming work (any agent, any session) | [stages/CONTEXT.md](stages/CONTEXT.md) status line, then that stage's `CONTEXT.md` | that stage's check |
| a stage's check passed | next numbered stage | that stage's check |
| asked for status | `stages/*/output/check.md` | report what exists |
| changing scope or a locked decision | [PLAN.md](PLAN.md) section 0 | owner approval |

## Rules for every agent

- Setup: `uv sync`. Tests: `uv run pytest -q`. App: `uv run python app.py`. Links: `python -I _tools/links.py .`
- $0 budget: no paid API may be required to run, test or demo. LLM code stays optional, behind env vars.
- Trust decisions are deterministic code. Never let LLM output decide ACCEPT / REFUSE / ESCALATE.
- Use real crypto (`cryptography` Ed25519). Never hand-roll primitives.
- Write tests first for every verification rule and attack.
- When a stage finishes, write its `output/check.md` and `output/notes.md`, then update the status line in `stages/CONTEXT.md`.
- `requirements.txt` (used by Hugging Face Spaces) lists direct dependencies only, with no exact pins and no Gradio. Never regenerate it with `uv export`: full pins clash with the Space's own Gradio install.
- Deploy: `git push origin main` (GitHub) and `git push space main` (huggingface.co/spaces/SalQ/trustdesk).
- Commits are authored by the owner only: never add `Co-Authored-By` or other AI attribution trailers.
- Commit and push only when the owner asks. Remote: `origin` = github.com/AhmedSAAhmed/The-agent-that-you-can-trust, branch `main`.

## The one rule

Nothing moves to the next stage until the last one's `check.md` says `pass`.

## Deliberate break of an ICM invariant

Code products live in `src/` and `tests/`, not in each stage's `output/`. Python imports need one package tree. Each stage's `output/` holds only its `check.md` verdict and a short `notes.md`.
