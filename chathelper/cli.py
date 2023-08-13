import argparse
from collections import defaultdict
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List

import yaml
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from chathelper.cache import download_all, find_paper, load_paper
from chathelper.config import ChatConfig, ChatDocument, load_chat_config
from chathelper.model import (
    find_similar_text_chucks,
    populate_vector_store,
    load_vector_store_files,
    query_llm,
)
from chathelper.questions import QandASequence, QuestionAndAnswer, load_questions


class config_cache:
    def __init__(self):
        self.config_file_cache = Path("./.chatter").absolute()

    def _load(self) -> Dict[str, Any]:
        """Load the yaml config file from the config_file_cache path"""
        try:
            with open(self.config_file_cache, "r") as f:
                data = yaml.safe_load(f)
                return data if data is not None else {}
        except FileNotFoundError:
            return {}

    def _update(self, values: Dict[str, Any]) -> None:
        """Update the config file with the values passed in"""
        data = self._load()
        with open(self.config_file_cache, "w") as f:
            data.update(values)
            yaml.safe_dump(data, f)

    @property
    def cache_dir(self) -> Path:
        """Return the cache directory"""
        return Path(self._load().get("cache_dir", Path("./chatter_cache").absolute()))

    @cache_dir.setter
    def cache_dir(self, value: Path) -> None:
        """Set the cache directory"""
        self._update({"cache_dir": str(value.absolute())})

    @property
    def vector_store_dir(self) -> Path:
        """Return the vector store directory"""
        return Path(
            self._load().get("vector_store_dir", Path("./vector_store").absolute())
        )

    @vector_store_dir.setter
    def vector_store_dir(self, value: Path) -> None:
        """Set the vector store directory"""
        self._update({"vector_store_dir": str(value.absolute())})

    @property
    def keys(self) -> Dict[str, str]:
        """Return the keys"""
        return self._load().get("keys", {})

    def add_key(self, key, value) -> None:
        """Add a key"""
        keys = self.keys
        keys[key] = value
        self._update({"keys": keys})


def load_config(args) -> ChatConfig:
    """Load the config file from the command line arguments

    Args:
        args (_type_): The command line arguments

    Raises:
        FileNotFoundError: Raised if the config file can't be located."""
    if args.config is None:
        raise ValueError(
            "No config file specified on the command line. "
            "Please use the --config option"
        )
    config_file = Path(args.config).absolute()
    if not config_file.exists():
        raise FileNotFoundError(f"Config file {config_file} does not exist")
    return load_chat_config(str(config_file))


def cache_set(args):
    """Set the cache directory"""
    cache_dir = Path(args.dir)
    config_cache().cache_dir = cache_dir
    logging.info(f"Cache directory set to {cache_dir}")


def cache_get(args):
    """Get the cache directory"""
    cache_dir = config_cache().cache_dir
    print(f"Cache directory is {cache_dir}")


def cache_download(args):
    """Download everything in the config file to the cache"""
    config = load_config(args)
    cache_dir = config_cache().cache_dir

    max_download: int | None = int(args.n) if args.n is not None else None

    progress = Progress()
    with progress:
        task1 = progress.add_task("Downloading", total=len(config.papers))
        download_all(
            config.papers,
            cache_dir,
            lambda _: progress.update(task1, advance=1),
            max_downloads=max_download,
        )


def cache_list(args):
    "List all the files in the cache"
    config = load_config(args)
    cache_dir = config_cache().cache_dir

    table = Table()
    table.add_column("Ref")
    table.add_column("Title")
    table.add_column("Size")
    table.add_column("Tags")

    count_cached = 0
    count_uncached = 0
    for paper in config.papers:
        title = ""
        size = "<not in cache>"
        doc_path = find_paper(paper, cache_dir)
        tags = ""
        if doc_path is not None:
            count_cached += 1
            doc = load_paper(paper, cache_dir)
            assert doc is not None
            title = doc.metadata["Title"]
            size = f"{len(doc.page_content) / 1024:.0f} kb"
            tags = ", ".join(doc.metadata["chatter_tags"])
        else:
            count_uncached += 1
        table.add_row(paper.ref, title, size, tags)

    console = Console()
    console.print(table)
    print(
        f"{count_cached} papers cached, {count_uncached} not cached, "
        f"for a total of {count_cached + count_uncached}"
    )


