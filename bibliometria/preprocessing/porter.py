"""
Algoritmo de stemming de Porter (M. F. Porter, 1980), implementado desde cero.

Reduce una palabra en inglés a su raíz morfológica eliminando sufijos en cinco
pasos. Ejemplos: ``connections -> connect``, ``learning -> learn``,
``education -> educ``.

Definiciones del artículo original:
- Una consonante es una letra distinta de a, e, i, o, u, y distinta de 'y'
  precedida por consonante.
- Toda palabra tiene la forma ``[C](VC)^m[V]``; ``m`` es la *medida*.
- ``*v*``: el tallo contiene una vocal. ``*d``: termina en consonante doble.
- ``*o``: termina en consonante-vocal-consonante y la última no es w, x ni y.

En cada lista de reglas sólo se aplica la de sufijo más largo que coincida; si
su condición falla no se prueba ninguna otra (semántica del artículo original).
La implementación sigue el modo ``ORIGINAL_ALGORITHM`` de NLTK, que se usa como
oráculo en las pruebas unitarias.

Complejidad: O(L) por palabra, con L = longitud de la palabra (número constante
de reglas, cada una evaluada en O(L)).
"""

from __future__ import annotations

from typing import Callable, Optional

_VOWELS = "aeiou"

Rule = tuple[str, str, Optional[Callable[[str], bool]]]


