import sys
from pathlib import Path as _Path
_ROOT_FOR_IMPORT = _Path(__file__).resolve().parents[1]
if str(_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_ROOT_FOR_IMPORT))
from pathlib import Path
from app.storage.source_store import SourceStore

root=Path(__file__).resolve().parents[1]
store=SourceStore(str(root/'data'))
for p in sorted((root/'datasets'/'domain').glob('*.md')):
    print(store.import_text(p.name,p.read_text(encoding='utf-8')))
