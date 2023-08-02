from urllib.parse import urlparse
from fsspec import AbstractFileSystem
import fsspec
import requests


class InspireFileSystem(AbstractFileSystem):
    def ls(self, path, detail=True, **kwargs):
        return []
        # return super().ls(path, detail, **kwargs)

    def cp_file(self, path1, path2, **kwargs):
        # Extract the inspire id from the path
        uri = urlparse(path1)
        paper_id = uri.netloc

        # Request the metadata info
        meta_url = f"https://inspirehep.net/api/literature/{paper_id}?format=json"
        meta = requests.get(meta_url).json()

        # Grab the URL of the document out of there:
        doc_url = meta["metadata"]["documents"][0]["url"]

        # Now copy the data from there to the destination
        dest_uri = urlparse(path2)
        dest_fs = fsspec.filesystem(dest_uri.scheme)
        with dest_fs.open(path2, "wb") as f:
            f.write(requests.get(doc_url).content)