def cache_dump(args):
    """Dump the page contents of a locally cached item"""
    config = load_config(args)
    cache_dir = config_cache().cache_dir

    found = [c for c in config.papers if c.ref == args.ref]
    if len(found) == 0:
        print(f"Paper {args.ref} not found in config file")
        return

    doc = load_paper(found[0], cache_dir)
    if doc is None:
        print(f"Paper {args.ref} not found in cache")
        return
    print(doc.page_content)


def cache_clear(args):
    """Clear the cache"""
    cache_dir = config_cache().cache_dir
    if not args.force:
        if input(f"Are you sure you want to delete {cache_dir}? (y/N) ").lower() != "y":
            return

    logging.info(f"Deleting cache directory {cache_dir}")
    if cache_dir.exists():
        shutil.rmtree(cache_dir)


def keys_list(args):
    """List all keys"""
    keys = config_cache().keys
    if len(keys) == 0:
        print("No keys set")
        return

    table = Table()
    table.add_column("Key")
    table.add_column("Value")
    for key, value in keys.items():
        table.add_row(key, value)

    console = Console()
    console.print(table)


def keys_set(args):
    """Set a new key"""
    config_cache().add_key(args.key, args.value)


def vector_get(args):
    """display the current vector directory"""
    vector_dir = config_cache().vector_store_dir
    print(f"Vector directory is {vector_dir}")


def vector_set(args):
    """set the vector directory"""
    vector_dir = Path(args.dir)
    config_cache().vector_store_dir = vector_dir


def vector_store_path(args) -> Path:
    """Determine the path to the vector store from the configuration file name"""
    config = load_config(args)
    assert (
        config.short_name is not None and len(config.short_name) > 0
    ), "The 'shortname' key must be defined in the config file"
    return config_cache().vector_store_dir / config.short_name


def vector_clear(args):
    """clear the vector store"""
    vector_dir = vector_store_path(args)
    if not args.force:
        if (
            input(f"Are you sure you want to delete {vector_dir}? (y/N) ").lower()
            != "y"
        ):
            return
    logging.info(f"Deleting vector directory {vector_dir}")
    if vector_dir.exists():
        shutil.rmtree(vector_dir)


def vector_list(args):
    """List the references that are in the store"""
    vector_dir = vector_store_path(args)
    f_list = load_vector_store_files(vector_dir)
    if len(f_list.refs) == 0:
        print("No vectors in the vector store")
        return

    table = Table()
    table.add_column("Ref")
    for ref in f_list.refs:
        table.add_row(ref)

    console = Console()
    console.print(table)


def vector_populate(args):
    """Populate the store from cached papers"""
    vector_dir = vector_store_path(args)
    cache_dir = config_cache().cache_dir
    chat_config = load_config(args)
    openai_key = config_cache().keys.get("openai", None)
    if openai_key is None:
        print("No OpenAI API key set, use chatter set key openai <key>")
        return

    progress = Progress()
    with progress:
        task1 = progress.add_task("Populating", total=len(chat_config.papers))

        populate_vector_store(
            vector_dir,
            cache_dir,
            openai_key,
            chat_config.papers,
            lambda _: progress.update(task1, advance=1),
        )


def config_list(args):
    config = load_config(args)
    print(f"Config file: {config.short_name}")

    table = Table()
    table.add_column("Ref")
    table.add_column("Tags")

    for paper in config.papers:
        table.add_row(paper.ref, ", ".join(paper.tags))

    console = Console()
    console.print(table)
    print(f"There are {len(config.papers)} papers in this configuration")


