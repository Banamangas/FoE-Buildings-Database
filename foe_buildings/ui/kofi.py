"""Ko-fi support widget embedded via Streamlit HTML component."""

import streamlit.components.v1 as components
from typing import Literal

def _get_kofi_html(column_position: Literal["left", "right", "center"], color: str = "#e8c900", language: str = "en") -> str:
    if language == "en":
        support_text = "Support me on Ko-fi"
    elif language == "fr":
        support_text = "Me faire un don sur Ko-fi"
    else:
        support_text = "Support me on Ko-fi"

    if column_position == "left":
        return f"""
<div style="display: flex; justify-content: flex-start; align-items: center; min-height: 48px;">
<script type='text/javascript' src='https://storage.ko-fi.com/cdn/widget/Widget_2.js'></script><script type='text/javascript'>kofiwidget2.init('{support_text}', '{color}', 'Z4N5227ICQ');kofiwidget2.draw();</script> 
</div>
"""
    elif column_position == "right":
        return f"""
<div style="display: flex; justify-content: flex-end; align-items: center; min-height: 48px;">
<script type='text/javascript' src='https://storage.ko-fi.com/cdn/widget/Widget_2.js'></script><script type='text/javascript'>kofiwidget2.init('{support_text}', '{color}', 'Z4N5227ICQ');kofiwidget2.draw();</script> 
</div>
"""
    elif column_position == "center":
        return f"""
<div style="display: flex; justify-content: center; align-items: center; min-height: 48px;">
<script type='text/javascript' src='https://storage.ko-fi.com/cdn/widget/Widget_2.js'></script><script type='text/javascript'>kofiwidget2.init('{support_text}', '{color}', 'Z4N5227ICQ');kofiwidget2.draw();</script> 
</div>
"""

def render_kofi_widget(column_position: Literal["left", "right", "center"] = "center", height: int = 56, language: str = "en") -> None:
    """Render the Ko-fi support widget in the designated column."""
    if column_position == "left":
        components.html(_get_kofi_html("left", language=language), height=height)
    elif column_position == "right":
        components.html(_get_kofi_html("right", language=language), height=height)
    elif column_position == "center":
        components.html(_get_kofi_html("center", language=language), height=height)