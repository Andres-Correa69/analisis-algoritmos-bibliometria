"""
Tubería (pipeline) de preprocesamiento compartida por los requerimientos 1 y 2.

Pasos: normalizar -> tokenizar (minúsculas) -> eliminar stopwords, números y
tokens de un carácter -> stemming de Porter.

Todos los algoritmos clásicos reciben la MISMA representación (secuencia de
raíces), de modo que las diferencias en los resultados se deban al algoritmo
y no al preprocesamiento.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .porter import PorterStemmer
from .stopwords import DEFAULT_STOPWORDS
from .tokenizer import normalize_text, tokenize


@dataclass
class PreprocessedText:
    """Resultado del preprocesamiento de un texto."""

    original: str
    normalized: str
    tokens: list[str]  # tokens en minúscula (antes de filtrar)
    filtered: list[str]  # tokens sin stopwords/números
    stems: list[str]  # raíces de Porter (representación final)
    stem_to_word: dict[str, str] = field(default_factory=dict)  # raíz -> palabra más frecuente

    def to_dict(self) -> dict:
        return {
            "normalized": self.normalized,
            "tokens": self.tokens,
            "filtered": self.filtered,
            "stems": self.stems,
            "stem_to_word": self.stem_to_word,
            "counts": {
                "tokens": len(self.tokens),
                "filtered": len(self.filtered),
                "stems": len(self.stems),
                "unique_stems": len(self.stem_to_word),
            },
        }


def _is_number(token: str) -> bool:
    for ch in token:
        if not ch.isdigit():
            return False
    return True


class Preprocessor:
    """Configuración del preprocesamiento."""

    def __init__(
        self,
        remove_stopwords: bool = True,
        stem: bool = True,
        min_length: int = 2,
        drop_numbers: bool = True,
        stopwords: frozenset[str] = DEFAULT_STOPWORDS,
    ) -> None:
        self.remove_stopwords = remove_stopwords
        self.stem = stem
        self.min_length = min_length
        self.drop_numbers = drop_numbers
        self.stopwords = stopwords
        self.stemmer = PorterStemmer()

    def filter_tokens(self, tokens: list[str]) -> list[str]:
        out: list[str] = []
        for t in tokens:
            if len(t) < self.min_length:
                continue
            if self.drop_numbers and _is_number(t):
                continue
            if self.remove_stopwords and t in self.stopwords:
                continue
            out.append(t)
        return out

    def process(self, text: str) -> PreprocessedText:
        normalized = normalize_text(text)
        tokens = tokenize(normalized, lowercase=True)
        filtered = self.filter_tokens(tokens)
        if self.stem:
            stems = [self.stemmer.stem(t) for t in filtered]
        else:
            stems = list(filtered)

        # Para mostrar resultados legibles: palabra más frecuente por raíz.
        votes: dict[str, dict[str, int]] = {}
        for word, st in zip(filtered, stems):
            bucket = votes.setdefault(st, {})
            bucket[word] = bucket.get(word, 0) + 1
        stem_to_word: dict[str, str] = {}
        for st, bucket in votes.items():
            best_word, best_count = "", -1
            for word, count in bucket.items():
                if count > best_count or (count == best_count and len(word) < len(best_word)):
                    best_word, best_count = word, count
            stem_to_word[st] = best_word

        return PreprocessedText(
            original=text,
            normalized=normalized,
            tokens=tokens,
            filtered=filtered,
            stems=stems,
            stem_to_word=stem_to_word,
        )

    def stems(self, text: str) -> list[str]:
        return self.process(text).stems


_DEFAULT: Preprocessor | None = None


def default_preprocessor() -> Preprocessor:
    """Instancia compartida (con caché de raíces) del preprocesador por defecto."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Preprocessor()
    return _DEFAULT