def config_check(args):
    """Look for duplicate papers, etc"""
    config = load_config(args)

    all_papers: Dict[str, List[ChatDocument]] = defaultdict(list)
    for paper in config.papers:
        all_papers[paper.ref].append(paper)

    if not args.fix:
        table = Table()
        table.add_column("Ref")
        table.add_column("Tags")

        count = 0
        for ref in all_papers.keys():
            if len(all_papers[ref]) > 1:
                all_tags = set([t for p in all_papers[ref] for t in p.tags])
                table.add_row(ref, ", ".join(sorted(list(all_tags))))
                count += 1

        if count > 0:
            console = Console()
            console.print(table)
            print(f"Found {count} duplicate papers")
        print("Config file checks out!")
    else:
        new_config = ChatConfig(**config.dict())
        new_config.papers = []
        for ref in all_papers.keys():
            paper = all_papers[ref][0]
            paper.tags = sorted(list(set([t for p in all_papers[ref] for t in p.tags])))
            titles = set([p.title for p in all_papers[ref]])
            if len(titles) > 1:
                raise ValueError(f"Multiple titles for {ref}: {titles}")
            paper.title = titles.pop()
            new_config.papers.append(paper)

        new_config_path = (
            Path(args.config).parent / f"{Path(args.config).stem}_fixed.yaml"
        )
        with open(new_config_path, "w") as f:
            yaml.dump(new_config.dict(), f)
        print(
            f"New config file written to {new_config_path}. "
            "Any comments in the original were lost!"
        )


def query_find(args):
    """Find all similar text chunks to the query"""
    vector_dir = vector_store_path(args)
    openai_key = config_cache().keys.get("openai", None)
    if openai_key is None:
        print("No OpenAI API key set, use chatter set key openai <key>")
        return

    chunks = find_similar_text_chucks(
        vector_dir, openai_key, args.query, int(args.n or 4)
    )
    if len(chunks) == 0:
        print("No similar chunks found")
        return
    table = Table(show_lines=True)
    table.add_column("Title", width=30)
    table.add_column("Text")

    for c in chunks:
        table.add_row(c.metadata["Title"], c.page_content.replace("\n", " "))

    console = Console()
    console.print(table)


def ask_from_args(args, query: str) -> Dict[str, Any]:
    """Ask a query given the correct command line args

    Args:
        args (argparse.args): Arguments needed to ask the question

    Returns:
        str: Response from the model.
    """
    vector_dir = vector_store_path(args)
    openai_key = config_cache().keys.get("openai", None)
    if openai_key is None:
        raise ValueError("No OpenAI API key set, use chatter set key openai <key>")

    return query_llm(vector_dir, openai_key, query, int(args.n or 4))


def query_ask(args):
    """Find all similar text chunks to the query"""
    response = ask_from_args(args, args.query)
    print(response["result"])


def questions_list(args):
    """List the questions in the questions file"""
    questions = load_questions(args.questions_file)
    table = Table()
    table.add_column("Question")

    for q in questions.questions:
        table.add_row(q.question)

    console = Console()
    console.print(table)
    print(
        f"There are {len(questions.questions)} questions in {args.questions_file.name}"
    )


def questions_ask(args):
    """Ask a question from the questions file"""

    # Check args as much as we can early
    if args.output_file.exists():
        raise ValueError(
            f"Output path {args.output_file} already exists. "
            "Either delete or use --force"
        )

    # Build the description
    description = f"{args.description} (-n {args.n})"

    questions = load_questions(args.questions_file)

    response = [
        QuestionAndAnswer(
            question=q.question, answer=ask_from_args(args, q.question)["result"]
        )
        for q in questions.questions
    ]

    qanda = QandASequence(
        questions=response, title=questions.title, description=description
    )

    with open(args.output_file, "w") as f:
        yaml.dump(qanda.dict(), f)


