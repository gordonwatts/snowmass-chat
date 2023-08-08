import argparse
import logging
import re
from typing import List
from urllib.parse import urlparse, urlunparse

import chardet
import yaml
from pydantic import BaseModel


def extract_urls(markdown_text):
    # Define a regular expression to match URLs
    url_regex = r"(?P<url>https?://[^\s\"]+)"

    # Find all matches of the URL regex in the markdown text
    matches = re.finditer(url_regex, markdown_text)

    # Extract the URLs from the matches
    urls = [match.group("url") for match in matches]

    return urls


def sanitize_arxiv(paper_number: str):
    p = paper_number.lower().replace("arxiv:", "")
    p = p.replace("|", "")
    return p


class ChatterDoc(BaseModel):
    ref: str
    tags: List[str]


class ChatterDocs(BaseModel):
    papers: List[ChatterDoc]


def main():
    # Create an argparse that takes a single argument, the input filename.
    parser = argparse.ArgumentParser(
        description="Converts links found in a markdown file to a list of URLs for our "
        "chatter."
    )
    parser.add_argument("input_filename", help="The input filename.")

    # The 'tag' argument which can be used multiple times to add tags to the output.
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help="Tags to add to the output. Can be used multiple times.",
    )

    args = parser.parse_args()

    # Open the input file and read the contents.
    with open(args.input_filename, "rb") as f:
        contents = f.read()

    encoding = chardet.detect(contents)["encoding"]
    assert isinstance(encoding, str)
    contents = contents.decode(encoding)

    # Extract all URLs from the text
    urls = extract_urls(contents)

    # Fix up the URLs as the parser sometimes gets them wrong.
    urls = [urlparse(u) for u in urls]

    # Now, extract all the archive ones, as they are the only ones we know how to use.
    def url_test(u):
        if u.netloc == "arxiv.org":
            return True
        if u.scheme == "http" or u.scheme == "https":
            if u.path.endswith("pdf"):
                return True
        return False

    bad_urls = [u for u in urls if not url_test(u)]
    good_urls = [u for u in urls if url_test(u)]

    for bad in bad_urls:
        logging.warning(f"Url that we can't currently process: {urlunparse(bad)}")

    # For the good URL's, collect the archive paper numbers and make sure each is
    # unique by putting them in a set.
    paper_numbers = set()
    for good in good_urls:
        if good.netloc == "arxiv.org":
            paper_numbers.add("arxiv://" + sanitize_arxiv(good.path.split("/")[-1]))
        else:
            paper_numbers.add(good.geturl())

    # Now place them into a dataclass that looks a lot like the one we use for the
    # chatter documents.
    tags = args.tags or []
    paper_list = [ChatterDoc(ref=p, tags=tags) for p in paper_numbers]
    paper_docs = ChatterDocs(papers=paper_list)
    print(yaml.dump(paper_docs.dict(), None))
