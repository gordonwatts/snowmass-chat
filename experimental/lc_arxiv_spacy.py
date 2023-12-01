# Try to download and "cache" the data loaded from a document on the archive

# from langchain.document_loaders import ArxivLoader
from pathlib import Path
import pickle

from chathelper.lc_experimental.archive_loader import ArxivLoader


def sanitize(n: str) -> str:
    return n.replace(":", "_").replace(".", "_")


document_name = "id:2109.10905"

downloaded = Path(f"./{sanitize(document_name)}.pkl")
if not downloaded.exists():
    loader = ArxivLoader(
        document_name,
        load_all_available_meta=True,
        doc_content_chars_max=None,
        keep_pdf=True,
    )
    data = loader.load()

    print(len(data))
    assert len(data) == 1

    good_doc = data[0]

    with downloaded.open("wb") as f:
        pickle.dump(good_doc, f)
else:
    with downloaded.open("rb") as f:
        good_doc = pickle.load(f)

# And now read it back in to test that pickle round trip worked.
print(f"content len: {len(good_doc.page_content)}")

# Now lets see how this noun thing works.
