"""
Normalización y tokenización de texto.

Se implementan recorriendo el texto carácter por carácter (autómata simple),
sin expresiones regulares, para que el comportamiento sea transparente.
"""

from __future__ import annotations

# Ligaduras tipográficas frecuentes en PDFs y caracteres "invisibles".
_REPLACEMENTS = {
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "st",
    "ﬆ": "st",
    "‘": "'",
    "’": "'",
    "‚": "'",
    "“": '"',
    "”": '"',
    "–": "-",  # en dash
    "—": "-",  # em dash
    "−": "-",  # signo menos
    " ": " ",  # espacio no separable
    " ": " ",
    " ": " ",
    "­": "",  # guion suave
    "​": "",  # espacio de ancho cero
    "‌": "",
    "‍": "",
    "﻿": "",
}


def normalize_text(text: str) -> str:
    """Reemplaza ligaduras/caracteres especiales y colapsa espacios en blanco.

    Complejidad: O(n) sobre la longitud del texto.
    """
    out: list[str] = []
    prev_space = True  # evita espacios al inicio
    for ch in text:
        ch = _REPLACEMENTS.get(ch, ch)
        if ch == "":
            continue
        for c in ch:
            if c.isspace():
                if not prev_space:
                    out.append(" ")
                prev_space = True
            else:
                out.append(c)
                prev_space = False
    if out and out[-1] == " ":
        out.pop()
    return "".join(out)


def tokenize(text: str, lowercase: bool = True) -> list[str]:
    """Divide el texto en tokens alfanuméricos maximales.

    Un token es una secuencia maximal de caracteres alfanuméricos (letras con o
    sin tilde y dígitos). Cualquier otro carácter (espacio, puntuación, guion)
    actúa como separador. Ejemplo: ``"AI-driven tools (2023)"`` ->
    ``["ai", "driven", "tools", "2023"]``.

    Complejidad: O(n).
    """
    tokens: list[str] = []
    current: list[str] = []
    for ch in text:
        if ch.isalnum():
            current.append(ch.lower() if lowercase else ch)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


_SENTENCE_END = {".", "!", "?"}
_ABBREVIATIONS = {"e.g", "i.e", "et al", "vs", "etc", "fig", "no", "dr", "prof"}


def split_sentences(text: str) -> list[str]:
    """Segmenta un texto en oraciones (heurística: ``.``, ``!`` o ``?`` seguidos de espacio y mayúscula).

    Se usa para mostrar fragmentos (párrafos/oraciones) en los casos de estudio.
    """
    sentences: list[str] = []
    start = 0
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch in _SENTENCE_END:
            nxt = i + 1
            # Debe venir un espacio y luego una mayúscula (o fin del texto).
            if nxt >= n or (text[nxt] == " " and nxt + 1 < n and text[nxt + 1].isupper()):
                candidate = text[start : i + 1].strip()
                tail = candidate.lower()
                is_abbrev = False
                for ab in _ABBREVIATIONS:
                    if tail.endswith(ab + "."):
                        is_abbrev = True
                        break
                if candidate and not is_abbrev:
                    sentences.append(candidate)
                    start = i + 1
        i += 1
    rest = text[start:].strip()
    if rest:
        sentences.append(rest)
    return sentences
