"""Pruebas del extractor de PDF contra la verdad de referencia verificada manualmente."""

import pytest

from bibliometria.config import RAW_PDF_DIR
from bibliometria.extraction.pdf_extractor import clean_text, extract_pdf, parse_author_names, sequence_dice


def _norm(s: str | None) -> str:
    return clean_text(s or "").replace("–", "-").replace("—", "-")


def _name(s: str) -> str:
    return "".join(c for c in clean_text(s).lower() if c.isalnum())


def _pdf(article_id: int):
    matches = sorted(RAW_PDF_DIR.glob(f"{article_id}. *.pdf"))
    assert matches, f"No se encontró el PDF {article_id}"
    return matches[0]


@pytest.fixture(scope="module")
def extracted():
    return {i: extract_pdf(_pdf(i)) for i in range(1, 21)}


@pytest.mark.parametrize("article_id", range(1, 21))
def test_title_authors_abstract_match_ground_truth(extracted, ground_truth, article_id):
    got, exp = extracted[article_id], ground_truth[article_id]
    assert _norm(got.title) == _norm(exp["title"])
    assert [_name(a) for a in got.authors] == [_name(a) for a in exp["authors"]]
    assert _norm(got.abstract) == _norm(exp["abstract"])


@pytest.mark.parametrize("article_id", range(1, 21))
def test_secondary_metadata_match_ground_truth(extracted, ground_truth, article_id):
    got, exp = extracted[article_id], ground_truth[article_id]
    assert got.year == exp["year"]
    assert (got.doi or "").lower() == (exp["doi"] or "").lower()
    assert got.journal == exp["journal"]
    assert [_name(k) for k in got.keywords] == [_name(k) for k in exp["keywords"]]


def test_no_extraction_warnings(extracted):
    assert {i: a.warnings for i, a in extracted.items() if a.warnings} == {}


def test_parse_author_names_handles_separators_and_markers():
    text = "Qi Xia1, Xiaojing Weng2 · Fan Ouyang3* | Tzung Jin Lin4 and Thomas K.F. Chiu1,5"
    assert parse_author_names(text) == ["Qi Xia", "Xiaojing Weng", "Fan Ouyang", "Tzung Jin Lin", "Thomas K.F. Chiu"]


def test_sequence_dice_is_one_for_same_tokens():
    assert sequence_dice("A Review: of AI?", "a review of ai") == 1.0
