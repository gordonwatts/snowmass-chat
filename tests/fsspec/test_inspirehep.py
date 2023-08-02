import fsspec
from chathelper.fsspec.inspirehep import InspireFileSystem


def test_copy(tmp_path):
    output_file = tmp_path / "2043503.pdf"
    fs = InspireFileSystem()
    fs.copy("inspirehep://2043503", output_file.as_uri())

    assert output_file.exists()


def test_find_protocol():
    fs = fsspec.filesystem("inspirehep")
    assert isinstance(fs, InspireFileSystem)
