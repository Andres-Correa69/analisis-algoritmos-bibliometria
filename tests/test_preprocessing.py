"""Pruebas del preprocesamiento: normalización, tokenización y stemmer de Porter."""

import pytest
from nltk.stem.porter import PorterStemmer as NltkPorter

from bibliometria.preprocessing import PorterStemmer, Preprocessor, normalize_text, split_sentences, tokenize
from bibliometria.preprocessing.stopwords import ENGLISH_STOPWORDS


def test_normalize_text_replaces_ligatures_and_collapses_spaces():
    assert normalize_text("  artiﬁcial   intel­ligence  is  ") == "artificial intelligence is"


def test_tokenize_splits_on_non_alphanumeric():
    assert tokenize("AI-driven tools (2023), ChatGPT's impact!") == ["ai", "driven", "tools", "2023", "chatgpt", "s", "impact"]


def test_tokenize_keeps_accents_and_case_option():
    assert tokenize("Educación Marín", lowercase=False) == ["Educación", "Marín"]


def test_split_sentences_respects_abbreviations():
    text = "AI is used, e.g. in tutoring. Results vary. Done?"
    assert split_sentences(text) == ["AI is used, e.g. in tutoring.", "Results vary.", "Done?"]


def test_stopword_list_is_the_standard_179_words():
    assert len(ENGLISH_STOPWORDS) == 179


@pytest.mark.parametrize(
    "word,stem",
    [
        ("caresses", "caress"),
        ("ponies", "poni"),
        ("relational", "relat"),
        ("conditional", "condit"),
        ("generalizations", "gener"),
        ("oscillators", "oscil"),
        ("education", "educ"),
        ("learning", "learn"),
        ("hopping", "hop"),
        ("agreed", "agre"),
        ("happy", "happi"),
    ],
)
def test_porter_known_examples(word, stem):
    assert PorterStemmer().stem(word) == stem


def test_porter_matches_nltk_original_algorithm_on_corpus_vocabulary(corpus):
    """Oráculo: el stemmer propio debe coincidir con NLTK (modo ORIGINAL_ALGORITHM)."""
    ours, ref = PorterStemmer(), NltkPorter(mode=NltkPorter.ORIGINAL_ALGORITHM)
    vocab = set()
    for a in corpus:
        for t in tokenize(a.abstract + " " + a.title):
            if t.isalpha() and t.isascii():
                vocab.add(t)
    assert len(vocab) > 900
    mismatches = [w for w in vocab if ours.stem(w) != ref.stem(w)]
    assert mismatches == []


def test_preprocessor_pipeline_counts():
    p = Preprocessor().process("The students are learning with AI tools in 2023.")
    assert p.tokens == ["the", "students", "are", "learning", "with", "ai", "tools", "in", "2023"]
    assert p.filtered == ["students", "learning", "ai", "tools"]
    assert p.stems == ["student", "learn", "ai", "tool"]
    assert p.stem_to_word["learn"] == "learning"
