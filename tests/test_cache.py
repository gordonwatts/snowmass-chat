import pytest
from chathelper.cache import download_all, download_paper, find_paper, _paper_path
from chathelper.config import ChatDocument
from unittest.mock import patch


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
                "2023%20-%20MODE%20-%20NN%20and%20Cuts.pdf",
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


def test_download_archive(tmp_path):
    "Download a paper to the cache"
    paper_name = "2109.10905"

    cache_dir = tmp_path / "cache"
    # expected_paper = cache_dir / f"{paper_name}.pickle"

    paper = ChatDocument(ref=f"arxiv://{paper_name}", tags=[])
    download_paper(paper, cache_dir)

    downloaded = find_paper(paper, cache_dir)
    assert downloaded is not None
    assert downloaded.exists()


def test_download_all(tmp_path):
    "Download list of papers to the cache"
    cache_dir = tmp_path / "cache"

    paper = ChatDocument(ref="arxiv://2109.10905", tags=[])

    with patch("chathelper.cache.download_paper") as mock_download:
        download_all([paper], cache_dir)
        mock_download.assert_called_once_with(paper, cache_dir)
