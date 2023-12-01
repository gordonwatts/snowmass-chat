import argparse
from rake_nltk import Rake
from rich.table import Table
from rich.console import Console

from chathelper.lc_experimental.archive_loader import ArxivLoader


def main():
    parser = argparse.ArgumentParser(description="Extract keywords from a PDF file.")
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Archive search string",
        default="id:2109.10905",
        nargs="?",
    )
    args = parser.parse_args()

    # Use the 'pdf_path' argument in your code
    pdf_path = args.pdf_path
    print(pdf_path)

    # Extract the complete text from the PDF file.
    loader = ArxivLoader(
        pdf_path,
        load_all_available_meta=True,
        doc_content_chars_max=None,
        keep_pdf=True,
    )
    data = loader.load()

    print(len(data))
    assert len(data) == 1

    good_doc = data[0]
    # print(good_doc.page_content)

    # Use rake to get the list of keywords.

    # Uses stop-words for english from NLTK, and all punctuation characters by
    # default
    r = Rake(max_length=3)

    # Extraction given the text.
    r.extract_keywords_from_text(good_doc.page_content)

    # To get keyword phrases ranked highest to lowest with scores.
    results = r.get_ranked_phrases_with_scores()

    # Create a rich table with the header and the two columns
    table = Table(title="Keyword Rankings")
    table.add_column("Index", justify="right", style="green")
    table.add_column("Rank Score", justify="right", style="cyan")
    table.add_column("Keyword", style="magenta")

    seen = set()
    for index, (score, keyword) in enumerate(results):
        if keyword not in seen and len(seen) < 500:
            table.add_row(str(index), str(score), keyword)
            seen.add(keyword)

    # Print the table
    console = Console()
    console.print(table)


if __name__ == "__main__":
    main()
