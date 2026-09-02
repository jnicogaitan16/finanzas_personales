from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_alembic_migration_chain_is_valid() -> None:
    """Verify the migration scripts form a valid chain reaching head."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "db" / "migrations"))
    cfg.set_main_option("prepend_sys_path", str(BACKEND_DIR))

    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    assert head == "004_enhanced_model"

    revisions = list(script.walk_revisions())
    assert len(revisions) == 4
