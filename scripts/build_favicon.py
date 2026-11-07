"""Build the favicon set from the real ồ in the project's own Inter.

The mark is the glyph that makes the name: bồi carries both a circumflex and
a grave, the two marks that make Vietnamese look like itself and English
not. It is drawn as paths from app/fonts/inter-vi.woff2 at weight 800 and
the large optical size, so it needs no font where it is shown.

    uv run --with fonttools --with brotli --with playwright \\
        scripts/build_favicon.py

Writes app/favicon.svg, a square in ink that inverts on a dark tab, the
flat mark of docs/DESIGN.md, and four PNGs of it. iOS and Android apply their
own masks to the 180, 192 and 512.
"""
import asyncio
import base64
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
BOX = 32.0
MARGIN = 3.6          # the stacked marks make the glyph tall; this fills 16px
WEIGHT = 800
INK = ("#141414", "#ffffff")    # --accent, light and dark


def glyph_path():
    font = instantiateVariableFont(TTFont(APP / "fonts" / "inter-vi.woff2"),
                                   {"wght": WEIGHT, "opsz": 32})
    glyphs = font.getGlyphSet()
    name = font.getBestCmap()[ord("ồ")]
    bounds = BoundsPen(glyphs)
    glyphs[name].draw(bounds)
    x0, y0, x1, y1 = bounds.bounds
    scale = (BOX - 2 * MARGIN) / (y1 - y0)
    tx = (BOX - (x1 - x0) * scale) / 2 - x0 * scale
    ty = (BOX + (y1 - y0) * scale) / 2 + y0 * scale
    pen = SVGPathPen(glyphs)
    glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, tx, ty)))
    return pen.getCommands()


def svg(path):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            f'<style>.t{{fill:{INK[0]}}}.g{{fill:{INK[1]}}}@media (prefers-color-scheme:dark)'
            f'{{.t{{fill:{INK[1]}}}.g{{fill:{INK[0]}}}}}</style>'
            f'<rect class="t" width="32" height="32"/>'
            f'<path class="g" d="{path}"/></svg>\n')


async def render(source, jobs):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        # The installed Chrome, not Playwright's own download, which a plain
        # `--with playwright` does not fetch.
        browser = await p.chromium.launch(channel="chrome")
        for size, out in jobs:
            page = await (await browser.new_context(
                viewport={"width": size, "height": size}, color_scheme="light")).new_page()
            await page.set_content(
                f'<body style="margin:0"><img src="{source}" width="{size}" '
                f'height="{size}" style="display:block"></body>')
            # A broken image renders as a placeholder, not an error, so wait for
            # the picture itself rather than trusting the screenshot.
            await page.wait_for_function(
                "document.images[0].complete && document.images[0].naturalWidth > 0")
            await page.screenshot(path=APP / out)
        await browser.close()


def main():
    path = glyph_path()
    mark = svg(path)
    (APP / "favicon.svg").write_text(mark, encoding="utf-8")
    uri = "data:image/svg+xml;base64," + base64.b64encode(mark.encode()).decode()
    asyncio.run(render(uri, [(32, "favicon-32.png"), (180, "apple-touch-icon.png"),
                             (192, "icon-192.png"), (512, "icon-512.png")]))
    print("app/favicon.svg and four PNGs")


if __name__ == "__main__":
    main()
