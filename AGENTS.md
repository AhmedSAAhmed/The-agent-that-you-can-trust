# TrustDesk

A trust layer for AI agents (DIDs, Verifiable Credentials, revocation, scoped delegation, policy). It ships a working Gradio demo where a DOO-style support agent accepts, refuses or escalates refund requests from other agents.

## Where things live

| Folder | What it holds |
|---|---|
| `stages/` | the build pipeline, in execution order (one `CONTEXT.md` each) |
| `src/trustdesk/` | product: the Python package |
| `tests/` | product: pytest suites, which are the stage checks |
| `policies/` | factory: YAML trust policies |
| `docs/` | product: architecture, thesis, notes |
| `_tools/` | scripts; `links.py` checks every link and input path |
| [PLAN.md](PLAN.md) | factory: scope, scenario, scoring map, schedule |

## Route by what just happened

| If | Go to | Then stop at |
|---|---|---|
| starting the build | [01_crypto_core](stages/01_crypto_core/CONTEXT.md) | its check |
| a stage's check passed | next numbered stage | that stage's check |
| asked for status | `stages/*/output/check.md` | report what exists |
| changing scope | [PLAN.md](PLAN.md) | owner approval |

## The one rule

Nothing moves to the next stage until the last one's `check.md` says `pass`.

## Deliberate break of an ICM invariant

Code products live in `src/` and `tests/`, not in each stage's `output/`. Python imports need one package tree. Each stage's `output/` holds only its `check.md` verdict and a short `notes.md`.