def execute_command_line():
    """Parse command line arguments using the `argparse` module as a series of
    sub-commands.

    At the top level command:
        -c, --config <filename>     The yaml filename we will use for the config file.

    Sub-commands:
        cache
            set <dir>       Location of the cache, defaults to /tmp
            get             Print the location of the cache
            clear           Clear the cache
            download        Download everything in the config file to the cache
    """
    parser = argparse.ArgumentParser(description="Chat Helper")
    parser.add_argument(
        "-c", "--config", help="The yaml filename we will use for the config file."
    )
    parser.set_defaults(func=lambda _: parser.print_help())
    subparsers = parser.add_subparsers(help="Possible Commands")

    # Add the keys sub-command to add keys needed to access services
    keys_parser = subparsers.add_parser("keys", help="API Keys Access")
    keys_parser.set_defaults(func=lambda _: keys_parser.print_help())
    keys_subparsers = keys_parser.add_subparsers(help="Possible Commands")

    # list all keys command, and set all keys
    keys_list_parser = keys_subparsers.add_parser("list", help="List API keys")
    keys_list_parser.set_defaults(func=keys_list)

    keys_set_parser = keys_subparsers.add_parser("set", help="Set/Add a API key")
    keys_set_parser.add_argument("key", help="The key to set")
    keys_set_parser.add_argument("value", help="The value to set the key to")
    keys_set_parser.set_defaults(func=keys_set)

    # Add the cache sub-command & sub-commands parser for it.
    cache_parser = subparsers.add_parser("cache", help="Paper/Document Download Cache")
    cache_parser.set_defaults(func=lambda _: cache_parser.print_help())
    cache_subparsers = cache_parser.add_subparsers(help="Possible Commands")

    # Add the cache set command and the callback to execute when it is called.
    cache_set_parser = cache_subparsers.add_parser("set", help="Set cache directory")
    cache_set_parser.add_argument("dir", help="Location of the cache, defaults to /tmp")
    cache_set_parser.set_defaults(func=cache_set)

    # Add the cache get command
    cache_get_parser = cache_subparsers.add_parser("get", help="Show cache directory")
    cache_get_parser.set_defaults(func=cache_get)

    # Add the cache clear command
    cache_clear_parser = cache_subparsers.add_parser("clear", help="Delete cache")
    cache_clear_parser.add_argument(
        "--force",
        action="store_true",
        help="Do not ask before deleting cache directory",
    )
    cache_clear_parser.set_defaults(func=cache_clear)

    # List all downloaded files in the cache for a config
    cache_list_parser = cache_subparsers.add_parser(
        "list", help="List all downloaded files in the cache"
    )
    cache_list_parser.set_defaults(func=cache_list)

    # Dump a paper content
    cache_dump_parser = cache_subparsers.add_parser(
        "dump", help="Dump a paper content to stdout"
    )
    cache_dump_parser.add_argument("ref", help="The Ref of the paper to dump")
    cache_dump_parser.set_defaults(func=cache_dump)

    # Add the cache download command
    cache_download_parser = cache_subparsers.add_parser(
        "download", help="Download all papers to cache for a configuration file"
    )
    cache_download_parser.add_argument(
        "-n",
        help="Number of (uncached) papers to download",
        type=int,
    )
    cache_download_parser.set_defaults(func=cache_download)

    # The vector sub-command deals with the vector store.
    vector_parser = subparsers.add_parser(
        "vector",
        help="Vector Store DB",
        epilog="All commands other than get/set require a configuration file",
    )
    vector_parser.set_defaults(func=lambda _: vector_parser.print_help())
    vector_subparsers = vector_parser.add_subparsers(help="Possible Commands")

    # You can get, set, clear, list, and populate the contents of the store.
    vector_get_parser = vector_subparsers.add_parser(
        "get", help="show master vector store directory"
    )
    vector_get_parser.set_defaults(func=vector_get)
    vector_set_parser = vector_subparsers.add_parser(
        "set", help="set master vector store directory"
    )
    vector_set_parser.add_argument("directory", help="where to put vector stores")
    vector_set_parser.set_defaults(func=vector_set)
    vector_clear_parser = vector_subparsers.add_parser(
        "clear", help="clear vector store directory"
    )
    vector_clear_parser.set_defaults(func=vector_clear)
    vector_clear_parser.add_argument("--force", help="do not ask before deleting")
    vector_list_parser = vector_subparsers.add_parser(
        "list", help="list papers already stored in a vector store"
    )
    vector_list_parser.set_defaults(func=vector_list)
    vector_populate_parser = vector_subparsers.add_parser(
        "populate", help="populate vector store with already cached papers"
    )
    vector_populate_parser.set_defaults(func=vector_populate)

    # The query sub command has find and ask sub commands
    query_parser = subparsers.add_parser("query", help="Query the vector store")
    query_parser.set_defaults(func=lambda _: query_parser.print_help())
    query_subparsers = query_parser.add_subparsers(help="Possible Commands")

    # The find command finds similar text chunks.
    query_find_parser = query_subparsers.add_parser(
        "find", help="Find similar text chunks from the vector store"
    )
    query_find_parser.add_argument("query", help="The query to match")
    query_find_parser.add_argument("-n", help="The number of results to return")
    query_find_parser.set_defaults(func=query_find)

    # The ask command queries the LLM for the answer to a question.
    def ask_args(parser):
        parser.add_argument("-n", help="The number of results to return", default=4)

    query_ask_parser = query_subparsers.add_parser("ask", help="Ask the LLM a question")
    query_ask_parser.add_argument("query", help="The question to ask")
    ask_args(query_ask_parser)
    query_ask_parser.set_defaults(func=query_ask)

    # The config sub command, which will allow us to list a config file, and combine
    # duplicate entries.
    config_parser = subparsers.add_parser(
        "config",
        help="Working with config files",
        epilog="All commands require a config file",
    )
    config_parser.set_defaults(func=lambda _: config_parser.print_help())
    config_subparsers = config_parser.add_subparsers(help="Possible Commands")

    # list the contents of a config file
    config_list_parser = config_subparsers.add_parser(
        "list", help="List the contents of a config file"
    )
    config_list_parser.set_defaults(func=config_list)

    # The check command will look for duplicate entries in a config file, and will
    # print a fixed up version to stdout if asked.
    config_check_parser = config_subparsers.add_parser(
        "check", help="Check a config file consistency"
    )
    config_check_parser.add_argument(
        "--fix",
        action="store_true",
        help="Resolve issues detected if possible.",
    )
    config_check_parser.set_defaults(func=config_check)

    # The questions subcommand deals with questions files
    questions_parser = subparsers.add_parser(
        "questions",
        help="Working with questions files",
        epilog="All commands require a questions file.",
    )
    questions_parser.set_defaults(func=lambda _: questions_parser.print_help())
    questions_parser.add_argument(
        "--questions_file", help="The questions file", type=Path
    )
    questions_subparsers = questions_parser.add_subparsers(help="Possible Commands")

    # List the contents of a questions file
    questions_list_parser = questions_subparsers.add_parser(
        "list", help="List the contents of a questions file"
    )
    questions_list_parser.set_defaults(func=questions_list)

    # Ask the questions and generate an output files
    questions_ask_parser = questions_subparsers.add_parser(
        "ask",
        help="Ask the questions and generate an output files",
        epilog="Answers are only written to a file to make sure they are saved "
        "(given they cost money). Use the list command to show the responses "
        "nicely formatted.",
    )
    questions_ask_parser.add_argument(
        "description", help="Description to be stored along with answers", type=str
    )
    questions_ask_parser.add_argument("output_file", help="The output file", type=Path)
    questions_ask_parser.add_argument(
        "--force, -f",
        help="Overwrite output file",
        default=False,
        action="store_true",
    )
    ask_args(questions_ask_parser)
    questions_ask_parser.set_defaults(func=questions_ask)

    # Parse the arguments
    args = parser.parse_args(namespace=None)
    args.func(args)


def main():
    execute_command_line()
