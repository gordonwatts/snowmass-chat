from typing import Any, Dict
from urllib.parse import urlparse
from fsspec import AbstractFileSystem
import fsspec
from pydantic_core import Url
import requests
import functools


class InspireFileSystem(AbstractFileSystem):
    @functools.lru_cache(maxsize=None)
    def _get_meta(self, path: str) -> Dict[str, Any]:
        """Return the metadata for the given path. Cached.

        Note: Inspire API is rate limited.
        Docs: https://github.com/inspirehep/rest-api-doc

        Args:
            path (str): The path from `fsspec`
        """
        # Extract the inspire id from the path
        uri = urlparse(path)
        paper_id = uri.netloc

        # Request the metadata info
        meta_url = f"https://inspirehep.net/api/literature/{paper_id}?format=json"
        return requests.get(meta_url).json()

    def _get_paper_url(self, path: str) -> Url:
        """Get the URL of the paper from the metadata

        Args:
            path (str): The path from `fsspec`

        Returns:
            Url: The URL of the paper
        """
        meta = self._get_meta(path)
        return Url(meta["metadata"]["documents"][0]["url"])

    def ls(self, path, detail=True, **kwargs):
        """Get metadata info for the given path. Cached.

        Args:
            path (str): Path to the file
            detail (bool, optional): How many details. Defaults to True.

        Returns:
            Dict[]: Keys needed for fsspec
        """
        meta = self._get_meta(path)
        meta["name"] = path
        meta["size"] = None
        meta["type"] = "file"
        return [meta]

    def open(
        self,
        path,
        mode="rb",
        block_size=None,
        cache_options=None,
        compression=None,
        **kwargs,
    ):
        if mode != "rb":
            raise NotImplementedError("Only read-byte mode is supported ('rb')")

        # Grab the URL of the document and open it with fsspec's http backend.
        doc_url = self._get_paper_url(path)
        source_fs = fsspec.filesystem(doc_url.scheme)
        return source_fs.open(
            str(doc_url), mode, block_size, cache_options, compression
        )
