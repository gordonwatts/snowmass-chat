from pathlib import Path
import pickle
from unittest.mock import patch

import pytest
from langchain.document_loaders import UnstructuredPDFLoader

from chathelper.cache import (
    _paper_path,
    download_all,
    download_paper,
    find_paper,
    load_paper,
)
from chathelper.config import ChatDocument
from chathelper.lc_experimental.archive_loader import ArxivLoader


class _dummy_document:
    def __init__(self):
        self.page_content = "holy cow"
        self.metadata = {"chatter_tags": ["EF"]}


def test_paper_path(tmp_path):
    "Different papers use different ways of turning into a path"

    # Inspire.hep
    assert (
        _paper_path(ChatDocument(ref="inspirehep://12345", tags=[]), tmp_path)
        == tmp_path / "12345.pickle"
    )

    # Archive
    assert (
        _paper_path(ChatDocument(ref="arxiv://2203.01009", tags=[]), tmp_path)
        == tmp_path / "2203.01009.pickle"
    )

    # URL https://arxiv.org/pdf/2203.01009 (no meta data in the ned, but...)
    assert (
        _paper_path(
            ChatDocument(ref="https://arxiv.org/pdf/2203.01009", tags=[]), tmp_path
        )
        == tmp_path / "2203.01009.pickle"
    )

    # URL https://www.slac.stanford.edu/econf/C210711/reports/ExecutiveSummary.pdf
    assert (
        _paper_path(
            ChatDocument(
                ref="https://www.slac.stanford.edu/econf/C210711/reports/"
                "ExecutiveSummary.pdf",
                tags=[],
            ),
            tmp_path,
        )
        == tmp_path / "ExecutiveSummary.pickle"
    )

    # Local path
    assert (
        _paper_path(ChatDocument(ref="file:///tmp/2203.01009.pdf", tags=[]), tmp_path)
        == tmp_path / "2203.01009.pdf.pickle"
    )


def test_paper_path_bad(tmp_path):
    """Not supported yet"""

    with pytest.raises(NotImplementedError):
        _paper_path(
            ChatDocument(
                ref="https://indico.cern.ch/event/1242538/contributions/"
                "5432836/attachments/2689673/4669514/"
                "2023%20-%20MODE%20-%20NN%20and%20Cuts",
                tags=[],
            ),
            tmp_path,
        )

    with pytest.raises(ValueError):
        _paper_path(ChatDocument(ref="arxiv:2022.2109", tags=[]), tmp_path)


def test_find(tmp_path):
    "Look for an existing paper in the cache"
    paper_name = "01234"
    paper_file = tmp_path / f"{paper_name}.pickle"
    paper_file.touch()

    paper1 = ChatDocument(ref=f"inspirehep://{paper_name}", tags=[])
    assert find_paper(paper1, tmp_path) == paper_file

    paper2 = ChatDocument(ref="inspirehep://fork", tags=[])
    assert find_paper(paper2, tmp_path) is None


@patch.object(ArxivLoader, "load", return_value=[_dummy_document()])
def test_download_archive_loaded(mock_load, tmp_path):
    "Download a paper to the cache"
    paper_name = "2109.10905"

    cache_dir = tmp_path / "cache"
    # expected_paper = cache_dir / f"{paper_name}.pickle"

    paper = ChatDocument(ref=f"arxiv://{paper_name}", tags=[])
    assert download_paper(paper, cache_dir)

    downloaded = find_paper(paper, cache_dir)
    assert downloaded is not None
    assert downloaded.exists()

    mock_load.assert_called_once_with()


@patch.object(ArxivLoader, "__init__", return_value=None)
@patch.object(ArxivLoader, "load", return_value=[_dummy_document()])
def test_download_arxiv(mock_load, mock_init, tmp_path):
    "Make sure the Archive loader is called correctly"
    paper_name = "2109.10905"

    cache_dir = tmp_path / "cache"
    # expected_paper = cache_dir / f"{paper_name}.pickle"

    paper = ChatDocument(ref=f"arxiv://{paper_name}", tags=[])
    download_paper(paper, cache_dir)

    assert mock_init.called_once_with(
        "id:2109.10905",
        load_all_available_meta=True,
        doc_content_chars_max=None,
    )


@patch.object(UnstructuredPDFLoader, "__init__", return_value=None)
@patch.object(UnstructuredPDFLoader, "load", return_value=[_dummy_document()])
def test_download_pdf_From_url(mock_load, mock_init, tmp_path):
    "Download a pdf from a url"
    paper_name = (
        "https://www.slac.stanford.edu/econf/C210711/reports/ExecutiveSummary.pdf"
    )

    cache_dir = tmp_path

    paper = ChatDocument(ref=f"{paper_name}", tags=[])
    download_paper(paper, cache_dir)

    downloaded = find_paper(paper, cache_dir)
    assert downloaded is not None
    assert downloaded.exists()

    mock_load.assert_called_once()

    arg = mock_init.call_args[0][0]
    assert Path(arg).name == "ExecutiveSummary.pdf"


@patch.object(ArxivLoader, "load", side_effect=ValueError("should not be called"))
def test_download_cached(mock_load, tmp_path):
    "Do not re-download a paper"
    paper_name = "2109.10905"

    cache_dir = tmp_path / "cache"
    # expected_paper = cache_dir / f"{paper_name}.pickle"

    paper = ChatDocument(ref=f"arxiv://{paper_name}", tags=[])
    expected_paper_path = _paper_path(paper, cache_dir)
    expected_paper_path.parent.mkdir(exist_ok=True, parents=True)
    expected_paper_path.touch()

    # This download should do nothing
    assert not download_paper(paper, cache_dir)
    mock_load.assert_not_called()


def test_load_cached(tmp_path):
    cache_dir = tmp_path / "cache"
    paper = ChatDocument(ref="arxiv://2109.10905", tags=[])

    expected_paper_path = _paper_path(paper, cache_dir)
    expected_paper_path.parent.mkdir(exist_ok=True, parents=True)
    with expected_paper_path.open("wb") as f:
        pickle.dump(_dummy_document(), f)

    assert isinstance(load_paper(paper, cache_dir), _dummy_document)


def test_load_cached_new_metadata(tmp_path):
    cache_dir = tmp_path / "cache"
    paper = ChatDocument(ref="arxiv://2109.10905", tags=["WF"], title="fork")

    expected_paper_path = _paper_path(paper, cache_dir)
    expected_paper_path.parent.mkdir(exist_ok=True, parents=True)
    with expected_paper_path.open("wb") as f:
        pickle.dump(_dummy_document(), f)

    p = load_paper(paper, cache_dir)
    assert p is not None
    assert p.metadata["chatter_tags"] == ["WF"]
    assert p.metadata["Title"] == "fork"


def test_download_all(tmp_path):
    "Download list of papers to the cache"
    cache_dir = tmp_path / "cache"

    paper = ChatDocument(ref="arxiv://2109.10905", tags=[])

    with patch("chathelper.cache.download_paper") as mock_download:
        download_all([paper], cache_dir)
        mock_download.assert_called_once_with(paper, cache_dir)


def test_download_all_callback(tmp_path):
    cache_dir = tmp_path / "cache"

    paper = ChatDocument(ref="arxiv://2109.10905", tags=[])

    calls = []

    def callback(downloaded):
        calls.append(downloaded)

    with patch("chathelper.cache.download_paper") as mock_download:
        download_all([paper], cache_dir, callback)
        mock_download.assert_called_once_with(paper, cache_dir)

    assert len(calls) == 1
    assert calls == [1]
