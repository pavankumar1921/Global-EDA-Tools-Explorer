"""Standard-library HTML helpers: tables (with rowspan/colspan), infoboxes, page metadata.

BeautifulSoup is not in the Crucible catalog as a declared tool (it only arrives bundled inside
jupyterlab), so the project parses HTML with html.parser from the standard library.
"""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

WIKI_BASE = "https://en.wikipedia.org"


def text_of(fragment):
    """Visible text of an HTML fragment: drops <sup> footnotes, <style>, tags; collapses whitespace."""
    s = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", fragment or "", flags=re.S | re.I)
    s = re.sub(r"<sup[^>]*>.*?</sup>", "", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</li>|</p>", "; ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,;:.)])", r"\1", s)
    s = re.sub(r"(;\s*)+", "; ", s)
    return s.strip(" ;")


def links_of(fragment, base=WIKI_BASE):
    """[(absolute_href, link_text)] for every <a href> in the fragment, footnotes excluded."""
    frag = re.sub(r"<sup[^>]*>.*?</sup>", "", fragment or "", flags=re.S | re.I)
    out = []
    for href, inner in re.findall(r'<a\s[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', frag, re.S | re.I):
        out.append((urljoin(base, html.unescape(href)), text_of(inner)))
    return out


def wiki_article(href):
    """Normalise a link to an English Wikipedia article URL, or '' if it is not one."""
    m = re.match(r"https?://en\.wikipedia\.org/wiki/([^#?]+)", href or "")
    if not m or ":" in m.group(1):  # File:, Help:, Special: ... are not articles
        return ""
    return WIKI_BASE + "/wiki/" + m.group(1)


