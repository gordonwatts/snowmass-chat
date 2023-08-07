from pathlib import Path
import pickle
from typing import Callable, Iterable, Optional

from chathelper.utils import throttle
from .config import ChatDocument
from .lc_experimental.archive_loader import ArxivLoader
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
        return cache_dir / f"{r.path.split('/')[-1]}.pickle"

    if r.scheme == "file":
        return cache_dir / f"{r.path.split('/')[-1]}.pickle"

    if r.scheme == "arxiv" and len(r.netloc) == 0:
        raise ValueError(f"Invalid arxiv id {paper.ref} (missing '//'?)")

    # TODO: Eventually remove this - but a little nervous
    # about fetching metadata, so lets let more of the code
    # be put in place first (Gordon). Also nervous about how
    # names get calculated - might want something that uses
    # all elements of a url (thinking about you, indico!).
    if r.scheme == "https" or r.scheme == "http":
        raise NotImplementedError(
            f"Arbitrary URL is not implemented as paper source {paper.ref}"
        )

    return cache_dir / f"{r.netloc}.pickle"


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


@throttle(10)
def do_download(paper, cache_dir, paper_path):
    # Now parse and figure out how to get the thing
    uri = urlparse(paper.ref)
    if uri.scheme == "arxiv":
        query = f"id:{uri.netloc}"
        loader = ArxivLoader(
            query, load_all_available_meta=True, doc_content_chars_max=None
        )
        data = loader.load()
    else:
        raise NotImplementedError(f"Unknown scheme {uri.scheme} for {paper.ref}")

    # Check what came back is good.
    if len(data) != 1:
        raise ValueError(f"Expected one paper, got {len(data)} for {paper.ref}")

    # Save the data using pickle
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True)

    # Add the metadata tags
    data[0].metadata["chatter_tags"] = paper.tags

    # Finally, save it!
    with open(paper_path, "wb") as f:
        pickle.dump(data[0], f)


def download_paper(paper: ChatDocument, cache_dir: Path) -> None:
    """Download a paper to the local cache directory.

    Use the langchain loaders - and the uri scheme to set which one.
    As far as I know langchain can't determine which is which, so each
    scheme has to be hardcoded.

    Args:
        paper (ChatDocument): Paper to download
        cache_dir (Path): Location of the cache directory
    """
    # Get the final path - this will also do some sanity checking
    # on the url(s).
    # Return if the paper is already there.
    paper_path = _paper_path(paper, cache_dir)
    if paper_path.exists():
        return

    do_download(paper, cache_dir, paper_path)


def load_paper(paper: ChatDocument, cache_dir: Path):
    """Load a paper from the local cache directory.

    Args:
        paper (ChatDocument): Paper to load
        cache_dir (Path): Location of the cache directory

    Returns:
        ChatDocument: Paper loaded from the cache directory
    """
    paper_path = _paper_path(paper, cache_dir)
    if not paper_path.exists():
        return None

    with open(paper_path, "rb") as f:
        return pickle.load(f)


def download_all(
    papers: Iterable[ChatDocument],
    cache_dir: Path,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> None:
    """Download all papers to the local cache directory

    Args:
        papers (List[ChatDocument]): List of papers to download
        cache_dir (Path): Location of the cache directory
    """
    counter = 0

    def my_cb(count: int):
        if progress_callback is not None:
            progress_callback(count)

    for paper in papers:
        download_paper(paper, cache_dir)
        counter += 1
        my_cb(counter)
