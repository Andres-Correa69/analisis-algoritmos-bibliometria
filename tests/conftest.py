"""Fixtures compartidas por las pruebas."""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=FutureWarning)

GROUND_TRUTH = ROOT / "tests" / "fixtures" / "ground_truth_metadata.json"


@pytest.fixture(scope="session")
def ground_truth() -> dict[int, dict]:
    with open(GROUND_TRUTH, encoding="utf-8") as fh:
        return {r["id"]: r for r in json.load(fh)}


@pytest.fixture(scope="session")
def corpus():
    from bibliometria.corpus import load_corpus

    return load_corpus()


@pytest.fixture(scope="session")
def engine():
    from bibliometria.similarity.service import get_engine

    return get_engine()


@pytest.fixture(scope="session")
def clustering_engine():
    from bibliometria.clustering.service import get_clustering_engine

    return get_clustering_engine()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from bibliometria.api.main import app

    return TestClient(app)
