#!/usr/bin/env python3
"""
fix-widows.py — glue short connector words to the word that follows them,
so they never dangle alone at the end of a wrapped line.

This is the classic Polish typesetting rule: single-letter prepositions and
conjunctions (a, i, o, u, w, z) — and, in this script, a few very common
two-letter ones (do, na, od, po, we, ze, że, by, ku, aż, co, bo) — must never
be left as the last thing on a line. The fix is to replace the space right
after such a word with a non-breaking space (U+00A0), so the renderer keeps
it glued to the word that follows.

It walks the HTML with the standard library's html.parser, so it only ever
touches real text content — never tag names, attributes, or the contents of
<style>/<script> blocks — so it's safe to run on a whole page.

Usage:
    python3 scripts/fix-widows.py index.html [more.html ...]

Edits files in place. Re-running it is safe (idempotent): a word already
followed by a non-breaking space is left alone.
"""
import re
import sys
import html
from html.parser import HTMLParser

NBSP = " "

# Polish: single-letter prepositions/conjunctions + common two-letter ones.
WORDS_PL = [
    "a", "i", "o", "u", "w", "z",
    "do", "ku", "na", "od", "po", "we", "ze", "że", "by", "aż", "co", "bo",
]
# English: short function words worth keeping off a line-end.
WORDS_EN = ["a", "an", "the", "of", "in", "to", "is", "as", "or", "by", "at", "on", "it"]
# German: short function words.
WORDS_DE = ["im", "am", "zu", "an", "in", "es", "ob", "da", "so", "ja", "ist", "und", "der", "die", "das"]

ALL_WORDS = sorted(set(WORDS_PL + WORDS_EN + WORDS_DE), key=len, reverse=True)
_pattern = re.compile(
    r"(?<=\s)(" + "|".join(re.escape(w) for w in ALL_WORDS) + r")[ \t]",
    re.IGNORECASE,
)

SKIP_TAGS = {"script", "style"}


def glue(text: str) -> str:
    return _pattern.sub(lambda m: m.group(1) + NBSP, text)


class Fixer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        self.out.append(self._tag_html(tag, attrs, False))

    def handle_startendtag(self, tag, attrs):
        self.out.append(self._tag_html(tag, attrs, True))

    def handle_endtag(self, tag):
        self.out.append(f"</{tag}>")
        if tag in SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth > 0:
            self.out.append(data)
        else:
            self.out.append(html.escape(glue(data), quote=False))

    def handle_comment(self, data):
        self.out.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.out.append(f"<!{decl}>")

    def unknown_decl(self, data):
        self.out.append(f"<![{data}]>")

    def _tag_html(self, tag, attrs, self_close):
        parts = [f"<{tag}"]
        for k, v in attrs:
            if v is None:
                parts.append(f" {k}")
            else:
                parts.append(f' {k}="{html.escape(v, quote=True)}"')
        parts.append("/>" if self_close else ">")
        return "".join(parts)

    def get_html(self):
        return "".join(self.out)


def fix_file(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    parser = Fixer()
    parser.feed(src)
    parser.close()
    out = parser.get_html()
    if out != src:
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"updated: {path}")
    else:
        print(f"no change: {path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        fix_file(p)
