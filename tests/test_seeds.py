import os
import tempfile
from pathlib import Path

from dbwarden.constants import SEEDS_DIR
from dbwarden.engine.seeds import (
    SEED_SQL_PATTERN,
    SEED_PYTHON_PATTERN,
    _get_seed_filepaths_by_version,
    _description_from_filename,
    generate_seed_filename,
    get_next_seed_number,
    get_pending_seeds,
    get_seeds_to_rollback,
    read_sql_seed,
)
from dbwarden.repositories.seeds_repo import (
    create_seeds_table_if_not_exists,
    get_all_seed_records,
    get_applied_seed_versions,
    record_applied_seed,
    remove_seed_record,
    seed_is_applied,
    seeds_table_exists,
)


def _write_seed(directory: str, name: str, content: str) -> None:
    with open(os.path.join(directory, name), "w", encoding="utf-8") as f:
        f.write(content)


def _setup_dbwarden_config(tmpdir: str, db_filename: str = "test.db") -> str:
    db_path = f"sqlite:///./{db_filename}"
    Path(tmpdir, "dbwarden.py").write_text(
        f"from dbwarden import database_config\n\n"
        f"database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='{db_path}')\n",
        encoding="utf-8",
    )
    return db_path


def test_seed_sql_pattern_matches():
    m = SEED_SQL_PATTERN.match("V0001__create_users.sql")
    assert m is not None
    assert m.group(1) == "0001"
    assert m.group(2) == "create_users"


def test_seed_sql_pattern_rejects_non_v_prefix():
    assert SEED_SQL_PATTERN.match("0001__create_users.sql") is None
    assert SEED_SQL_PATTERN.match("migration__0001__create_users.sql") is None


def test_seed_python_pattern_matches():
    m = SEED_PYTHON_PATTERN.match("V0002__seed_data.py")
    assert m is not None
    assert m.group(1) == "0002"
    assert m.group(2) == "seed_data"


def test_generate_seed_filename_sql():
    name = generate_seed_filename("primary", "create_users", "0001", "sql")
    assert name == "V0001__create_users.sql"


def test_generate_seed_filename_python():
    name = generate_seed_filename("primary", "seed_data", "0002", "python")
    assert name == "V0002__seed_data.py"


def test_generate_seed_filename_sanitizes():
    name = generate_seed_filename("primary", "Add Users!!", "0001", "sql")
    assert name == "V0001__add_users.sql"


def test_get_next_seed_number_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        num = get_next_seed_number(tmpdir)
        assert num == "0001"


def test_get_next_seed_number_increments():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_seed(tmpdir, "V0001__create_users.sql", "")
        num = get_next_seed_number(tmpdir)
        assert num == "0002"


def test_get_next_seed_number_mixed_types():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_seed(tmpdir, "V0001__create_users.sql", "")
        _write_seed(tmpdir, "V0002__seed_data.py", "")
        num = get_next_seed_number(tmpdir)
        assert num == "0003"


def test_get_seed_filepaths_by_version():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_seed(tmpdir, "V0001__create_users.sql", "INSERT INTO users ...")
        _write_seed(tmpdir, "V0002__seed_data.py", "def seed(): pass")
        seeds = _get_seed_filepaths_by_version(tmpdir)
        assert "0001" in seeds
        assert seeds["0001"][1] == "sql"
        assert "0002" in seeds
        assert seeds["0002"][1] == "python"
        assert len(seeds) == 2


def test_get_seed_filepaths_by_version_ignores_non_seed():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_seed(tmpdir, "regular_file.sql", "")
        _write_seed(tmpdir, "V0001__ok.sql", "")
        seeds = _get_seed_filepaths_by_version(tmpdir)
        assert "0001" in seeds
        assert len(seeds) == 1


def test_description_from_filename():
    assert _description_from_filename("V0001__create_users.sql") == "create users"
    assert _description_from_filename("V0002__seed_data.py") == "seed data"


def test_read_sql_seed():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "V0001__test.sql")
        _write_seed(tmpdir, "V0001__test.sql", "INSERT INTO t VALUES (1);")
        content = read_sql_seed(path)
        assert content == "INSERT INTO t VALUES (1);"


def _reset_dev_mode():
    from dbwarden.config import set_dev_mode
    set_dev_mode(False)


def test_get_pending_seeds_all_pending_when_no_table():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            _reset_dev_mode()
            _setup_dbwarden_config(tmpdir, "test_pend.db")
            create_seeds_table_if_not_exists(db_name=None)
            _write_seed(tmpdir, "V0001__create_users.sql", "")
            pending = get_pending_seeds(tmpdir, db_name=None)
            assert "0001" in pending
        finally:
            os.chdir(old_cwd)


