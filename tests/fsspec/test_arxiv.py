import fsspec
from chathelper.fsspec.arxiv import ArxivFileSystem
import pytest


@pytest.mark.skip("Network hit")
def test_copy(tmp_path):
    output_file = tmp_path / "2203.01009.pdf"
    fs = ArxivFileSystem()
    fs.get("arxiv://2203.01009", str(output_file))

    assert output_file.exists()


def test_find_protocol():
    fs = fsspec.filesystem("arxiv")
    assert isinstance(fs, ArxivFileSystem)
