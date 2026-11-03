"""Pruebas de KMP, Boyer-Moore y Rabin-Karp (Requerimiento 3)."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bibliometria.string_matching.boyer_moore import bad_character_table, boyer_moore_search, good_suffix_table
from bibliometria.string_matching.kmp import kmp_search, prefix_function
from bibliometria.string_matching.naive import naive_search
from bibliometria.string_matching.rabin_karp import rabin_karp_search
from bibliometria.string_matching.service import fold_case, search_corpus, trace_search

ALGOS = [kmp_search, boyer_moore_search, naive_search, lambda t, p: rabin_karp_search(t, p, modulus=13)]


def _brute(text, pattern):
    return [i for i in range(len(text) - len(pattern) + 1) if text[i : i + len(pattern)] == pattern]


# ------------------------------------------------------------- tablas a mano


def test_prefix_function_textbook_examples():
    assert prefix_function("ababaca") == [0, 0, 1, 2, 3, 0, 1]  # Cormen et al.
    assert prefix_function("aabaaab") == [0, 1, 0, 1, 2, 2, 3]
    assert prefix_function("abcd") == [0, 0, 0, 0]


def test_bad_character_table():
    assert bad_character_table("learning") == {"l": 0, "e": 1, "a": 2, "r": 3, "n": 6, "i": 5, "g": 7}


def test_good_suffix_table_known_example():
    shift, bpos = good_suffix_table("ABBABAB")
    assert shift == [5, 5, 5, 5, 2, 5, 4, 1]
    assert bpos == [5, 6, 4, 5, 6, 7, 7, 8]


def test_rabin_karp_hash_by_hand():
    # H("ab") con d=10, q=13: (97·10 + 98) mod 13 = 1068 mod 13 = 2
    r = rabin_karp_search("xxab", "ab", base=10, modulus=13)
    assert r.tables["pattern_hash"] == 1068 % 13
    assert r.tables["h"] == 10 % 13
    assert r.positions == [2]


def test_rabin_karp_small_modulus_produces_spurious_hits_but_correct_result():
    text = "artificial intelligence and intelligent tutoring"
    r = rabin_karp_search(text, "intelligen", modulus=13)
    assert r.positions == _brute(text, "intelligen")
    assert r.extra["spurious_hits"] > 0
    big = rabin_karp_search(text, "intelligen")
    assert big.extra["spurious_hits"] == 0


# --------------------------------------------------- correctitud y propiedades


@pytest.mark.parametrize("search", ALGOS)
@pytest.mark.parametrize(
    "text,pattern",
    [("abracadabra", "abra"), ("aaaaa", "aa"), ("hello", "z"), ("ab", "abc"), ("learning machine learning", "learning")],
)
def test_known_cases(search, text, pattern):
    assert search(text, pattern).positions == _brute(text, pattern)


@given(st.text(alphabet="ab", max_size=40), st.text(alphabet="ab", min_size=1, max_size=5))
@settings(max_examples=400, deadline=None)
def test_all_algorithms_agree_with_brute_force_binary_alphabet(text, pattern):
    expected = _brute(text, pattern)
    assert kmp_search(text, pattern).positions == expected
    assert boyer_moore_search(text, pattern).positions == expected
    assert rabin_karp_search(text, pattern, modulus=7).positions == expected


@given(st.text(alphabet="acgt ", max_size=80), st.text(alphabet="acgt ", min_size=1, max_size=8))
@settings(max_examples=300, deadline=None)
def test_all_algorithms_agree_with_brute_force_dna_alphabet(text, pattern):
    expected = _brute(text, pattern)
    for search in ALGOS:
        assert search(text, pattern).positions == expected


@given(st.text(alphabet="abc", max_size=60), st.text(alphabet="abc", min_size=1, max_size=6))
@settings(max_examples=200, deadline=None)
def test_kmp_comparisons_are_at_most_2n(text, pattern):
    assert kmp_search(text, pattern).comparisons <= 2 * len(text)


def test_boyer_moore_skips_characters_on_natural_text(corpus):
    text = fold_case(corpus.get(1).abstract)
    bm = boyer_moore_search(text, "literacy")
    kmp = kmp_search(text, "literacy")
    assert bm.positions == kmp.positions
    assert bm.comparisons < len(text) < kmp.comparisons + 1


def test_empty_pattern_is_rejected():
    for search in (kmp_search, boyer_moore_search, rabin_karp_search, naive_search):
        with pytest.raises(ValueError):
            search("abc", "")


# ------------------------------------------------------------------ trazas


@pytest.mark.parametrize("algorithm", ["kmp", "boyer_moore", "rabin_karp", "naive"])
def test_trace_events_are_consistent(algorithm):
    text = "Generative AI transforms assessment; generative models generate text."
    d = trace_search("generat", text, algorithm, modulus=101)
    found = [e["position"] for e in d["trace"] if e["type"] == "found"]
    assert found == d["positions"] == _brute(fold_case(text), "generat")
    compares = [e for e in d["trace"] if e["type"] == "compare"]
    if algorithm != "rabin_karp":
        assert len(compares) == d["comparisons"]
        for e in compares:
            assert (d["text"][e["i"]] == "generat"[e["j"]]) == e["match"]
    else:
        windows = [e for e in d["trace"] if e["type"] == "window"]
        assert len(windows) == len(text) - len("generat") + 1


def test_trace_is_truncated_when_limit_reached():
    r = naive_search("a" * 500, "aaab", trace=True, max_trace=50)
    assert r.trace_truncated and len(r.trace) == 50


# ---------------------------------------------------------- servicio corpus


def test_search_corpus_is_consistent_and_case_insensitive(corpus):
    res = search_corpus("Generative", fields=["abstract", "title"], corpus=corpus)
    assert res["consistent"]
    total = 0
    for a in corpus:
        for text in (a.abstract, a.title):
            total += len(_brute(text.lower(), "generative"))
    assert res["total_occurrences"] == total
    for alg, t in res["totals"].items():
        assert t["occurrences"] == total, alg


def test_search_corpus_cross_reference_authors(corpus):
    res = search_corpus("Melissa Bond", fields=["authors"], case_sensitive=True, corpus=corpus)
    assert sorted(r["code"] for r in res["results"]) == ["A12", "A20"]


def test_search_corpus_validation(corpus):
    with pytest.raises(ValueError):
        search_corpus("   ", corpus=corpus)
    with pytest.raises(ValueError):
        search_corpus("ai", fields=["body"], corpus=corpus)
