import logging
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from pydantic import BaseModel

from chathelper.cache import load_paper
from chathelper.config import ChatDocument


def _load_vector_store(
    vector_store_path: Path,
    cache_dir: Path,
    api_key: str,
    docs: Iterable,
) -> Chroma:
    """Loads the vector store from a list of cached documents.

    Note: This has as little non-langchain logic in it
    as possible - and is not tested by unit tests atm.

    Args:
        vector_store_path (Path): The folder where the vector store can be put.
        api_key (str): The OpenAI key to use for the embeddings.
        cache_dir (Path): The path to the cache directory.
        docs (Iterable[ChatDocument]): List of documents to load into db

    Returns:
        Chroma: The vector store
    """

    # Open the DB from the path

    embedding = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        openai_api_key=api_key,
    )  # type: ignore
    vector_store = Chroma(
        embedding_function=embedding, persist_directory=str(vector_store_path)
    )
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)

    # Loop over the documents, sending them through the splitter
    # and then through the embedding, finally storing them in the
    # vector store.
    count = 0
    for doc_info in docs:
        splits = text_splitter.split_documents([doc_info])
        vector_store.add_documents(splits)

        count += 1

    # Make sure all data is on disk
    vector_store.persist()
    return vector_store


class VectorStoreFiles(BaseModel):
    """Files used to store the vector store"""

    # The references already included in the store
    refs: List[str]


def load_vector_store_files(vector_store_path: Path) -> VectorStoreFiles:
    """Load vector store filelist from the vector store path"""
    p = vector_store_path / "files.json"
    if not p.exists():
        return VectorStoreFiles(refs=[])
    with open(p, "r") as f:
        return VectorStoreFiles.parse_raw(f.read())


def _save_store(vector_store_path: Path, files: VectorStoreFiles):
    """Save vector store filelist"""
    p = vector_store_path / "files.json"
    vector_store_path.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        f.write(files.json())


def load_vector_store(
    vector_store_path: Path,
    cache_dir: Path,
    api_key: str,
    docs: Iterable[ChatDocument],
    progress_cb: Optional[Callable[[int], None]] = None,
):
    def my_cb(count: int):
        if progress_cb is not None:
            progress_cb(count)

    files = load_vector_store_files(vector_store_path)

    def good_documents():
        count = 0
        for d in docs:
            doc_info = load_paper(d, cache_dir)
            if doc_info is None:
                logging.info(f"Skipping {d} - not cached")
                continue
            if d.ref in files.refs:
                logging.info(f"Skipping {d} - already in vector store")
                continue
            logging.info(f"Adding {d} to vector store")
            yield doc_info
            files.refs.append(d.ref)
            _save_store(vector_store_path, files)
            count += 1
            my_cb(count)

    _load_vector_store(vector_store_path, cache_dir, api_key, good_documents())
