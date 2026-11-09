"""Visual theme modelled on the 'Navy' SaaS style: Switzer type, ink-navy text,
electric-blue accent, flat square tiles (navy / blue / lilac / mist), and a
navy-to-blue gradient hero. Light by default, with a matching navy dark mode.
"""

from __future__ import annotations

import gradio as gr

# Tokens (converted from the theme's oklch values)
BG, SURFACE, INK, MUTED, FAINT = "#FAFBFF", "#FFFFFF", "#111428", "#585D6F", "#878B9C"
BORDER, SOFT, MIST, LILAC, FROST = "#DEE1EC", "#F4F5FD", "#EAEEFC", "#DBDFFF", "#DEEDFB"
BLUE, NAVY, NAVY_2, NAVY_LINE, HERO_SOFT = "#3555E5", "#060B22", "#0D142C", "#222C4C", "#A4B3F8"

FONT = ["Switzer", "Helvetica Neue", "Arial", "sans-serif"]
MONO = ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"]

# Switzer is free for commercial use (Indian Type Foundry, via Fontshare).
HEAD = (
    '<link rel="preconnect" href="https://api.fontshare.com" crossorigin>'
    '<link href="https://api.fontshare.com/v2/css?f[]=switzer@300,400,500,600,700,400i,600i,700i&display=swap" rel="stylesheet">'
)


def build_theme() -> gr.themes.Base:
    return gr.themes.Base(
        font=[gr.themes.Font(f) for f in FONT], font_mono=[gr.themes.Font(f) for f in MONO], radius_size=gr.themes.sizes.radius_none,
        primary_hue=gr.themes.colors.indigo, neutral_hue=gr.themes.colors.slate,
    ).set(
        body_background_fill=BG, body_background_fill_dark=NAVY,
        body_text_color=INK, body_text_color_dark="#FFFFFF",
        body_text_color_subdued=MUTED, body_text_color_subdued_dark=HERO_SOFT,
        background_fill_primary=SURFACE, background_fill_primary_dark=NAVY_2,
        background_fill_secondary=SOFT, background_fill_secondary_dark=NAVY,
        border_color_primary=BORDER, border_color_primary_dark=NAVY_LINE,
        block_background_fill=SURFACE, block_background_fill_dark=NAVY_2,
        block_border_color=BORDER, block_border_color_dark=NAVY_LINE,
        block_border_width="1px", block_shadow="none", block_shadow_dark="none",
        block_label_background_fill=MIST, block_label_background_fill_dark=NAVY_LINE,
        block_label_text_color=INK, block_label_text_color_dark="#FFFFFF",
        block_title_text_color=INK, block_title_text_color_dark="#FFFFFF",
        block_title_text_weight="500", block_label_text_weight="500",
        input_background_fill=SURFACE, input_background_fill_dark=NAVY,
        input_border_color=BORDER, input_border_color_dark=NAVY_LINE,
        input_border_color_focus=BLUE, input_border_color_focus_dark=HERO_SOFT,
        input_shadow="none", input_shadow_focus="none",
        button_primary_background_fill=INK, button_primary_background_fill_dark="#FFFFFF",
        button_primary_background_fill_hover=NAVY_LINE, button_primary_background_fill_hover_dark=LILAC,
        button_primary_text_color="#FFFFFF", button_primary_text_color_dark=INK,
        button_primary_border_color=INK, button_primary_border_color_dark="#FFFFFF",
        button_secondary_background_fill=LILAC, button_secondary_background_fill_dark=NAVY_LINE,
        button_secondary_background_fill_hover=MIST, button_secondary_background_fill_hover_dark="#2E3A63",
        button_secondary_text_color=INK, button_secondary_text_color_dark="#FFFFFF",
        button_secondary_border_color=LILAC, button_secondary_border_color_dark=NAVY_LINE,
        button_large_text_weight="500", button_small_text_weight="500",
        button_primary_shadow="none", button_primary_shadow_hover="none", button_primary_shadow_active="none",
        button_secondary_shadow="none", button_secondary_shadow_hover="none", button_secondary_shadow_active="none",
        color_accent=BLUE, color_accent_soft=LILAC, color_accent_soft_dark=NAVY_LINE,
        checkbox_background_color_selected=BLUE, checkbox_border_color_selected=BLUE,
        slider_color=BLUE, link_text_color=INK, link_text_color_dark="#FFFFFF",
        link_text_color_hover=BLUE, link_text_color_visited=INK,
        table_border_color=BORDER, shadow_drop="none", shadow_drop_lg="none",
    )


