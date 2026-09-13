"""
vdak-host/ui/__main__.py
Allows running the Gradio UI as: python -m ui
"""
from ui.gradio_app import demo
import os

demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.getenv("GRADIO_PORT", "7860")),
    share=False,
    show_error=True,
)
