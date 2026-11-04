"""Render the Lab 7 architecture as a standalone PNG for the report."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "lab7" / "results" / "architecture.png"
FONT = Path("C:/Windows/Fonts/arial.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")

image = Image.new("RGB", (1800, 650), "#ffffff")
draw = ImageDraw.Draw(image)
title_font = ImageFont.truetype(str(FONT_BOLD), 40)
box_font = ImageFont.truetype(str(FONT_BOLD), 24)
small_font = ImageFont.truetype(str(FONT), 20)


def centered(text, x, y, font, fill="#172a40"):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((x - (box[2] - box[0]) / 2, y - (box[3] - box[1]) / 2), text, font=font, fill=fill)


def node(bounds, lines, fill, outline="#51708d"):
    draw.rounded_rectangle(bounds, radius=20, fill=fill, outline=outline, width=3)
    mid_x = (bounds[0] + bounds[2]) / 2
    mid_y = (bounds[1] + bounds[3]) / 2
    if len(lines) == 1:
        centered(lines[0], mid_x, mid_y, box_font)
    else:
        centered(lines[0], mid_x, mid_y - 16, box_font)
        centered(lines[1], mid_x, mid_y + 18, small_font)


def arrow(points, color="#5a718b"):
    draw.line(points, fill=color, width=5, joint="curve")
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    if x2 > x1:
        tip = [(x2, y2), (x2 - 15, y2 - 9), (x2 - 15, y2 + 9)]
    elif y2 > y1:
        tip = [(x2, y2), (x2 - 9, y2 - 15), (x2 + 9, y2 - 15)]
    else:
        tip = [(x2, y2), (x2 - 9, y2 + 15), (x2 + 9, y2 + 15)]
    draw.polygon(tip, fill=color)


draw.text((60, 35), "Архітектура TrackHub ЛР 7", font=title_font, fill="#15263b")
draw.text((60, 91), "CRUD на Primary  •  асинхронна реплікація PostgreSQL", font=small_font, fill="#59718a")

node((45, 270, 220, 360), ["Клієнт"], "#eef2f6")
node((310, 270, 500, 360), ["Lab7 API"], "#e5efff")
node((590, 270, 800, 360), ["Shard Router"], "#d8e9ff")
node((890, 270, 1100, 360), ["128 кошиків"], "#d8e9ff")
node((1190, 145, 1430, 235), ["Shard A", "Primary"], "#d8e9ff")
node((1190, 425, 1430, 515), ["Shard B", "Primary"], "#d8e9ff")
node((1525, 145, 1765, 235), ["Shard A", "Replica"], "#dcf3e7", "#479c74")
node((1525, 425, 1765, 515), ["Shard B", "Replica"], "#dcf3e7", "#479c74")
node((300, 495, 510, 585), ["Single DB", "контроль"], "#eef2f6")

arrow([(220, 315), (310, 315)])
arrow([(500, 315), (590, 315)])
arrow([(800, 315), (890, 315)])
arrow([(1100, 315), (1140, 315), (1140, 190), (1190, 190)])
arrow([(1100, 315), (1140, 315), (1140, 470), (1190, 470)])
arrow([(1430, 190), (1525, 190)], "#479c74")
arrow([(1430, 470), (1525, 470)], "#479c74")
arrow([(405, 360), (405, 495)])

centered("WAL", 1478, 164, small_font, "#357e5b")
centered("WAL", 1478, 444, small_font, "#357e5b")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUTPUT)
print(OUTPUT)
