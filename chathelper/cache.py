from pathlib import Path
from typing import Iterable, Optional

import fsspec
from .config import ChatDocument
from urllib.parse import urlparse


def _paper_path(paper: ChatDocument, cache_dir: Path) -> Path:
    """Get the path to a paper in the local cache directory

    Args:
        paper (ChatDocument): Paper to find
        cache_dir (Path): Location of the cache directory

    Returns:
        Path: Path to the paper in the cache directory
    """
    r = urlparse(paper.ref)

    if r.netloc == "arxiv.org":
        return cache_dir / f"{r.path.split('/')[-1]}.pdf"

    if r.scheme == "file":
        return cache_dir / f"{r.path.split('/')[-1]}"

    # TODO: Eventually remove this - but a little nervous
    # about fetching metadata, so lets let more of the code
    # be put in place first (Gordon). Also nervous about how
    # names get calculated - might want something that uses
    # all elements of a url (thinking about you, indico!).
    if r.scheme == "https" or r.scheme == "http":
        raise NotImplementedError(
            f"Arbitrary URL is not implemented as paper source {paper.ref}"
        )

    return cache_dir / f"{r.netloc}.pdf"


def find_paper(paper: ChatDocument, cache_dir: Path) -> Optional[Path]:
    """Find a paper in the local cache directory

    Args:
        paper (ChatDocument): Paper to find
        cache_dir (Path): Location of the cache directory

    Returns:
        Optional[Path]: Path to the paper in the cache directory. None
        if the paper isn't there.
    """
    p = _paper_path(paper, cache_dir)
    return p if p.exists() else None


def download_paper(paper: ChatDocument, cache_dir: Path) -> None:
    """Download a paper to the local cache directory.

    All sources that fsspec knows about can be
    copied from.

    Args:
        paper (ChatDocument): Paper to download
        cache_dir (Path): Location of the cache directory
    """
    uri = urlparse(paper.ref)
    fs = fsspec.filesystem(uri.scheme)

    if not cache_dir.exists():
        cache_dir.mkdir(parents=True)

    fs.copy(paper.ref, str(_paper_path(paper, cache_dir)))


def download_all(papers: Iterable[ChatDocument], cache_dir: Path) -> None:
    """Download all papers to the local cache directory

    Args:
        papers (List[ChatDocument]): List of papers to download
        cache_dir (Path): Location of the cache directory
    """
    for paper in papers:
        download_paper(paper, cache_dir)
