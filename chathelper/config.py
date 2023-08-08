from typing import List, Optional
from pydantic import BaseModel
import yaml


class ChatDocument(BaseModel):
    # the fsspec string that leads to the paper itself
    ref: str

    # Tags is a list of tags (like the frontier, etc.) attached to the thing
    tags: list[str]

    title: Optional[str] = None

    class Config:
        _env_file = "bogus.yaml"


class ChatConfig(BaseModel):
    papers: List[ChatDocument]
    short_name: str


def load_chat_config(path: str) -> ChatConfig:
    """Load a chat config from a yaml file path"""

    with open(path, "r") as f:
        return ChatConfig(**yaml.safe_load(f))
