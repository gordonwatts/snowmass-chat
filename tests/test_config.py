from chathelper.config import ChatDocument, load_chat_config


def test_create_chat_doc():
    ChatDocument(ref="arxiv://2109.10905", tags=[])


def test_config_load():
    c = load_chat_config("tests/simple_config.yaml")
    assert len(c.papers) == 2
