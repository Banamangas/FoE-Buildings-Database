from pathlib import Path
from PIL import Image

FORGE_HAMMER = Path.home() / "Github" / "forge-hammer"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "icons"
OUTPUT.mkdir(parents=True, exist_ok=True)

SPRITE = FORGE_HAMMER / "js" / "web" / "productions" / "images" / "productions.png"
sprite = Image.open(SPRITE).convert("RGBA")

ICONS = [
    ("att_def_boost_attacker.png", 340, 1, 22, 24),
    ("att_def_boost_defender.png", 362, 1, 22, 24),
]

for filename, left, top, width, height in ICONS:
    box = (left, top, left + width, top + height)
    icon = sprite.crop(box)
    icon.save(OUTPUT / filename)
    print(f"Saved {filename}")

BADGES = [
    ("gbg_badge.png", FORGE_HAMMER / "js" / "web" / "x_img" / "gbg-green.png"),
    ("ge_badge.png", FORGE_HAMMER / "js" / "web" / "x_img" / "ge.png"),
    ("qi_badge.png", FORGE_HAMMER / "js" / "web" / "x_img" / "guild_raids.png"),
]

for filename, src in BADGES:
    img = Image.open(src).convert("RGBA")
    img.thumbnail((16, 16))
    img.save(OUTPUT / filename)
    print(f"Saved {filename}")
