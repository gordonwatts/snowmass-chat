from typing import List
from pydantic import BaseModel
from dataclasses import dataclass
import yaml


@dataclass
class ChatDocument:
    # the fsspec string that leads to the paper itself
    ref: str

    # Tags is a list of tags (like the frontier, etc.) attached to the thing
    tags: list[str]

    class Config:
        env_file = "bogus.yaml"


class ChatConfig(BaseModel):
    papers: List[ChatDocument]


def load_config(path: str) -> ChatConfig:
    """Load a chat config from a path"""
    with open(path, "r") as f:
        return ChatConfig.model_validate(yaml.safe_load(f))