def test_get_seeds_to_rollback():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            _reset_dev_mode()
            _setup_dbwarden_config(tmpdir, "test_roll.db")
            create_seeds_table_if_not_exists(db_name=None)
            _write_seed(tmpdir, "V0001__first.sql", "")
            _write_seed(tmpdir, "V0002__second.sql", "")
            _write_seed(tmpdir, "V0003__third.sql", "")
            record_applied_seed("0001", "first", "V0001__first.sql", "sql", "c1", db_name=None)
            record_applied_seed("0002", "second", "V0002__second.sql", "sql", "c2", db_name=None)
            record_applied_seed("0003", "third", "V0003__third.sql", "sql", "c3", db_name=None)
            to_rollback = get_seeds_to_rollback(tmpdir, count=1, db_name=None)
            assert len(to_rollback) == 1
            assert "0003" in to_rollback
        finally:
            os.chdir(old_cwd)


def test_seeds_table_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            _reset_dev_mode()
            _setup_dbwarden_config(tmpdir, "test_create.db")
            create_seeds_table_if_not_exists(db_name=None)
            assert seeds_table_exists(db_name=None)
        finally:
            os.chdir(old_cwd)


def test_seed_record_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            _reset_dev_mode()
            _setup_dbwarden_config(tmpdir, "test_rtrip.db")
            create_seeds_table_if_not_exists(db_name=None)
            assert not seed_is_applied("0001", db_name=None)
            record_applied_seed(
                version="0001",
                description="create users",
                filename="V0001__create_users.sql",
                seed_type="sql",
                checksum="abc123",
                db_name=None,
            )
            assert seed_is_applied("0001", db_name=None)
            records = get_all_seed_records(db_name=None)
            assert len(records) == 1
            assert records[0].version == "0001"
            assert records[0].description == "create users"
            assert records[0].seed_type == "sql"
        finally:
            os.chdir(old_cwd)


def test_remove_seed_record():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            _reset_dev_mode()
            _setup_dbwarden_config(tmpdir, "test_rm.db")
            create_seeds_table_if_not_exists(db_name=None)
            record_applied_seed(
                version="0001",
                description="test",
                filename="V0001__test.sql",
                seed_type="sql",
                checksum="abc",
                db_name=None,
            )
            assert seed_is_applied("0001", db_name=None)
            remove_seed_record("0001", db_name=None)
            assert not seed_is_applied("0001", db_name=None)
        finally:
            os.chdir(old_cwd)


def test_get_applied_seed_versions():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            _reset_dev_mode()
            _setup_dbwarden_config(tmpdir, "test_vers.db")
            create_seeds_table_if_not_exists(db_name=None)
            record_applied_seed("0001", "a", "V1.sql", "sql", "c1", db_name=None)
            record_applied_seed("0002", "b", "V2.sql", "sql", "c2", db_name=None)
            versions = get_applied_seed_versions(db_name=None)
            assert versions == {"0001", "0002"}
        finally:
            os.chdir(old_cwd)


def test_seed_create_creates_directory_and_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            _reset_dev_mode()
            _setup_dbwarden_config(tmpdir, "test_scdir.db")
            from dbwarden.commands.seeds import seed_create_cmd
            seed_create_cmd("my_seed", seed_type="sql", database=None, verbose=False)
            seeds_path = Path(tmpdir) / SEEDS_DIR
            assert seeds_path.exists()
            files = list(seeds_path.iterdir())
            assert len(files) == 1
            assert files[0].name.endswith(".sql")
            assert "my_seed" in files[0].name
        finally:
            os.chdir(old_cwd)


def test_seeds_table_configurable():
    """Seed tracking table name is configurable via seed_table param."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            _reset_dev_mode()
            db_path = f"sqlite:///./{Path(tmpdir).name}_seeds.db"
            Path(tmpdir, "dbwarden.py").write_text(
                "from dbwarden import database_config\n\n"
                f"database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='{db_path}', seed_table='custom_seeds')\n",
                encoding="utf-8",
            )
            from dbwarden.database.queries import get_seed_table_name

            table_name = get_seed_table_name(db_name=None)
            assert table_name == "custom_seeds"

            create_seeds_table_if_not_exists(db_name=None)
            assert seeds_table_exists(db_name=None)

            record_applied_seed("0001", "test", "V0001__test.sql", "sql", "abc", db_name=None)
            assert seed_is_applied("0001", db_name=None)
            records = get_all_seed_records(db_name=None)
            assert len(records) == 1
            assert records[0].version == "0001"
        finally:
            os.chdir(old_cwd)
