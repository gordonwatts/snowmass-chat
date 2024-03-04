import pickle
from pathlib import Path
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse
import requests


from langchain.schema.document import Document
from langchain_community.document_loaders import UnstructuredPDFLoader

from chathelper.utils import throttle

from .config import ChatDocument
from .lc_experimental.archive_loader import ArxivLoader


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
        filename = r.path.split("/")[-1]
        if not filename.endswith(".pdf"):
            raise NotImplementedError(
                f"Invalid URL {paper.ref} (must end with '.pdf'?)"
            )
        return cache_dir / f"{Path(filename).stem}.pickle"

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


def update_metadata(doc: Document, paper: ChatDocument):
    """Update the metadata of a document"""
    doc.metadata["chatter_tags"] = paper.tags
    doc.metadata["chatter_ref"] = paper.ref
    if paper.title is not None:
        doc.metadata["Title"] = paper.title


@throttle(10)
def do_download(paper: ChatDocument, cache_dir: Path, paper_path: Path):
    # Now parse and figure out how to get the thing
    uri = urlparse(paper.ref)
    if uri.scheme == "arxiv":
        query = f"id:{uri.netloc}"
        loader = ArxivLoader(
            query,
            load_all_available_meta=True,
            doc_content_chars_max=None,
            keep_pdf=True,
        )
        data = loader.load()
    elif uri.scheme == "http" or uri.scheme == "https":
        # Download the PDF locally from the uri using the `requests` library.
        # This is a bit of a hack, but it works.
        r = requests.get(paper.ref)
        pdf_path = (Path(".") / f"{paper_path.stem}.pdf").absolute()
        if not pdf_path.exists():
            with pdf_path.open("wb") as f:
                f.write(r.content)
        loader = UnstructuredPDFLoader(str(pdf_path))
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
    update_metadata(data[0], paper)

    # Finally, save it!
    with open(paper_path, "wb") as f:
        pickle.dump(data[0], f)


def download_paper(paper: ChatDocument, cache_dir: Path) -> bool:
    """Download a paper to the local cache directory.

    Use the langchain loaders - and the uri scheme to set which one.
    As far as I know langchain can't determine which is which, so each
    scheme has to be hardcoded.

    Args:
        paper (ChatDocument): Paper to download
        cache_dir (Path): Location of the cache directory

    Returns:
        bool: True if the paper was downloaded, False if it was already in the cache.
        Exception is thrown if the download attempt is made and fails.
    """
    # Get the final path - this will also do some sanity checking
    # on the url(s).
    # Return if the paper is already there.
    paper_path = _paper_path(paper, cache_dir)
    if paper_path.exists():
        return False

    do_download(paper, cache_dir, paper_path)
    return True


def load_paper(paper: ChatDocument, cache_dir: Path) -> Optional[Document]:
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
        r = pickle.load(f)
        update_metadata(r, paper)
        return r


def download_all(
    papers: Iterable[ChatDocument],
    cache_dir: Path,
    progress_callback: Optional[Callable[[int], None]] = None,
    max_downloads: Optional[int] = None,
) -> None:
    """Download all papers to the local cache directory

    Args:
        papers (List[ChatDocument]): List of papers to download
        cache_dir (Path): Location of the cache directory
        max_downloads (Optional[int], optional): Maximum number of papers to download.
            Defaults to None. If None, everything is downloaded. Otherwise maximum
            number of downloads. Already cached papers do not count.
    """
    counter = 0
    downloaded = 0

    def my_cb(count: int):
        if progress_callback is not None:
            progress_callback(count)

    for paper in papers:
        if max_downloads is None or downloaded < max_downloads:
            if download_paper(paper, cache_dir):
                downloaded += 1
        counter += 1
        my_cb(counter)
