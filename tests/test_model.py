import pickle
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch

import pytest

from chathelper.cache import _paper_path
from chathelper.config import ChatDocument
from chathelper.model import populate_vector_store


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
        pickle.dump(["this is the paper contents"], f)

    return (cache_dir, [paper])


@patch("chathelper.model._load_vector_store")
def test_load_vector_store(mock_load, tmp_path, cache_with_files):
    "Load a paper into the vector store"

    cache_dir, papers = cache_with_files
    vector_store = tmp_path / "vector_store"

    populate_vector_store(vector_store, cache_dir, "api_key", papers)

    mock_load.assert_called_once()
    assert len(list(mock_load.call_args[0][3])) == 1


@patch("chathelper.model._load_vector_store")
def test_load_vector_store_nocache(mock_load, tmp_path):
    "Paper isn't in the cache"

    cache_dir = tmp_path / "cache"
    vector_store = tmp_path / "vector_store"

    papers = [ChatDocument(ref="arxiv://2109.10905", tags=[])]

    populate_vector_store(vector_store, cache_dir, "api_key", papers)

    mock_load.assert_called_once()
    assert len(list(mock_load.call_args[0][3])) == 0


@patch("chathelper.model._load_vector_store")
def test_load_vector_store_repeat(mock_load, tmp_path, cache_with_files):
    "Don't reload papers that are already in cache"

    cache_dir, papers = cache_with_files
    vector_store = tmp_path / "vector_store"

    populate_vector_store(vector_store, cache_dir, "api_key1", papers)
    list(mock_load.call_args[0][3])
    populate_vector_store(vector_store, cache_dir, "api_key2", papers)

    assert mock_load.call_count == 2
    assert len(list(mock_load.call_args[0][3])) == 0
