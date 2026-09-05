from app.storage.source_store import SourceStore


def test_source_and_chunk_locator(tmp_path):
    store=SourceStore(str(tmp_path/'data'))
    imported=store.import_text('x.md','Alpha beta gamma.\n\nDelta epsilon.')
    assert imported['source_id']
    rows=store.list_sources()
    assert rows[0]['source_name']=='x.md'
    source=store.source(imported['source_id'])
    assert source and source['chunks']
    chunk_id=source['chunks'][0]['chunk_id']
    chunk=store.chunk(chunk_id)
    assert chunk and chunk['source_id']==imported['source_id']
    assert store.snapshot_id().startswith('corpus_')