class _TableParser(HTMLParser):
    """Collects every <table> as a list of rows; each cell = dict(html, header, rowspan, colspan)."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tables, self._stack = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._stack.append({"cls": a.get("class", ""), "rows": [], "cell": None, "pos": self.getpos()})
            return
        if not self._stack:
            return
        t = self._stack[-1]
        if tag == "tr":
            t["rows"].append([])
        elif tag in ("td", "th") and t["rows"] is not None:
            if not t["rows"]:
                t["rows"].append([])
            # the cell's class (e.g. 'table-yes') is kept as a leading comment for yes/no columns
            t["cell"] = {"header": tag == "th", "html": ["<!--cls:%s-->" % a.get("class", "")],
                         "rowspan": _int(a.get("rowspan")), "colspan": _int(a.get("colspan"))}
            t["rows"][-1].append(t["cell"])
        elif t["cell"] is not None:
            t["cell"]["html"].append(self.get_starttag_text() or "")

    def handle_endtag(self, tag):
        if not self._stack:
            return
        t = self._stack[-1]
        if tag == "table":
            self._stack.pop()
            self.tables.append(t)
            if self._stack and self._stack[-1]["cell"] is not None:  # nested table: keep as text
                self._stack[-1]["cell"]["html"].append("")
        elif tag in ("td", "th"):
            t["cell"] = None
        elif t["cell"] is not None:
            t["cell"]["html"].append("</%s>" % tag)

    def _data(self, d):
        if self._stack and self._stack[-1]["cell"] is not None:
            self._stack[-1]["cell"]["html"].append(d)

    handle_data = _data

    def handle_entityref(self, name):
        self._data("&%s;" % name)

    def handle_charref(self, name):
        self._data("&#%s;" % name)


def _int(v):
    try:
        return max(1, int(re.sub(r"\D", "", v or "") or 1))
    except ValueError:
        return 1


def expand_grid(rows):
    """Apply rowspan/colspan so every row has one entry per logical column."""
    grid, pending = [], {}  # pending[col] = (cell, rows_left)
    for row in rows:
        out, col, cells = [], 0, list(row)
        while cells or col in pending:
            if col in pending:
                cell, left = pending[col]
                out.append(cell)
                pending[col] = (cell, left - 1)
                if left - 1 == 0:
                    del pending[col]
                col += 1
                continue
            cell = cells.pop(0)
            for _ in range(cell["colspan"]):
                out.append(cell)
                if cell["rowspan"] > 1:
                    pending[col] = (cell, cell["rowspan"] - 1)
                col += 1
        grid.append(out)
    return grid


def cell_flag(cell_html):
    """'yes' / 'no' / '' for a feature cell, read from its text or its table-yes/table-no class."""
    m = re.match(r"<!--cls:([^>]*)-->", cell_html or "")
    cls = m.group(1) if m else ""
    t = text_of(cell_html).lower()
    if "table-yes" in cls or t.startswith("yes"):
        return "yes"
    if "table-no" in cls or t.startswith("no"):
        return "no"
    return ""


def parse_tables(page_html, css_class="wikitable"):
    """Return [{'section': heading, 'header': [...], 'rows': [[cell_html, ...], ...]}] in page order."""
    p = _TableParser()
    p.feed(page_html)
    # map each table to the nearest preceding h2/h3 heading (by source line)
    lines = page_html.splitlines()
    headings = []
    for i, line in enumerate(lines, start=1):
        for m in re.finditer(r"<h([23])[^>]*>(.*?)</h\1>", line):
            headings.append((i, int(m.group(1)), text_of(m.group(2))))
    out = []
    for t in sorted(p.tables, key=lambda t: t["pos"]):
        if css_class not in t["cls"]:
            continue
        line = t["pos"][0]
        h2 = next((h for ln, lvl, h in reversed(headings) if ln <= line and lvl == 2), "")
        h3 = next((h for ln, lvl, h in reversed(headings) if ln <= line), "")
        grid = expand_grid([r for r in t["rows"] if r])
        n_head = 0
        while n_head < len(grid) and all(c["header"] for c in grid[n_head]):
            n_head += 1
        n_head = max(n_head, 1)
        header = []
        for col in range(max(len(r) for r in grid[:n_head])):
            parts = []
            for r in grid[:n_head]:
                if col < len(r):
                    t_ = text_of("".join(r[col]["html"]))
                    if t_ and t_ not in parts:
                        parts.append(t_)
            header.append(" / ".join(parts))
        # Wikipedia repeats the header row inside long tables: drop body rows made only of header cells
        body = [["".join(c["html"]) for c in r] for r in grid[n_head:] if not all(c["header"] for c in r)]
        out.append({"section": h2, "subsection": h3, "header": header, "rows": body})
    return out


def balanced(s, start, tag):
    """The element starting at s[start] up to its matching close tag (handles nesting)."""
    depth, pat = 0, re.compile(r"<(/?)%s\b" % tag, re.I)
    for m in pat.finditer(s, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            end = s.find(">", m.end())
            return s[start:end + 1]
    return s[start:]


def parse_infobox(page_html):
    """{label: (text, links)} from the first infobox on a Wikipedia article."""
    m = re.search(r'<table[^>]*class="[^"]*\binfobox\b', page_html)
    box = balanced(page_html, m.start(), "table") if m else ""
    out = {}
    for th, td in re.findall(r'<th[^>]*infobox-label[^>]*>(.*?)</th>\s*<td[^>]*infobox-data[^>]*>(.*?)</td>',
                             box, re.S):
        label = text_of(th).lower()
        out.setdefault(label, (text_of(td), links_of(td)))
    return out


def lead_paragraph(page_html):
    """First substantial paragraph of a Wikipedia article (the article's own one-sentence definition)."""
    body = page_html
    m = re.search(r'<table[^>]*class="[^"]*\binfobox\b', page_html)
    if m:
        body = page_html[m.start() + len(balanced(page_html, m.start(), "table")):]
    for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S):
        t = text_of(p)
        if len(t) > 60:
            return t[:600]
    return ""


def page_meta(page_html):
    """Title, og:site_name and meta description of a vendor page (used as text evidence)."""
    def meta(name):
        m = re.search(r'<meta[^>]+(?:name|property)="%s"[^>]+content="([^"]*)"' % re.escape(name), page_html, re.I) \
            or re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:name|property)="%s"' % re.escape(name), page_html, re.I)
        return text_of(m.group(1)) if m else ""
    t = re.search(r"<title[^>]*>(.*?)</title>", page_html, re.I | re.S)
    return {"title": text_of(t.group(1)) if t else "", "site_name": meta("og:site_name"),
            "description": meta("description") or meta("og:description")}
