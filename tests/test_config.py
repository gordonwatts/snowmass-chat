from chathelper.config import load_chat_config


def test_config_load():
    c = load_chat_config("tests/simple_config.yaml")
    assert len(c.papers) == 2
