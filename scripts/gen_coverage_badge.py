"""Gera coverage.svg a partir do .coverage local (rodar depois de `pytest`).

Nao usa o pacote coverage-badge -- ele importa pkg_resources internamente
(coverage_badge/__main__.py), removido do setuptools moderno. Quebrou de
verdade na CI (Python 3.14, setuptools 83.0.0): ModuleNotFoundError.
So depende de `coverage` (ja instalado via pytest-cov) + stdlib.
"""
import io

import coverage

THRESHOLDS = [(90, "#4c1"), (75, "#97CA00"), (50, "#dfb317")]
FALLBACK_COLOR = "#e05d44"


def _color_for(percent: float) -> str:
    for threshold, color in THRESHOLDS:
        if percent >= threshold:
            return color
    return FALLBACK_COLOR


def _text_width(text: str) -> int:
    return len(text) * 7 + 10


def build_svg(percent: float) -> str:
    label, value = "coverage", f"{percent:.0f}%"
    color = _color_for(percent)
    label_w, value_w = _text_width(label), _text_width(value)
    total_w = label_w + value_w

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="{total_w}" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
    <rect width="{total_w}" height="20" fill="url(#b)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_w / 2:.0f}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_w / 2:.0f}" y="14">{label}</text>
    <text x="{label_w + value_w / 2:.0f}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{label_w + value_w / 2:.0f}" y="14">{value}</text>
  </g>
</svg>
'''


def main():
    cov = coverage.Coverage()
    cov.load()
    percent = cov.report(file=io.StringIO())

    with open("coverage.svg", "w", encoding="utf-8") as f:
        f.write(build_svg(percent))
    print(f"Badge gerado: {percent:.0f}% -> coverage.svg")


if __name__ == "__main__":
    main()
