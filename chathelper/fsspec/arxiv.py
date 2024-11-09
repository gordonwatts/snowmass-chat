from urllib.parse import urlparse
from fsspec import AbstractFileSystem
import fsspec
from httpcore import URL


class ArxivFileSystem(AbstractFileSystem):
    def _get_paper_url(self, path: str) -> URL:
        """Get the URL of the paper from the metadata

        Args:
            path (str): The path from `fsspec`

        Returns:
            Url: The URL of the paper
        """
        uri = urlparse(path)
        return URL(f"https://arxiv.org/pdf/{uri.netloc}.pdf")

    def ls(self, path, detail=True, **kwargs):
        """Get metadata info for the given path. Cached.

        Args:
            path (str): Path to the file
            detail (bool, optional): How many details. Defaults to True.

        Returns:
            Dict[]: Keys needed for fsspec
        """
        meta = {}
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
