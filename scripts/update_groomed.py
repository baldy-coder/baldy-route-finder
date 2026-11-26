"""
Fetches Sun Valley's mountain report, figures out which Bald Mountain trails
are currently groomed, and writes groomed-today.json mapped to this app's
RUN ids. Pure standard library only — no pip installs needed to run this.

Usage: python3 scripts/update_groomed.py
Writes groomed-today.json in the repo root. Committing/pushing that file is
left to the caller (the scheduled job), not done by this script.
"""
import datetime
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

REPORT_URL = "https://www.sunvalley.com/the-mountain/mountain-report/"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Resort trail name (normalized) -> our RUN id, for the handful of names
# that don't match automatically (punctuation/spelling differences).
NAME_ALIASES = {
    "i 80": "1-80",
    "lefty bowl": "leftys-bowl",
    "lower picabos street": "lower-picabo-street",
    "mid picabos street": "mid-picabo-street",
    "upper picabos street": "upper-picabo-street",
}


def normalize(name):
    s = name.lower().replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def load_our_runs():
    """Extract {normalized display name: run id} straight from index.html's RUNS object."""
    with open(os.path.join(REPO_ROOT, "index.html")) as f:
        html = f.read()
    m = re.search(r"const RUNS = \{(.*?)\n    \};", html, re.DOTALL)
    if not m:
        raise RuntimeError("Could not find RUNS data in index.html")
    pairs = re.findall(r'"([\w-]+)":\s*\{\s*id:"([\w-]+)",\s*name:"([^"]+)"', m.group(1))
    return {normalize(name): run_id for run_id, run_id2, name in pairs}


class TrailTableParser(HTMLParser):
    """Parses <tr><td>name</td><td>status</td><td>groomed</td>...</tr> rows."""

    def __init__(self):
        super().__init__()
        self.trails = []
        self._in_row = False
        self._cells = []
        self._in_cell = False
        self._cur_span_classes = None
        self._cur_span_text = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self._in_row = True
            self._cells = []
        elif tag == "td" and self._in_row:
            self._in_cell = True
            self._cells.append({"spans": []})
        elif tag == "span" and self._in_cell:
            self._cur_span_classes = attrs.get("class", "")
            self._cur_span_text = ""

    def handle_data(self, data):
        if self._cur_span_classes is not None:
            self._cur_span_text += data

    def handle_endtag(self, tag):
        if tag == "span" and self._cur_span_classes is not None:
            self._cells[-1]["spans"].append((self._cur_span_classes, self._cur_span_text.strip()))
            self._cur_span_classes = None
            self._cur_span_text = ""
        elif tag == "td":
            self._in_cell = False
        elif tag == "tr":
            self._finish_row()
            self._in_row = False

    def _finish_row(self):
        if len(self._cells) < 3:
            return
        name_spans = self._cells[0]["spans"]
        if not name_spans:
            return
        name = name_spans[-1][1]
        if not name:
            return
        status_spans = self._cells[1]["spans"] if len(self._cells) > 1 else []
        groomed_spans = self._cells[2]["spans"]
        is_open = any("mc__icon-open" in cls for cls, _ in status_spans)
        is_groomed = any("mc__icon-groomed" in cls for cls, _ in groomed_spans)
        self.trails.append({"name": name, "open": is_open, "groomed": is_groomed})


def extract_bald_mountain_section(html):
    # Specific enough to match only the content div, not the nav tab button
    # that shares the same data-tab attribute value earlier in the page.
    start_marker = '<div class="mc__tab js-mc__tab -active" data-tab="trails-bald">'
    end_marker = 'data-tab="trails-dollar"'
    start = html.find(start_marker)
    end = html.find(end_marker, start)
    if start == -1:
        raise RuntimeError("Could not find Bald Mountain trails section on page")
    return html[start: end if end != -1 else None]


def fetch_report_html():
    req = urllib.request.Request(REPORT_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_trail_status(html, our_runs_by_normalized_name):
    section = extract_bald_mountain_section(html)
    parser = TrailTableParser()
    parser.feed(section)

    groomed_ids, open_ids, unmatched = [], [], []
    for trail in parser.trails:
        norm = normalize(trail["name"])
        run_id = NAME_ALIASES.get(norm) or our_runs_by_normalized_name.get(norm)
        if not run_id:
            if trail["groomed"] or trail["open"]:
                unmatched.append(trail["name"])
            continue
        if trail["groomed"]:
            groomed_ids.append(run_id)
        if trail["open"]:
            open_ids.append(run_id)
    return groomed_ids, open_ids, unmatched, len(parser.trails)


def main():
    our_runs = load_our_runs()
    html = fetch_report_html()
    groomed_ids, open_ids, unmatched, total = get_trail_status(html, our_runs)

    output = {
        "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "groomedRunIds": sorted(groomed_ids),
        "openRunIds": sorted(open_ids),
    }
    out_path = os.path.join(REPO_ROOT, "groomed-today.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"Parsed {total} trails, {len(groomed_ids)} groomed runs matched, {len(open_ids)} open runs matched.")
    if unmatched:
        print(f"Groomed/open on resort page but unrecognized (not in our RUNS data): {unmatched}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
