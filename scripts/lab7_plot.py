"""Create reproducible PNG charts from the Lab 7 JSON results (requires Pillow)."""

import json
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RESULTS = Path(__file__).resolve().parents[1] / "docs" / "lab7" / "results"
SCALE = 2
WHITE = "#ffffff"
INK = "#172334"
MUTED = "#66758a"
GRID = "#dce3eb"
BLUE = "#2563eb"
TEAL = "#0d9488"
ORANGE = "#e97931"


def font(size: int, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size * SCALE)


def canvas(title: str):
    image = Image.new("RGB", (1500 * SCALE, 900 * SCALE), WHITE)
    draw = ImageDraw.Draw(image)
    draw.text((75 * SCALE, 40 * SCALE), title, font=font(27, True), fill=INK)
    return image, draw


def text(draw, x, y, value, size=18, color=INK, bold=False):
    draw.text((x * SCALE, y * SCALE), str(value), font=font(size, bold), fill=color)


def line(draw, coordinates, fill=GRID, width=1):
    draw.line(tuple(int(value * SCALE) for value in coordinates), fill=fill, width=width * SCALE)


def bar(draw, coordinates, fill):
    draw.rounded_rectangle(tuple(int(value * SCALE) for value in coordinates), radius=6 * SCALE, fill=fill)


def save(image, filename):
    image.resize((1500, 900), Image.Resampling.LANCZOS).save(RESULTS / filename)
    print(RESULTS / filename)


def hot_shard_chart():
    naive = json.loads((RESULTS / "seed-lab7-naive-hot.json").read_text(encoding="utf-8"))
    bucket = json.loads((RESULTS / "seed-lab7-bucket.json").read_text(encoding="utf-8"))
    image, draw = canvas("Hot shard: tenant modulo versus virtual buckets")
    text(draw, 75, 85, "500 writes per strategy; 90% from tenant 2; concurrency 16", 17, MUTED)

    text(draw, 75, 155, "Distribution of writes (%)", 21, INK, True)
    left, right, top, bottom = 100, 705, 205, 650
    for value in (0, 25, 50, 75, 100):
        y = bottom - value * (bottom - top) / 100
        line(draw, (left, y, right, y))
        text(draw, 60, y - 10, value, 14, MUTED)
    for x, result, label in ((220, naive, "Naive modulo"), (500, bucket, "Virtual buckets")):
        shards = result["distribution"]["shards"]
        for offset, entry, color in ((0, shards[0], BLUE), (78, shards[1], TEAL)):
            height = entry["write_percent"] * (bottom - top) / 100
            bar(draw, (x + offset, bottom - height, x + offset + 65, bottom), color)
            text(draw, x + offset + 5, bottom - height - 30, f'{entry["write_percent"]}%', 15, color, True)
        text(draw, x - 5, 670, label, 16, INK, True)
    bar(draw, (110, 740, 135, 762), BLUE)
    text(draw, 145, 738, "Shard A", 16)
    bar(draw, (280, 740, 305, 762), TEAL)
    text(draw, 315, 738, "Shard B", 16)

    text(draw, 820, 155, "Write latency p95 (ms)", 21, INK, True)
    max_value = 1000
    for value in (0, 250, 500, 750, 1000):
        y = bottom - value * (bottom - top) / max_value
        line(draw, (820, y, 1420, y))
        text(draw, 770, y - 10, value, 14, MUTED)
    for x, result, color, label in ((930, naive, ORANGE, "Naive"), (1190, bucket, TEAL, "Buckets")):
        latency = result["write_metrics"]["p95_ms"]
        height = latency * (bottom - top) / max_value
        bar(draw, (x, bottom - height, x + 125, bottom), color)
        text(draw, x, bottom - height - 35, f"{latency:.1f} ms", 17, color, True)
        text(draw, x + 20, 670, label, 16, INK, True)
    text(draw, 75, 820, "Source: docs/lab7/results/seed-lab7-*.json", 14, MUTED)
    save(image, "hot-shard-comparison.png")


def throughput_chart():
    single = json.loads((RESULTS / "benchmark-lab7-single.json").read_text(encoding="utf-8"))
    bucket = json.loads((RESULTS / "benchmark-lab7-bucket.json").read_text(encoding="utf-8"))
    image, draw = canvas("TrackHub read benchmark: throughput and p95 latency")
    text(draw, 75, 85, "200 requests per point; one local result versus fan-out to two shards", 17, MUTED)
    rows = single["rows"] + bucket["rows"]
    series = [
        ("Single node", BLUE, [row for row in rows if row["topology"] == "single"]),
        ("Sharded local", TEAL, [row for row in rows if row["topology"] == "bucket" and row["operation"] == "shard_local"]),
        ("Cross-shard", ORANGE, [row for row in rows if row["topology"] == "bucket" and row["operation"] == "cross_shard"]),
    ]
    concurrencies = [1, 4, 8, 16, 32]
    for x0, title, metric, upper, unit in ((90, "Throughput", "rps", 500, "RPS"),
                                            (800, "p95 latency", "p95_ms", 300, "ms")):
        top, bottom, width = 195, 690, 580
        text(draw, x0, 150, title, 21, INK, True)
        for value in range(0, upper + 1, 100 if upper == 500 else 50):
            y = bottom - value * (bottom - top) / upper
            line(draw, (x0, y, x0 + width, y))
            text(draw, x0 - 45, y - 9, value, 13, MUTED)
        for index, concurrency in enumerate(concurrencies):
            x = x0 + index * width / 4
            text(draw, x - 8, 705, concurrency, 15, MUTED)
        text(draw, x0 + width - 5, 735, "Concurrency", 14, MUTED)
        text(draw, x0 - 45, 175, unit, 14, MUTED)
        for label, color, points in series:
            coords = []
            for point in points:
                x = x0 + concurrencies.index(point["concurrency"]) * width / 4
                y = bottom - min(point[metric], upper) * (bottom - top) / upper
                coords.append((x, y))
            for a, b in pairwise(coords):
                line(draw, (*a, *b), color, 3)
            for x, y in coords:
                draw.ellipse(((x - 5) * SCALE, (y - 5) * SCALE, (x + 5) * SCALE, (y + 5) * SCALE), fill=color)
    for index, (label, color, _) in enumerate(series):
        x = 230 + index * 330
        line(draw, (x, 810, x + 45, 810), color, 4)
        text(draw, x + 55, 798, label, 17, INK)
    save(image, "benchmark-comparison.png")


if __name__ == "__main__":
    hot_shard_chart()
    throughput_chart()
