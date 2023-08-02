import fsspec
from chathelper.fsspec.inspirehep import InspireFileSystem


def test_copy(tmp_path):
    output_file = tmp_path / "2043503.pdf"
    fs = InspireFileSystem()
    fs.get("inspirehep://2043503", str(output_file))

    assert output_file.exists()


def test_find_protocol():
    fs = fsspec.filesystem("inspirehep")
    assert isinstance(fs, InspireFileSystem)
