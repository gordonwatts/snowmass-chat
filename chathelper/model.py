import logging
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
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
    # Get the vector store and splitter
    vector_store = load_vector_store_database(vector_store_path, api_key)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)

    # Loop over the documents, sending them through the splitter
    # and then through the embedding, finally storing them in the
    # vector store.
    count = 0
    for doc_info in docs:
        # ChromaDB cannot deal with complex metadata, so flatten lists
        for k, v in doc_info.metadata.items():
            if isinstance(v, list):
                doc_info.metadata[k] = ", ".join(v)

        # Split and then store
        splits = text_splitter.split_documents([doc_info])
        vector_store.add_documents(splits)

        count += 1

    # Make sure all data is on disk
    vector_store.persist()
    return vector_store


def load_vector_store_database(vector_store_path, api_key) -> Chroma:
    """Open the Vector store and create the embedding function

    Args:
        vector_store_path (Path): The location of the vector store
        api_key (str): The OpenAPI api key

    Returns:
        Tuple[Chroma, OpenAIEmbeddings]: The vector store and the embedding function
    """
    embedding = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        openai_api_key=api_key,
    )  # type: ignore
    vector_store = Chroma(
        embedding_function=embedding, persist_directory=str(vector_store_path)
    )

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


def populate_vector_store(
    vector_store_path: Path,
    cache_dir: Path,
    api_key: str,
    docs: Iterable[ChatDocument],
    progress_cb: Optional[Callable[[int], None]] = None,
):
    """
    Populates a vector store with the embeddings of the given documents.

    Args:
        vector_store_path (Path): The path to the directory where the vector store will
            be saved.
        cache_dir (Path): The path to the directory where the cached documents are
            stored.
        api_key (str): The OpenAI API key.
        docs (Iterable[ChatDocument]): The documents to be added to the vector store.
        progress_cb (Optional[Callable[[int], None]], optional): A callback function
            that will be called with the number of documents processed so far.
            Defaults to None.
    """

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


def find_similar_text_chucks(
    vector_store_path: Path,
    api_key: str,
    query: str,
):
    """Return documents from store that might answer the question"""
    # Vector store db and embedding function
    vector_store = load_vector_store_database(vector_store_path, api_key)
    return vector_store.similarity_search(query)  # type: ignore


def query_llm(
    vector_store_path: Path,
    api_key: str,
    query: str,
):
    # Vector store db and embedding function
    vector_store = load_vector_store_database(vector_store_path, api_key)
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=api_key)
    qa_chain = RetrievalQA.from_chain_type(llm, retriever=vector_store.as_retriever())

    return qa_chain({"query": query})
