"""Gradio entry point (Hugging Face Spaces runs this file). Placeholder until stage 04_ui."""

import sys
from pathlib import Path

# Hugging Face Spaces installs requirements.txt, not this package, so put src/ on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import gradio as gr  # noqa: E402

import trustdesk  # noqa: E402


def build() -> gr.Blocks:
    with gr.Blocks(title="TrustDesk") as demo:
        gr.Markdown(
            f"# TrustDesk v{trustdesk.__version__}\n"
            "A trust layer for AI agents. The demo is under construction."
        )
    return demo


if __name__ == "__main__":
    build().launch()
