"""
Extracción automática de metadatos desde los artículos en PDF.

Para cada PDF se obtienen: título, autores, abstract, palabras clave, año,
revista y DOI. Se usa PyMuPDF únicamente para leer las líneas de texto de la
primera página junto con su posición (bbox) y tamaño de fuente; la lógica de
reconocimiento es propia y se basa en la geometría de la página:

1. **Título**: se agrupan las líneas por tamaño de fuente en bloques
   verticalmente contiguos y se elige el bloque más parecido al nombre del
   archivo (``"N. Título.pdf"``), medido con 2·LCS/(|a|+|b|) sobre tokens.
   No basta con "la fuente más grande": en Elsevier y MDPI el nombre de la
   revista tiene una fuente mayor que el título.
2. **Autores**: primer bloque de líneas debajo del título con aspecto de lista
   de nombres. Se descartan los superíndices (marcas de afiliación) por su
   tamaño de fuente y se separa por ``,``, ``and``, ``&``, ``|`` y ``·``.
3. **Abstract**: desde el encabezado "Abstract"/"A B S T R A C T" se recorren
   las líneas de la misma columna hasta un marcador de fin (Keywords,
   Introduction, ©, Received, ...). Las barras laterales y la columna de
   "Article info" quedan excluidas por posición horizontal.
4. **Guiones de fin de línea**: se decide si ``edu-|cation`` se une
   (``education``) o se conserva (``AI-|driven``) consultando las frecuencias
   de ambas formas en el texto completo del propio documento.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pymupdf

from ..preprocessing.tokenizer import tokenize

# --------------------------------------------------------------------------- #
# Limpieza de texto
# --------------------------------------------------------------------------- #

_CLEAN_MAP = {
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "­": "",  # guion suave
    "​": "",
    "‌": "",
    "‍": "",
    "﻿": "",
    " ": " ",
    " ": " ",
    " ": " ",
    " ": " ",
    " ": " ",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "‐": "-",  # guion tipográfico
    "‑": "-",  # guion no separable
}

_HYPHENS = ("-", "‐", "‑")
_STRUCTURED_LABELS = (
    "Purpose",
    "Design/methodology/approach",
    "Findings",
    "Research limitations/implications",
    "Practical implications",
    "Social implications",
    "Originality/value",
)


def clean_text(text: str) -> str:
    """Reemplaza ligaduras, comillas tipográficas y espacios especiales; colapsa espacios."""
    text = unicodedata.normalize("NFC", text)
    out = []
    for ch in text:
        out.append(_CLEAN_MAP.get(ch, ch))
    return " ".join("".join(out).split())


def _fix_spacing_diacritics(text: str) -> str:
    """Corrige acentos separados que algunos PDF codifican aparte (``Gaševi´c`` -> ``Gašević``)."""
    pairs = {"´c": "ć", "´C": "Ć", "´s": "ś", "´n": "ń", "´z": "ź", "´e": "é", "´a": "á", "´o": "ó", "´i": "í", "´u": "ú"}
    for bad, good in pairs.items():
        text = text.replace(bad, good)
    return text


# --------------------------------------------------------------------------- #
# Modelo de líneas de texto
# --------------------------------------------------------------------------- #


@dataclass
class TextLine:
    text: str  # texto completo de la línea
    main: str  # texto sin superíndices
    size: float  # tamaño de fuente dominante
    bold: bool
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def height(self) -> float:
        return self.y1 - self.y0


def _join_spans(spans: list[dict], drop_superscripts: bool) -> str:
    parts: list[str] = []
    prev_x1 = None
    dominant = _dominant_size(spans)
    for s in spans:
        txt = s["text"]
        if not txt:
            continue
        if drop_superscripts and _is_superscript(s, dominant):
            prev_x1 = s["bbox"][2]
            continue
        if parts and prev_x1 is not None:
            gap = s["bbox"][0] - prev_x1
            if gap > 0.25 * dominant and not parts[-1].endswith(" ") and not txt.startswith(" "):
                parts.append(" ")
        parts.append(txt)
        prev_x1 = s["bbox"][2]
    return "".join(parts)


def _dominant_size(spans: list[dict]) -> float:
    weight: dict[float, int] = {}
    for s in spans:
        k = round(s["size"], 1)
        weight[k] = weight.get(k, 0) + len(s["text"].strip())
    best, best_w = 0.0, -1
    for k, w in weight.items():
        if w > best_w:
            best, best_w = k, w
    return best


def _is_superscript(span: dict, dominant: float) -> bool:
    txt = span["text"].strip()
    if not txt:
        return False
    if span["flags"] & 1:  # bandera de superíndice de PyMuPDF
        return True
    if span["size"] < 0.8 * dominant and len(txt) <= 12:
        allowed = set("0123456789,*†‡§¶#abcdefgh ")
        return all(c in allowed for c in txt)
    return False


def page_lines(page: pymupdf.Page) -> list[TextLine]:
    """Líneas horizontales de una página, ordenadas por (y, x)."""
    lines: list[TextLine] = []
    data = page.get_text("dict")
    for block in data["blocks"]:
        if block.get("type") != 0:
            continue
        for ln in block["lines"]:
            if tuple(ln["dir"]) != (1.0, 0.0):
                continue
            spans = [s for s in ln["spans"] if s["text"]]
            if not spans:
                continue
            text = _fix_spacing_diacritics(_join_spans(spans, drop_superscripts=False)).strip()
            if not text:
                continue
            main = _fix_spacing_diacritics(_join_spans(spans, drop_superscripts=True)).strip()
            x0, y0, x1, y1 = ln["bbox"]
            lines.append(
                TextLine(
                    text=text,
                    main=main,
                    size=_dominant_size(spans),
                    bold=any(s["flags"] & 16 for s in spans if s["text"].strip()),
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                )
            )
    lines.sort(key=lambda tl: (round(tl.y0, 0), tl.x0))
    return lines


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Longitud de la subsecuencia común más larga (programación dinámica)."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
            else:
                cur[j] = prev[j] if prev[j] >= cur[j - 1] else cur[j - 1]
        prev = cur
    return prev[len(b)]


def sequence_dice(a: str, b: str) -> float:
    """2·LCS(tokens_a, tokens_b) / (|tokens_a| + |tokens_b|)."""
    ta, tb = tokenize(a), tokenize(b)
    if not ta and not tb:
        return 1.0
    return 2.0 * _lcs_length(ta, tb) / (len(ta) + len(tb))


def _word_counts(text: str) -> tuple[dict[str, int], dict[str, int]]:
    """Frecuencias de palabras y de compuestos con guion en todo el documento."""
    words: dict[str, int] = {}
    hyphenated: dict[str, int] = {}
    for raw in clean_text(text).split():
        token = raw.strip(".,;:()[]{}\"'!?").lower()
        if not token:
            continue
        if "-" in token and not token.startswith("-") and not token.endswith("-"):
            hyphenated[token] = hyphenated.get(token, 0) + 1
            for piece in token.split("-"):
                if piece:
                    words[piece] = words.get(piece, 0) + 1
        else:
            words[token] = words.get(token, 0) + 1
    return words, hyphenated


class _Joiner:
    """Une líneas reparando los guiones de fin de línea."""

    def __init__(self, words: dict[str, int], hyphenated: dict[str, int]) -> None:
        self.words = words
        self.hyphenated = hyphenated

    def join(self, lines: list[str]) -> str:
        out = ""
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if not out:
                out = line
                continue
            if out.endswith("­"):
                out = out[:-1] + line
            elif out.endswith(_HYPHENS) and len(out) >= 2 and out[-2].isalpha():
                out = self._join_hyphen(out, line)
            elif out.endswith(("/", "\u2014", "\u2013")):
                out = out + line  # "countries/|regions", "stakeholders—|like"
            else:
                out = out + " " + line
        return out

    def _join_hyphen(self, left: str, right: str) -> str:
        prefix = left[:-1].split(" ")[-1]
        suffix = right.split(" ")[0]
        p = prefix.strip(".,;:()[]\"'").lower()
        s = suffix.strip(".,;:()[]\"'").lower()
        joined_count = self.words.get(p + s, 0)
        hyph_count = self.hyphenated.get(p + "-" + s, 0)
        keep = False
        if hyph_count > joined_count:
            keep = True
        elif hyph_count == joined_count == 0 and (suffix[:1].isupper() or prefix.isupper()):
            keep = True  # p. ej. "AI-" + "Driven", "COVID-" + "19"
        if keep:
            return left[:-1] + "-" + right
        return left[:-1] + right


# --------------------------------------------------------------------------- #
# Detección de campos
# --------------------------------------------------------------------------- #

_NON_AUTHOR_PREFIXES = (
    "abstract",
    "received",
    "accepted",
    "published",
    "department",
    "university",
    "institute",
    "school",
    "faculty",
    "college",
    "centre",
    "center",
    "contents",
    "journal",
    "correspondence",
    "citation",
    "open access",
    "review",
    "research",
    "systematic review",
    "https",
    "doi",
    "©",
    "a r t i c tl e",
)


def _plausible_author_line(text: str) -> bool:
    low = text.lower().strip()
    if not low or "@" in low:
        return False
    for p in _NON_AUTHOR_PREFIXES:
        if low.startswith(p):
            return False
    capitalized = 0
    for w in text.replace(",", " ").split():
        if w[:1].isupper() and any(c.isalpha() for c in w):
            capitalized += 1
    return capitalized >= 2


def parse_author_names(text: str) -> list[str]:
    t = " " + clean_text(text) + " "
    for sep in (" and ", " & ", "|", "·", "•", ";"):
        t = t.replace(sep, ",")
    names: list[str] = []
    for part in t.split(","):
        cleaned = []
        for ch in part:
            if ch.isdigit() or ch in "*†‡§¶#":
                continue
            cleaned.append(ch)
        words = "".join(cleaned).split()
        while words and len(words[-1]) == 1 and words[-1].islower():
            words.pop()  # marcas de afiliación "a", "b" no detectadas como superíndice
        if len(words) >= 2:
            names.append(" ".join(words))
    return names


_HEADING_RE = re.compile(r"^\s*(a\s?b\s?s\s?t\s?r\s?a\s?c\s?t)\b\s*[:.\-–—]?\s*", re.IGNORECASE)
_SECTION_RE = re.compile(r"^\s*(\d+(\.\d+)*\.?\s+)?(introduction|background)\s*$", re.IGNORECASE)
_IN_COLUMN_STOPS = (
    "keywords",
    "keyword",
    "index terms",
    "©",
    "copyright",
    "citation:",
    "received",
    "accepted",
    "published",
    "correspondence",
    "*correspondence",
    "cite this",
    "article history",
    "paper type",
    "jel classification",
    "https://doi",
    "doi:",
    "e-mail",
    "email:",
    "abbreviations",
)


@dataclass
class ExtractedArticle:
    id: int
    file: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    keywords: list[str] = field(default_factory=list)
    abstract: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class PdfExtractor:
    """Extrae los metadatos de un artículo científico en PDF."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.doc = pymupdf.open(self.path)
        self.page = self.doc[0]
        self.lines = page_lines(self.page)
        full_text = "".join(p.get_text() for p in self.doc)
        self.full_text = full_text
        words, hyphenated = _word_counts(full_text)
        self.joiner = _Joiner(words, hyphenated)
        self.warnings: list[str] = []

    # ---------------------------------------------------------------- título
    @property
    def filename_title(self) -> str:
        stem = self.path.stem
        head, _, rest = stem.partition(". ")
        return rest if head.isdigit() else stem

    @property
    def file_id(self) -> int:
        head = self.path.stem.split(".")[0]
        return int(head) if head.isdigit() else 0

    def _title_runs(self) -> list[list[TextLine]]:
        height = self.page.rect.height
        top = [tl for tl in self.lines if tl.y0 < 0.55 * height and tl.size >= 9]
        sizes: list[float] = []
        for tl in top:
            if not any(abs(tl.size - s) < 0.3 for s in sizes):
                sizes.append(tl.size)
        runs: list[list[TextLine]] = []
        for s in sizes:
            same = sorted((tl for tl in top if abs(tl.size - s) < 0.3), key=lambda tl: (tl.y0, tl.x0))
            current: list[TextLine] = []
            for tl in same:
                if current and (tl.y0 - current[-1].y1) > 0.9 * s:
                    runs.append(current)
                    current = []
                current.append(tl)
            if current:
                runs.append(current)
        return runs

    def detect_title(self) -> tuple[str, list[TextLine]]:
        anchor = self.filename_title
        best_score, best_run = -1.0, None
        for run in self._title_runs():
            text = self.joiner.join([tl.text for tl in run])
            score = sequence_dice(text, anchor)
            if score > best_score:
                best_score, best_run = score, run
        if best_run is None or best_score < 0.5:
            self.warnings.append(f"título: coincidencia baja con el nombre de archivo ({best_score:.2f})")
            meta = (self.doc.metadata or {}).get("title") or ""
            if len(meta.split()) >= 4 and "proof" not in meta.lower():
                return clean_text(meta), best_run or []
            return clean_text(anchor), best_run or []
        title = clean_text(self.joiner.join([tl.text for tl in best_run]))
        return title, best_run

    # --------------------------------------------------------------- autores
    def detect_authors(self, title_run: list[TextLine]) -> list[str]:
        if not title_run:
            return []
        bottom = max(tl.y1 for tl in title_run)
        tsize = title_run[0].size
        window = [tl for tl in self.lines if bottom - 1 <= tl.y0 <= bottom + 6 * tsize]
        first = None
        for tl in window:
            if _plausible_author_line(tl.main):
                first = tl
                break
        if first is None:
            self.warnings.append("autores: no se encontró la línea de autores")
            return []
        group = [first]
        band_end = first.y1
        for tl in window:
            if tl is first or tl.y0 < first.y0 - 1:
                continue
            same_size = abs(tl.size - first.size) < 0.35
            same_row = abs(tl.y0 - first.y0) < 0.5 * first.size
            contiguous = tl.y0 - band_end <= 0.8 * first.size
            if same_size and (same_row or contiguous) and _plausible_continuation(tl.main):
                group.append(tl)
                band_end = max(band_end, tl.y1)
        group.sort(key=lambda tl: (round(tl.y0 / (0.5 * first.size)), tl.x0))
        text = " ".join(tl.main for tl in group)
        names = parse_author_names(text)
        if not names:
            self.warnings.append("autores: lista vacía tras el análisis")
        return names

    # -------------------------------------------------------------- abstract
    def detect_abstract(self) -> str:
        heading = None
        for tl in self.lines:
            if _HEADING_RE.match(tl.text):
                rest = _HEADING_RE.sub("", tl.text, count=1)
                if not rest or rest[:1].isupper() or tl.bold:
                    heading = tl
                    break
        if heading is None:
            self.warnings.append("abstract: no se encontró el encabezado")
            return ""

        stop_y = None
        for tl in self.lines:
            if tl.y0 > heading.y0 + 1 and _SECTION_RE.match(tl.text):
                stop_y = tl.y0
                break

        collected: list[str] = []
        first_text = _HEADING_RE.sub("", heading.text, count=1).strip()
        if first_text:
            collected.append(first_text)
        last_y1 = heading.y1
        col_x0 = heading.x0
        for tl in self.lines:
            if tl is heading or tl.y0 <= heading.y0 + 0.5:
                continue
            if stop_y is not None and tl.y0 >= stop_y - 1:
                break
            if not (col_x0 - 3 <= tl.x0 <= col_x0 + 40):
                continue  # otra columna o barra lateral
            compact = tl.text.lower().replace(" ", "")
            if any(compact.startswith(s.replace(" ", "")) for s in _IN_COLUMN_STOPS):
                break
            if collected and tl.y0 - last_y1 > 3.5 * tl.size:
                break
            collected.append(tl.text)
            last_y1 = tl.y1

        text = self.joiner.join(collected)
        text = clean_text(text)
        for label in _STRUCTURED_LABELS:  # resúmenes estructurados (Emerald)
            text = re.sub(rf"(^|\s){re.escape(label)}\s*[–—-]\s+", rf"\1{label}: ", text)
        return text

    # --------------------------------------------------------- palabras clave
    def detect_keywords(self) -> list[str]:
        kw_line = None
        for tl in self.lines:
            if tl.text.lower().replace(" ", "").startswith("keyword"):
                kw_line = tl
                break
        if kw_line is None:
            return []
        label = re.match(r"^\s*k\s?e\s?y\s?w\s?o\s?r\s?d\s?s?\s*[:.\-–—]?\s*", kw_line.text, re.IGNORECASE)
        first = kw_line.text[label.end():] if label else kw_line.text
        parts = [first] if first.strip() else []
        # Si el rótulo va solo en su línea (Wiley: "K E Y W O R D S"), el tamaño de
        # referencia es el de la primera línea de palabras clave.
        ref_size = kw_line.size if parts else None
        last_y1 = kw_line.y1
        for tl in self.lines:
            if tl.y0 <= kw_line.y0 + 0.5:
                continue
            if not (kw_line.x0 - 3 <= tl.x0 <= kw_line.x0 + 40):
                continue
            if ref_size is None:
                ref_size = tl.size
            if tl.y0 - last_y1 > 0.9 * tl.size or abs(tl.size - ref_size) > 0.6:
                break
            low = tl.text.lower()
            if _SECTION_RE.match(tl.text) or any(low.startswith(s) for s in ("paper type", "©", "a b s t r a c t", "article history", "citation", "1 ", "1.")):
                break
            parts.append(tl.text)
            last_y1 = tl.y1
        separators = (";", ",", "·", "•")
        raw = " ".join(parts)
        if any(sep in raw for sep in separators):
            text = clean_text(self.joiner.join(parts))
            for sep in separators[1:]:
                text = text.replace(sep, ";")
            if ";" not in text:
                text = text.replace(",", ";")
            items = [k.strip(" .") for k in text.split(";")]
        else:
            items = [clean_text(p).strip(" .") for p in parts]
        return [k for k in items if k]

    # ----------------------------------------------------- año, DOI y revista
    def _first_page_text(self) -> str:
        return clean_text(self.page.get_text())

    def detect_doi(self) -> str | None:
        text = self._first_page_text()
        candidates = []
        for m in re.finditer(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text):
            doi = m.group(0).rstrip(".,;)")
            context = text[max(0, m.start() - 12) : m.start()].lower()
            strong = "doi.org/" in context or "doi" in context
            candidates.append((0 if strong else 1, m.start(), doi))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][2]

    def detect_year(self) -> int | None:
        text = self._first_page_text()
        patterns = [
            r"\((20\d{2}|19\d{2})\)\s*\d",  # "(2022) 100101", "(2024) 21:40"
            r"\b(20\d{2}|19\d{2}),\s*\d+,\s*\d+",  # MDPI "2024, 14, 636"
            r"Vol\.\s*\d+\s*No\.\s*\d+,\s*(20\d{2})",  # Emerald
            r",\s*(20\d{2});\s*\d+",  # Wiley "2024; 59"
            r"Published[^0-9]{0,25}\d{1,2}\s+[A-Za-z]+\s+(20\d{2})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return int(m.group(1))
        years = [int(y) for y in re.findall(r"\b(20[0-2]\d)\b", text)]
        return max(years) if years else None

    def detect_journal(self, title: str) -> str | None:
        lines = self.lines
        height = self.page.rect.height
        # 1) Elsevier: línea siguiente a "Contents lists available at ScienceDirect".
        for i, tl in enumerate(lines):
            if tl.text.lower().startswith("contents lists available"):
                for nxt in lines[i + 1 : i + 4]:
                    if nxt.size >= 10:
                        return clean_text(nxt.text)
        text = self._first_page_text()
        # 2a) Wiley / Taylor & Francis: "© 2024 The Authors. <Revista> published by ...".
        m = re.search(r"©\s*\d{4}\s+The Authors?\.?\s+(.+?)\s+published by", text)
        if m:
            return clean_text(m.group(1))
        # 2b) Emerald: "Education + Training Vol. 66 No. 7, 2024".
        m = re.search(r"([A-Z][A-Za-z&+þ ]{3,80}?)\s+Vol\.\s*\d+\s*No\.", text)
        if m:
            return clean_text(m.group(1).replace("þ", "+"))
        # 3) Cabecera grande en la franja superior (Springer BMC, logotipo MDPI).
        band = [
            tl
            for tl in lines
            if tl.y0 < 0.13 * height
            and tl.size >= 11
            and sequence_dice(tl.text, title) < 0.5
            and not _is_article_label(tl.text)
        ]
        if band:
            biggest = max(tl.size for tl in band)
            chosen = [tl for tl in band if abs(tl.size - biggest) < 0.3]
            chosen.sort(key=lambda tl: tl.y0)
            name = clean_text(" ".join(tl.text for tl in chosen))
            if name.islower():
                name = " ".join(w.capitalize() for w in name.split())
            if len(name) > 6:
                return name
        # 4a) Cabecera Springer "Autor et al. <Revista> (2019) 16:39" (puede ocupar dos líneas).
        header = clean_text(" ".join(tl.text for tl in lines if tl.y0 < 0.09 * height))
        m = re.search(r"et al\.\s+(.+?)\s+\((?:19|20)\d{2}\)", header)
        if m:
            return m.group(1).strip()
        # 4b) Cabecera "Revista (2023) 6:408–426" o "Revista, 2024; 59:e12663".
        for tl in lines[:12]:
            m = re.match(r"^(?!.*et al\.)([A-Z][A-Za-z:&+ ]{5,90}?),?\s+\(?(?:19|20)\d{2}\)?[;:,]?\s*\d", clean_text(tl.text))
            if m:
                return m.group(1).strip()
        m = re.search(r"([A-Z][A-Za-z ]{5,80}),\s*20\d{2};\s*\d+", text)
        if m:
            return m.group(1).strip()
        return None

    # ------------------------------------------------------------------ todo
    def extract(self) -> ExtractedArticle:
        title, run = self.detect_title()
        article = ExtractedArticle(
            id=self.file_id,
            file=self.path.name,
            title=title,
            authors=self.detect_authors(run),
            year=self.detect_year(),
            journal=self.detect_journal(title),
            doi=self.detect_doi(),
            keywords=self.detect_keywords(),
            abstract=self.detect_abstract(),
        )
        if len(article.abstract.split()) < 60:
            self.warnings.append("abstract: texto sospechosamente corto")
        article.warnings = list(self.warnings)
        return article


_ARTICLE_LABELS = ("open access", "review article", "research article", "systematic review", "research review", "review", "article")


def _is_article_label(text: str) -> bool:
    low = " ".join(text.lower().split())
    if "open access" in low:
        return True
    return low in _ARTICLE_LABELS or low.replace(" ", "") in ("reviewarticle", "researcharticle")


def _plausible_continuation(text: str) -> bool:
    low = text.lower().strip()
    if not low or "@" in low:
        return False
    for p in _NON_AUTHOR_PREFIXES:
        if low.startswith(p):
            return False
    return True


def extract_pdf(path: Path) -> ExtractedArticle:
    return PdfExtractor(path).extract()
