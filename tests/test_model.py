import logging
import pickle
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch

from pydantic import SecretStr
import pytest

from chathelper.cache import _paper_path
from chathelper.config import ChatDocument
from chathelper.model import load_vector_store_database, populate_vector_store


class _dummy_document:
    def __init__(self):
        self.page_content = "holy cow"
        self.metadata = {"chatter_tags": ["EF"]}


@pytest.fixture()
def cache_with_files(tmp_path) -> Tuple[Path, List[ChatDocument]]:
    """Create a cache populated with files.

    Returns:
        (cache_dir, papers) - tuple with the cache dir
        and the papers that have been cached

    """
    cache_dir = tmp_path / "cache"
    paper = ChatDocument(ref="arxiv://2109.10905", tags=[])
    expected_paper_path = _paper_path(paper, cache_dir)
    expected_paper_path.parent.mkdir(exist_ok=True, parents=True)
    with expected_paper_path.open("wb") as f:
        pickle.dump(_dummy_document(), f)

    return (cache_dir, [paper])


@patch("chathelper.model._load_vector_store")
def test_load_vector_store(mock_load, tmp_path, cache_with_files):
    "Load a paper into the vector store"

    cache_dir, papers = cache_with_files
    vector_store = tmp_path / "vector_store"

    populate_vector_store(
        vector_store, cache_dir, SecretStr("api_key"), papers, (500, 0), "do-embed"
    )

    mock_load.assert_called_once()
    assert len(list(mock_load.call_args[0][2])) == 1


@patch("chathelper.model._load_vector_store")
def test_load_vector_store_nocache(mock_load, tmp_path):
    "Paper isn't in the cache"

    cache_dir = tmp_path / "cache"
    vector_store = tmp_path / "vector_store"

    papers = [ChatDocument(ref="arxiv://2109.10905", tags=[])]

    populate_vector_store(
        vector_store, cache_dir, SecretStr("api_key"), papers, (500, 0), "do-embed"
    )

    mock_load.assert_called_once()
    assert len(list(mock_load.call_args[0][2])) == 0


@patch("chathelper.model._load_vector_store")
def test_load_vector_store_repeat(mock_load, tmp_path, cache_with_files):
    "Don't reload papers that are already in cache"

    cache_dir, papers = cache_with_files
    vector_store = tmp_path / "vector_store"

    populate_vector_store(
        vector_store, cache_dir, SecretStr("api_key1"), papers, (500, 0), "do-embed"
    )
    list(mock_load.call_args[0][2])
    populate_vector_store(
        vector_store, cache_dir, SecretStr("api_key2"), papers, (500, 0), "do-embed"
    )

    assert mock_load.call_count == 2
    assert len(list(mock_load.call_args[0][2])) == 0


@patch("chathelper.model._load_vector_store")
def test_populate_vector_store_no_docs(mock_load, tmp_path, caplog):
    "Check warning is issued if zero documents are passed"

    cache_dir = tmp_path / "cache"
    vector_store = tmp_path / "vector_store"
    papers = []

    with caplog.at_level(logging.WARNING):
        populate_vector_store(
            vector_store, cache_dir, SecretStr("api_key"), papers, (500, 0), "do-embed"
        )

    docs = list(mock_load.call_args[0][2])
    assert len(docs) == 0
    assert "No documents to process" in caplog.text


def test_load_vector_store_database(tmp_path):
    "Test the database is saved and can be created"

    from pydantic import SecretStr

    db = load_vector_store_database(tmp_path, SecretStr("dude"), "fork-it")
    assert db is not None
