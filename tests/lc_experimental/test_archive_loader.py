from chathelper.lc_experimental.archive_loader import ArxivLoader


def test_loader_for_good_paper(tmp_path):
    query = "id:2203.08127"
    loader = ArxivLoader(
        query,
        load_all_available_meta=True,
        doc_content_chars_max=None,
        keep_pdf=True,
        cache_dir=tmp_path,
    )
    data = loader.load()

    assert len(data) == 1
