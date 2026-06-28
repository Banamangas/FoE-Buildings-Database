"""Ko-fi support widget embedded via Streamlit HTML component."""

import streamlit.components.v1 as components
from typing import Literal

_KOFI_HTML_LEFT = """
<div style="display: flex; justify-content: flex-start; align-items: center; min-height: 48px;">
<script type="text/javascript" src="https://storage.ko-fi.com/cdn/widget/Widget_2.js"></script>
<script type="text/javascript">
kofiwidget2.init('Support me on Ko-fi', '#000000', 'Z4N5227ICQ');
kofiwidget2.draw();
</script>
</div>
"""

_KOFI_HTML_CENTER = """
<div style="display: flex; justify-content: center; align-items: center; min-height: 48px;">
<script type="text/javascript" src="https://storage.ko-fi.com/cdn/widget/Widget_2.js"></script>
<script type="text/javascript">
kofiwidget2.init('Support me on Ko-fi', '#000000', 'Z4N5227ICQ');
kofiwidget2.draw();
</script>
</div>
"""

_KOFI_HTML_RIGHT = """
<div style="display: flex; justify-content: flex-end; align-items: center; min-height: 48px;">
<script type="text/javascript" src="https://storage.ko-fi.com/cdn/widget/Widget_2.js"></script>
<script type="text/javascript">
kofiwidget2.init('Support me on Ko-fi', '#000000', 'Z4N5227ICQ');
kofiwidget2.draw();
</script>
</div>
"""

def render_kofi_widget(column_position: Literal["left", "right", "center"] = "center", height: int = 56) -> None:
    """Render the Ko-fi support widget in the designated column."""
    if column_position == "left":
        components.html(_KOFI_HTML_LEFT, height=height)
    elif column_position == "right":
        components.html(_KOFI_HTML_RIGHT, height=height)
    elif column_position == "center":
        components.html(_KOFI_HTML_CENTER, height=height)