class PorterStemmer:
    """Stemmer de Porter (algoritmo original de 1980)."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Predicados básicos
    # ------------------------------------------------------------------ #
    def _is_consonant(self, word: str, i: int) -> bool:
        ch = word[i]
        if ch in _VOWELS:
            return False
        if ch == "y":
            if i == 0:
                return True
            return not self._is_consonant(word, i - 1)
        return True

    def measure(self, stem: str) -> int:
        """Calcula m: número de secuencias VC en la forma [C](VC)^m[V]."""
        m = 0
        prev_vowel = False
        for i in range(len(stem)):
            consonant = self._is_consonant(stem, i)
            if consonant and prev_vowel:
                m += 1
            prev_vowel = not consonant
        return m

    def _contains_vowel(self, stem: str) -> bool:
        for i in range(len(stem)):
            if not self._is_consonant(stem, i):
                return True
        return False

    def _ends_double_consonant(self, word: str) -> bool:
        return len(word) >= 2 and word[-1] == word[-2] and self._is_consonant(word, len(word) - 1)

    def _ends_cvc(self, word: str) -> bool:
        n = len(word)
        return (
            n >= 3
            and self._is_consonant(word, n - 3)
            and not self._is_consonant(word, n - 2)
            and self._is_consonant(word, n - 1)
            and word[-1] not in "wxy"
        )

    def _positive_measure(self, stem: str) -> bool:
        return self.measure(stem) > 0

    def _measure_gt_1(self, stem: str) -> bool:
        return self.measure(stem) > 1

    @staticmethod
    def _ends_with(word: str, suffix: str) -> bool:
        """Comprueba el sufijo carácter por carácter."""
        ls, lw = len(suffix), len(word)
        if ls > lw:
            return False
        for k in range(1, ls + 1):
            if word[lw - k] != suffix[ls - k]:
                return False
        return True

    def _apply_rules(self, word: str, rules: list[Rule]) -> str:
        """Aplica la primera regla cuyo sufijo coincide (las listas están
        ordenadas de modo que el sufijo más largo se evalúa primero)."""
        for suffix, replacement, condition in rules:
            if suffix == "*d":
                if self._ends_double_consonant(word):
                    stem = word[:-2]
                    if condition is None or condition(stem):
                        return stem + replacement
                    return word
                continue
            if self._ends_with(word, suffix):
                stem = word[: len(word) - len(suffix)]
                if condition is None or condition(stem):
                    return stem + replacement
                return word
        return word

    # ------------------------------------------------------------------ #
    # Pasos del algoritmo
    # ------------------------------------------------------------------ #
    def _step1a(self, word: str) -> str:
        return self._apply_rules(
            word,
            [("sses", "ss", None), ("ies", "i", None), ("ss", "ss", None), ("s", "", None)],
        )

    def _step1b(self, word: str) -> str:
        if self._ends_with(word, "eed"):
            stem = word[:-3]
            return stem + "ee" if self.measure(stem) > 0 else word

        intermediate = None
        for suffix in ("ed", "ing"):
            if self._ends_with(word, suffix):
                candidate = word[: len(word) - len(suffix)]
                if self._contains_vowel(candidate):
                    intermediate = candidate
                    break
        if intermediate is None:
            return word

        last = intermediate[-1]
        return self._apply_rules(
            intermediate,
            [
                ("at", "ate", None),
                ("bl", "ble", None),
                ("iz", "ize", None),
                ("*d", last, lambda _stem: last not in "lsz"),
                ("", "e", lambda stem: self.measure(stem) == 1 and self._ends_cvc(stem)),
            ],
        )

    def _step1c(self, word: str) -> str:
        return self._apply_rules(word, [("y", "i", self._contains_vowel)])

    def _step2(self, word: str) -> str:
        p = self._positive_measure
        return self._apply_rules(
            word,
            [
                ("ational", "ate", p),
                ("tional", "tion", p),
                ("enci", "ence", p),
                ("anci", "ance", p),
                ("izer", "ize", p),
                ("abli", "able", p),
                ("alli", "al", p),
                ("entli", "ent", p),
                ("eli", "e", p),
                ("ousli", "ous", p),
                ("ization", "ize", p),
                ("ation", "ate", p),
                ("ator", "ate", p),
                ("alism", "al", p),
                ("iveness", "ive", p),
                ("fulness", "ful", p),
                ("ousness", "ous", p),
                ("aliti", "al", p),
                ("iviti", "ive", p),
                ("biliti", "ble", p),
            ],
        )

    def _step3(self, word: str) -> str:
        p = self._positive_measure
        return self._apply_rules(
            word,
            [
                ("icate", "ic", p),
                ("ative", "", p),
                ("alize", "al", p),
                ("iciti", "ic", p),
                ("ical", "ic", p),
                ("ful", "", p),
                ("ness", "", p),
            ],
        )

    def _step4(self, word: str) -> str:
        g = self._measure_gt_1
        return self._apply_rules(
            word,
            [
                ("al", "", g),
                ("ance", "", g),
                ("ence", "", g),
                ("er", "", g),
                ("ic", "", g),
                ("able", "", g),
                ("ible", "", g),
                ("ant", "", g),
                ("ement", "", g),
                ("ment", "", g),
                ("ent", "", g),
                ("ion", "", lambda stem: self.measure(stem) > 1 and len(stem) > 0 and stem[-1] in "st"),
                ("ou", "", g),
                ("ism", "", g),
                ("ate", "", g),
                ("iti", "", g),
                ("ous", "", g),
                ("ive", "", g),
                ("ize", "", g),
            ],
        )

    def _step5a(self, word: str) -> str:
        if self._ends_with(word, "e"):
            stem = word[:-1]
            m = self.measure(stem)
            if m > 1:
                return stem
            if m == 1 and not self._ends_cvc(stem):
                return stem
        return word

    def _step5b(self, word: str) -> str:
        if self._ends_with(word, "ll") and self.measure(word[:-1]) > 1:
            return word[:-1]
        return word

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def stem(self, word: str) -> str:
        """Devuelve la raíz de ``word`` (en minúsculas)."""
        word = word.lower()
        cached = self._cache.get(word)
        if cached is not None:
            return cached
        result = word
        if result:
            result = self._step1a(result)
            result = self._step1b(result)
            result = self._step1c(result)
            result = self._step2(result)
            result = self._step3(result)
            result = self._step4(result)
            result = self._step5a(result)
            result = self._step5b(result)
        self._cache[word] = result
        return result
