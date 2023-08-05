# Try to download and "cache" the data loaded from a document on the archive

# from langchain.document_loaders import ArxivLoader
from .archive_loader import ArxivLoader

document_name = "id:2109.10905"

loader = ArxivLoader(
    document_name, load_all_available_meta=True, doc_content_chars_max=None
)
data = loader.load()

print(len(data))
assert len(data) == 1

good_doc = data[0]

# Next, pickle the good_doc
# json or similar isn't used here b.c. it doesn't support the Document class
# That said, the Document is pydantic 1.0, so it could be there is a better way, I just do
# not know it.
import pickle

with open("good_doc.pickle", "wb") as f:
    pickle.dump(good_doc, f)

# And now read it back in to test that pickle round trip worked.
with open("good_doc.pickle", "rb") as f:
    good_doc_prime = pickle.load(f)
print(len(good_doc_prime.page_content), len(good_doc.page_content))

# Next, lets see if we can create the database with this character (e.g. make sure
# nothing that anyone cares about was lost during the pickling).
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)
all_splits = text_splitter.split_documents([good_doc_prime])
print(len(all_splits))

# Now, put it in the vector store
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

# Need api for this next line.
# vectorstore = Chroma.from_documents(documents=all_splits, embedding=OpenAIEmbeddings())
