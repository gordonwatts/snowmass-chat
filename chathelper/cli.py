import argparse
import logging
import shutil
from pathlib import Path
from typing import Any, Dict

import yaml
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from chathelper.cache import download_all, find_paper, load_paper
from chathelper.config import ChatConfig, load_chat_config
from chathelper.model import (
    find_similar_text_chucks,
    populate_vector_store,
    load_vector_store_files,
    query_llm,
)


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

    progress = Progress()
    with progress:
        task1 = progress.add_task("Downloading", total=len(config.papers))
        download_all(
            config.papers, cache_dir, lambda _: progress.update(task1, advance=1)
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

    for paper in config.papers:
        title = ""
        size = "<not in cache>"
        doc_path = find_paper(paper, cache_dir)
        tags = ""
        if doc_path is not None:
            doc = load_paper(paper, cache_dir)
            assert doc is not None
            title = doc.metadata["Title"]
            size = f"{len(doc.page_content) / 1024:.0f} kb"
            tags = ", ".join(doc.metadata["chatter_tags"])
        table.add_row(paper.ref, title, size, tags)

    console = Console()
    console.print(table)


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


def query_find(args):
    """Find all similar text chunks to the query"""
    vector_dir = vector_store_path(args)
    openai_key = config_cache().keys.get("openai", None)
    if openai_key is None:
        print("No OpenAI API key set, use chatter set key openai <key>")
        return

    chunks = find_similar_text_chucks(vector_dir, openai_key, args.query, int(args.n))
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


def query_ask(args):
    """Find all similar text chunks to the query"""
    vector_dir = vector_store_path(args)
    openai_key = config_cache().keys.get("openai", None)
    if openai_key is None:
        print("No OpenAI API key set, use chatter set key openai <key>")
        return

    response = query_llm(vector_dir, openai_key, args.query, int(args.n or 4))
    print(response["result"])


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
    query_ask_parser = query_subparsers.add_parser("ask", help="Ask the LLM a question")
    query_ask_parser.add_argument("query", help="The question to ask")
    query_ask_parser.add_argument(
        "-n", help="The number of results to return", default=4
    )
    query_ask_parser.set_defaults(func=query_ask)

    # Parse the arguments
    args = parser.parse_args(namespace=None)
    args.func(args)


def main():
    execute_command_line()
