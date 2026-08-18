from pathlib import Path

_STYLES_DIR = Path(__file__).parent


def load_tab_css() -> str:
    """Load tab CSS and wrap in <style> tags for st.markdown."""
    css = (_STYLES_DIR / "tabs.css").read_text()
    return f"<style>\n{css}\n</style>"


def load_tooltip_css() -> str:
    """Load tooltip CSS and wrap in <style> tags for st.markdown."""
    css = (_STYLES_DIR / "tooltip.css").read_text()
    return f"<style>\n{css}\n</style>"
