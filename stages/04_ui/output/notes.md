# 04_ui - notes

## Built
- `app.py`: Gradio 6 Blocks with 7 tabs: Live desk (chat + editable "Understood as" fields + decision panel + raw signed JSON), Escalations (approve/decline as Noura, signed), Trust profiles, Grant · scope · revoke, Attack Lab (single + run all), Verify a credential (paste JSON; tampered example), How it works.
- `src/trustdesk/views.py`: escaped HTML renderers + CSS (uses Gradio theme variables, so light and dark both work). The trace is grouped ⓪ reading → ① identity → ② credentials → ③ authority → ④ evidence → ⑤ policy, matching identity → claims → verification → policy.
- `.claude/launch.json`: preview config (`uv run python app.py`, port 7860).

## Decisions
- One `World` per browser session, created in `demo.load`, so concurrent visitors are isolated.
- Gradio 6: `theme`/`css` go to `launch()`, not `Blocks()`.
- Parser output fills editable Order/Amount fields; the user's corrections win over the parser.

## Visual theme (2026-11-09)
- `src/trustdesk/theme.py` restyles the app after the 'Navy' SaaS theme (navy-astro.pages.dev, scraped with Firecrawl): Switzer font (Fontshare, free for commercial use), ink #111428, muted #585D6F, blue #3555E5, lilac #DBDFFF, mist #EAEEFC, square corners, a navy-to-blue gradient hero with stat numerals, `///` section labels, and the decision path drawn as a navy → blue → lilac → mist tile row. A matching navy dark mode is included.
- Checked in the browser: light, dark, and phone width (375 px, no horizontal scroll; tabs collapse into a menu).

## Bug fixed during the visual check
- The empty Amount field (0) could override the parsed amount on a fast Enter ("AED 380" became a refund of 0). Edit fields now override only after the user types in them (`touched` state), and the policy refuses refunds without a positive amount and an order (`policy.request_complete`). Regression tests added.

## Known gaps
- HF Spaces deploy not done yet (stage 05).
