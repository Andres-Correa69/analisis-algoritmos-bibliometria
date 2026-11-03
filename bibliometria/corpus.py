"""Carga del corpus procesado (artículos con título, autores y abstract)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

from .config import CORPUS_JSON


@dataclass(frozen=True)
class Article:
    id: int
    code: str
    file: str
    title: str
    short_title: str
    authors: tuple[str, ...]
    year: int | None
    journal: str | None
    doi: str | None
    keywords: tuple[str, ...] = field(default_factory=tuple)
    abstract: str = ""

    @property
    def label(self) -> str:
        return f"{self.code} · {self.short_title}"

    @property
    def first_author_surname(self) -> str:
        return self.authors[0].split()[-1] if self.authors else ""

    def to_dict(self, include_abstract: bool = True) -> dict:
        d = asdict(self)
        d["authors"] = list(self.authors)
        d["keywords"] = list(self.keywords)
        d["abstract_words"] = len(self.abstract.split())
        d["abstract_chars"] = len(self.abstract)
        if not include_abstract:
            d.pop("abstract")
        return d


class Corpus:
    """Colección inmutable de artículos indexada por id."""

    def __init__(self, articles: list[Article]) -> None:
        self.articles = sorted(articles, key=lambda a: a.id)
        self._by_id = {a.id: a for a in self.articles}

    def __len__(self) -> int:
        return len(self.articles)

    def __iter__(self):
        return iter(self.articles)

    def get(self, article_id: int) -> Article:
        try:
            return self._by_id[article_id]
        except KeyError as exc:
            raise KeyError(f"No existe el artículo con id={article_id}") from exc

    @property
    def ids(self) -> list[int]:
        return [a.id for a in self.articles]

    @classmethod
    def from_json(cls, path: Path = CORPUS_JSON) -> "Corpus":
        if not Path(path).exists():
            raise FileNotFoundError(
                f"No existe {path}. Ejecute primero: python -m bibliometria.extraction.build_corpus"
            )
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        articles = [
            Article(
                id=int(r["id"]),
                code=r.get("code") or f"A{int(r['id']):02d}",
                file=r["file"],
                title=r["title"],
                short_title=r.get("short_title") or r["title"],
                authors=tuple(r.get("authors", [])),
                year=r.get("year"),
                journal=r.get("journal"),
                doi=r.get("doi"),
                keywords=tuple(r.get("keywords", [])),
                abstract=r.get("abstract", ""),
            )
            for r in raw
        ]
        return cls(articles)


@lru_cache(maxsize=1)
def load_corpus() -> Corpus:
    """Corpus por defecto (se carga una sola vez por proceso)."""
    return Corpus.from_json()
