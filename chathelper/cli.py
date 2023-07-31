import argparse
import logging
from pathlib import Path
from typing import Any, Dict
import yaml


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
        return Path(self._load().get("cache_dir", "/tmp"))

    @cache_dir.setter
    def cache_dir(self, value: Path) -> None:
        """Set the cache directory"""
        self._update({"cache_dir": str(value.absolute())})


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
    raise NotImplementedError()


def cache_clear(args):
    """Clear the cache"""
    raise NotImplementedError()


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
    subparsers = parser.add_subparsers(help="sub-command help")

    # Add the cache sub-command & sub-commands parser for it.
    cache_parser = subparsers.add_parser("cache", help="cache help")
    cache_subparsers = cache_parser.add_subparsers(help="cache sub-command help")

    # Add the cache set command and the callback to execute when it is called.
    cache_set_parser = cache_subparsers.add_parser("set", help="cache set help")
    cache_set_parser.add_argument("dir", help="Location of the cache, defaults to /tmp")
    cache_set_parser.set_defaults(func=cache_set)

    # Add the cache get command
    cache_get_parser = cache_subparsers.add_parser("get", help="cache get help")
    cache_get_parser.set_defaults(func=cache_get)

    # Add the cache clear command
    cache_clear_parser = cache_subparsers.add_parser("clear", help="cache clear help")
    cache_clear_parser.set_defaults(func=cache_clear)

    # Add the cache download command
    cache_download_parser = cache_subparsers.add_parser(
        "download", help="cache download help"
    )
    cache_download_parser.set_defaults(func=cache_download)

    # Parse the arguments
    args = parser.parse_args()
    args.func(args)


def main():
    execute_command_line()