CSS = f"""
:root{{--td-bg:{BG};--td-surface:{SURFACE};--td-ink:{INK};--td-muted:{MUTED};--td-faint:{FAINT};--td-border:{BORDER};
--td-soft:{SOFT};--td-mist:{MIST};--td-lilac:{LILAC};--td-frost:{FROST};--td-blue:{BLUE};--td-navy:{NAVY};--td-navy2:{NAVY_2};
--td-ok:#0F7A4A;--td-ok-bg:#E3F5EC;--td-bad:#C2263A;--td-bad-bg:#FCE7EA;--td-warn:#9A5B00;--td-warn-bg:#FDF0D8;}}
.dark{{--td-bg:{NAVY};--td-surface:{NAVY_2};--td-ink:#FFFFFF;--td-muted:{HERO_SOFT};--td-faint:#7F8BB8;--td-border:{NAVY_LINE};
--td-soft:{NAVY_2};--td-mist:#151D3B;--td-lilac:#1C2650;--td-frost:#13234A;
--td-ok:#5FD39A;--td-ok-bg:#0E2A22;--td-bad:#FF8A98;--td-bad-bg:#33121B;--td-warn:#F7C266;--td-warn-bg:#2E2210;}}
body,.gradio-container{{font-feature-settings:"ss01";-webkit-font-smoothing:antialiased}}
.gradio-container{{width:100%!important;max-width:min(1280px,100%)!important;margin:0 auto!important;overflow-x:hidden}}
.tabs [role=tablist]{{overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap}}
.prose h1,.prose h2,.prose h3{{font-weight:400!important;letter-spacing:-.02em}}
.prose em,.td-hero em,.td-h em{{font-style:italic;font-weight:700}}

/* hero */
.td-hero{{position:relative;margin:-8px -8px 8px;padding:64px 48px 32px;color:#fff;overflow:hidden;
 background:radial-gradient(120% 70% at 85% 105%,rgba(53,85,229,.95) 0%,rgba(53,85,229,.55) 35%,rgba(6,11,34,0) 70%),
 linear-gradient(180deg,{NAVY} 0%,#0A1340 45%,#2340C8 78%,{BLUE} 100%)}}
.td-hero,.td-hero h1,.td-hero em,.td-hero span,.td-hero .td-logo,.td-hero .l{{color:#fff!important}}
.td-hero p,.td-hero .d{{color:{HERO_SOFT}!important}}
.td-hero .td-stat .n span{{color:{LILAC}!important}}
.td-hero .td-nav{{display:flex;justify-content:space-between;align-items:center;font-size:.85rem;margin-bottom:56px}}
.td-hero .td-logo{{font-weight:700;letter-spacing:.04em}}
.td-hero .td-nav a{{color:#fff;text-decoration:none;margin-left:20px;opacity:.9}}
.td-hero a.td-cta{{background:#fff;color:{INK}!important;padding:6px 12px;border-radius:6px;font-weight:500;opacity:1!important}}
.td-hero h1{{font-size:clamp(2rem,4.6vw,3.25rem);font-weight:400;letter-spacing:-.025em;line-height:1.05;margin:0;max-width:760px;color:#fff}}
.td-hero p{{max-width:560px;margin:16px 0 0;color:{HERO_SOFT};font-size:1rem;line-height:1.5}}
.td-stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px;margin-top:40px}}
.td-stat .n{{font-size:clamp(2rem,4vw,3rem);font-weight:300;letter-spacing:-.03em;line-height:1}}
.td-stat .n span{{color:{LILAC}}}
.td-stat .l{{font-weight:500;margin-top:8px;font-size:.9rem}}
.td-stat .d{{color:{HERO_SOFT};font-size:.8rem;margin-top:2px}}
@media (max-width:720px){{.td-hero{{padding:40px 16px 24px}}.td-stats{{grid-template-columns:repeat(2,1fr)}}.td-hero .td-nav a:not(.td-cta){{display:none}}}}

/* tabs as a flat text nav */
.tabs button[role=tab]{{font-weight:500;font-size:.9rem;color:var(--td-muted);border:none!important;background:transparent!important}}
.tabs button[role=tab][aria-selected=true]{{color:var(--td-ink);box-shadow:inset 0 -2px 0 var(--td-blue)}}

/* labels and type */
.td-label{{font-size:.72rem;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--td-ink)}}
.td-label::before{{content:"/// ";color:var(--td-blue)}}
.td-h{{font-size:1.75rem;font-weight:400;letter-spacing:-.02em;line-height:1.15;margin:4px 0 6px;color:var(--td-ink)}}
.td-hint{{color:var(--td-muted);font-size:.88rem}}
.td-did{{font-family:var(--font-mono);font-size:.72rem;color:var(--td-muted);word-break:break-all}}
.td-name{{font-family:var(--font-mono);font-size:.72rem;color:var(--td-faint)}}

/* decision header */
.td-decision{{padding:20px 22px;border:1px solid var(--td-border);margin-bottom:0}}
.td-decision.td-ACCEPT{{background:var(--td-ok-bg)}}.td-decision.td-REFUSE{{background:var(--td-bad-bg)}}
.td-decision.td-ESCALATE{{background:var(--td-warn-bg)}}.td-decision.td-BLOCKED{{background:var(--td-mist)}}
.td-badge{{font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase}}
.td-ACCEPT .td-badge{{color:var(--td-ok)}}.td-REFUSE .td-badge{{color:var(--td-bad)}}.td-ESCALATE .td-badge{{color:var(--td-warn)}}.td-BLOCKED .td-badge{{color:var(--td-blue)}}
.td-reason{{font-size:1.35rem;font-weight:400;letter-spacing:-.015em;line-height:1.25;margin-top:6px;color:var(--td-ink)}}
.td-req{{margin-top:10px;color:var(--td-muted);font-size:.82rem}}

/* tile row (navy -> blue -> lilac -> mist) */
.td-tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:0 0 12px}}
.td-tile{{min-height:150px;padding:14px 16px;display:flex;flex-direction:column;justify-content:space-between}}
.td-tile .top{{display:flex;justify-content:space-between;font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;font-weight:500}}
.td-tile .t{{font-weight:500;font-size:.95rem}}.td-tile .s{{font-size:.78rem;margin-top:4px;line-height:1.35}}
.td-tile:nth-child(4n+1){{background:{NAVY};color:#fff}}.td-tile:nth-child(4n+1) .s{{color:{HERO_SOFT}}}
.td-tile:nth-child(4n+2){{background:{BLUE};color:#fff}}.td-tile:nth-child(4n+2) .s{{color:#D7DEFF}}
.td-tile:nth-child(4n+3){{background:var(--td-lilac);color:var(--td-ink)}}.td-tile:nth-child(4n+3) .s{{color:var(--td-muted)}}
.td-tile:nth-child(4n+4){{background:var(--td-mist);color:var(--td-ink)}}.td-tile:nth-child(4n+4) .s{{color:var(--td-muted)}}
.td-tile:nth-child(4n+1) .t,.td-tile:nth-child(4n+1) .top,.td-tile:nth-child(4n+2) .t,.td-tile:nth-child(4n+2) .top{{color:#fff!important}}
.td-tile:nth-child(4n+3) .t,.td-tile:nth-child(4n+3) .top,.td-tile:nth-child(4n+4) .t,.td-tile:nth-child(4n+4) .top{{color:var(--td-ink)!important}}
.td-tile:nth-child(4n+1) .top span,.td-tile:nth-child(4n+2) .top span{{color:#fff!important}}
.td-tile:nth-child(4n+3) .top span,.td-tile:nth-child(4n+4) .top span{{color:var(--td-ink)!important}}
.td-tile .top span.st.fail{{color:#fff!important}}
.td-tile.fail{{box-shadow:inset 0 0 0 3px var(--td-bad)}}
.td-tile .st.fail{{background:var(--td-bad);color:#fff;padding:1px 6px}}

/* check groups */
.td-group{{border:1px solid var(--td-border);border-top:none;padding:2px 14px;background:var(--td-surface)}}
.td-group:first-of-type{{border-top:1px solid var(--td-border)}}
.td-group summary{{cursor:pointer;font-weight:500;padding:10px 0;color:var(--td-ink)}}
.td-group ul{{list-style:none;padding-left:0;margin:0 0 10px}}
.td-group li{{padding:4px 0;font-size:.86rem;line-height:1.4;border-top:1px solid var(--td-soft);color:var(--td-ink)}}
.td-pass{{color:var(--td-ok);font-weight:500}}.td-fail{{color:var(--td-bad);font-weight:600}}
.td-pill{{display:inline-block;padding:1px 8px;font-size:.7rem;font-weight:500;margin:2px 4px 2px 0;background:var(--td-mist);color:var(--td-ink)}}
.td-pill.ok{{background:var(--td-ok-bg);color:var(--td-ok)}}.td-pill.bad{{background:var(--td-bad-bg);color:var(--td-bad)}}

/* cards, grids, tables */
.td-card{{border:1px solid var(--td-border);padding:16px 18px;background:var(--td-surface);color:var(--td-ink)}}
.td-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:0}}
.td-grid>.td-card{{margin:-1px 0 0 -1px}}
.td-grid>.td-card:nth-child(4n+1){{background:var(--td-mist)}}.td-grid>.td-card:nth-child(4n+2){{background:var(--td-lilac)}}
.td-table{{width:100%;border-collapse:collapse;font-size:.86rem;color:var(--td-ink)}}
.td-table th{{font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;font-weight:500;color:var(--td-muted)}}
.td-table td,.td-table th{{border-bottom:1px solid var(--td-border);padding:8px 10px;text-align:left;vertical-align:top}}
.td-steps{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:28px;margin:16px 0}}
.td-steps h3{{font-size:1rem;font-weight:500;margin:0 0 6px;color:var(--td-ink)}}
.td-steps p{{font-size:.86rem;color:var(--td-muted);margin:0;line-height:1.45}}
@media (max-width:720px){{.td-steps{{grid-template-columns:1fr 1fr}}}}
"""
