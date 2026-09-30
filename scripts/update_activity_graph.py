#!/usr/bin/env python3
"""Render a self-hosted GitHub contribution activity graph as an SVG."""

from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = "amansingh2116"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "assets" / "github-activity-graph.svg"


class ContributionCalendarParser(HTMLParser):
    """Extract GitHub's public contribution levels from its calendar markup."""

    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        if tag != "td":
            return

        attributes = dict(attrs)
        day = attributes.get("data-date")
        level = attributes.get("data-level")
        if not day or level is None:
            return

        try:
            self.days[date.fromisoformat(day)] = int(level)
        except ValueError:
            pass


def fetch_contribution_levels():
    request = Request(
        f"https://github.com/users/{USERNAME}/contributions",
        headers={"User-Agent": "github-profile-activity-graph"},
    )
    with urlopen(request, timeout=30) as response:
        markup = response.read().decode("utf-8")

    parser = ContributionCalendarParser()
    parser.feed(markup)
    if not parser.days:
        raise RuntimeError("GitHub contribution calendar did not contain any activity data.")
    return parser.days


def weekly_levels(levels):
    today = date.today()
    start = today - timedelta(days=363)
    start -= timedelta(days=(start.weekday() + 1) % 7)
    weeks = []

    for offset in range(0, 364, 7):
        week_start = start + timedelta(days=offset)
        weeks.append((week_start, sum(levels.get(week_start + timedelta(days=day), 0) for day in range(7))))

    return weeks


def chart_svg(weeks):
    width, height = 1000, 250
    left, right, top, bottom = 58, 28, 42, 48
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [value for _, value in weeks]
    maximum = max(values) or 1

    points = []
    for index, value in enumerate(values):
        x = left + (plot_width * index / (len(values) - 1))
        y = top + plot_height - (value / maximum * plot_height)
        points.append((x, y))

    line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    plot_bottom = height - bottom
    area_path = "M {0:.1f},{1} L {2} L {3:.1f},{1} Z".format(
        points[0][0], plot_bottom, line_points.replace(" ", " L "), points[-1][0]
    )

    grid_lines = "".join(
        f'<line x1="{left}" y1="{top + plot_height * step / 4:.1f}" '
        f'x2="{width - right}" y2="{top + plot_height * step / 4:.1f}" class="grid" />'
        for step in range(5)
    )

    labels = []
    seen_months = set()
    for index, (week_start, _) in enumerate(weeks):
        month = week_start.strftime("%b")
        if month not in seen_months and week_start.day <= 7:
            seen_months.add(month)
            x = left + (plot_width * index / (len(weeks) - 1))
            labels.append(f'<text x="{x:.1f}" y="{height - 20}" class="label">{month}</text>')

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{USERNAME} GitHub contribution activity graph">
  <style>
    .title {{ fill: #f0f6fc; font: 600 18px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    .subtitle, .label {{ fill: #8b949e; font: 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    .grid {{ stroke: #30363d; stroke-width: 1; }}
  </style>
  <rect width="1000" height="250" fill="#0d1117" rx="6" />
  <text x="58" y="26" class="title">GitHub contribution activity</text>
  <text x="972" y="26" text-anchor="end" class="subtitle">Updated {updated}</text>
  {grid_lines}
  <path d="{area_path}" fill="#1f6feb" fill-opacity="0.24" />
  <polyline points="{line_points}" fill="none" stroke="#58a6ff" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" />
  <circle cx="{points[-1][0]:.1f}" cy="{points[-1][1]:.1f}" r="4" fill="#3fb950" />
  <text x="58" y="220" class="subtitle">Weekly contribution intensity, last 52 weeks</text>
  {''.join(labels)}
</svg>'''


def main():
    levels = fetch_contribution_levels()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(chart_svg(weekly_levels(levels)), encoding="utf-8")
    print(f"Updated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
