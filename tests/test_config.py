from chathelper.config import load_config


def test_config_load():
    c = load_config("tests/simple_config.yaml")
    assert len(c.papers) == 2
