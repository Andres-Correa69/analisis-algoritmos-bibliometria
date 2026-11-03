"""Estructuras comunes de los algoritmos de coincidencia exacta de cadenas."""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_MAX_TRACE = 5000  # tope de eventos de traza para no saturar la memoria/UI


@dataclass
class MatchResult:
    """Resultado de una búsqueda.

    - ``positions``: índices (base 0) donde inicia cada ocurrencia exacta.
    - ``comparisons``: comparaciones carácter-carácter realizadas en la búsqueda.
    - ``preprocessing_ns`` / ``search_ns``: tiempos medidos por separado.
    - ``trace``: eventos paso a paso (sólo si se solicitó ``trace=True``).
    - ``tables``: estructuras auxiliares (π de KMP, tablas de Boyer-Moore, ...).
    """

    algorithm: str
    pattern: str
    text_length: int
    positions: list[int] = field(default_factory=list)
    comparisons: int = 0
    preprocessing_ns: int = 0
    search_ns: int = 0
    alignments: int = 0  # posiciones del patrón probadas sobre el texto
    extra: dict = field(default_factory=dict)
    tables: dict = field(default_factory=dict)
    trace: list[dict] = field(default_factory=list)
    trace_truncated: bool = False

    @property
    def total_ns(self) -> int:
        return self.preprocessing_ns + self.search_ns

    def to_dict(self, include_trace: bool = False) -> dict:
        d = {
            "algorithm": self.algorithm,
            "pattern": self.pattern,
            "text_length": self.text_length,
            "positions": self.positions,
            "occurrences": len(self.positions),
            "comparisons": self.comparisons,
            "alignments": self.alignments,
            "preprocessing_ns": self.preprocessing_ns,
            "search_ns": self.search_ns,
            "total_ns": self.total_ns,
            "extra": self.extra,
            "tables": self.tables,
        }
        if include_trace:
            d["trace"] = self.trace
            d["trace_truncated"] = self.trace_truncated
        return d


class Tracer:
    """Acumula eventos de traza con un tope máximo."""

    def __init__(self, enabled: bool, limit: int = DEFAULT_MAX_TRACE) -> None:
        self.enabled = enabled
        self.limit = limit
        self.events: list[dict] = []
        self.truncated = False

    def add(self, **event) -> None:
        if not self.enabled:
            return
        if len(self.events) >= self.limit:
            self.truncated = True
            return
        self.events.append(event)


def validate(text: str, pattern: str) -> None:
    if not isinstance(text, str) or not isinstance(pattern, str):
        raise TypeError("El texto y el patrón deben ser cadenas")
    if len(pattern) == 0:
        raise ValueError("El patrón no puede estar vacío")
