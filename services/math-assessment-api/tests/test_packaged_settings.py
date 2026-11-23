import base64
import gzip
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import settings


@pytest.fixture(autouse=True)
def clear_configured_database_paths(monkeypatch) -> None:
    """Materialization tests must exercise archives, not caller DB overrides."""

    monkeypatch.delenv("MATH_ASSESSMENT_PUBLISH_DB", raising=False)
    monkeypatch.delenv("MATH_ASSESSMENT_DETAIL_DB", raising=False)


def test_catalog_archive_is_materialized_to_temporary_storage(
    tmp_path, monkeypatch
) -> None:
    source = tmp_path / "source.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES ('ready')")

    archive = tmp_path / "catalog.sqlite.gz.b64"
    archive.write_bytes(
        base64.b64encode(gzip.compress(source.read_bytes(), compresslevel=9, mtime=0))
    )
    runtime_directory = tmp_path / "runtime"
    runtime_directory.mkdir()

    monkeypatch.setattr(
        settings, "DEFAULT_DETAIL_DATABASE", tmp_path / "missing-detail.sqlite"
    )
    monkeypatch.setattr(settings, "DEFAULT_DATABASE", tmp_path / "missing-default.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE", tmp_path / "missing-package.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_GZIP", tmp_path / "missing.sqlite.gz")
    monkeypatch.setattr(
        settings, "PACKAGED_DATABASE_GZIP_PATTERN", "missing.sqlite.gz.part-*"
    )
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_ARCHIVE", archive)
    monkeypatch.setattr(settings.tempfile, "tempdir", str(runtime_directory))

    materialized = settings.catalog_database_path()

    assert materialized.parent == runtime_directory
    assert materialized.name.startswith("science-assessment-catalog-")
    assert materialized.suffix == ".sqlite"
    with sqlite3.connect(materialized) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == "ready"


def test_binary_gzip_parts_are_materialized_without_base64(
    tmp_path, monkeypatch
) -> None:
    source = tmp_path / "source.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES ('binary-ready')")
    compressed = gzip.compress(source.read_bytes(), compresslevel=9, mtime=0)
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    midpoint = len(compressed) // 2
    (data_directory / "catalog.sqlite.gz.part-00").write_bytes(compressed[:midpoint])
    (data_directory / "catalog.sqlite.gz.part-01").write_bytes(compressed[midpoint:])
    runtime_directory = tmp_path / "runtime"
    runtime_directory.mkdir()

    monkeypatch.setattr(
        settings, "DEFAULT_DETAIL_DATABASE", tmp_path / "missing-detail.sqlite"
    )
    monkeypatch.setattr(settings, "DEFAULT_DATABASE", tmp_path / "missing-default.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE", tmp_path / "missing-package.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_GZIP", data_directory / "missing.gz")
    monkeypatch.setattr(
        settings, "PACKAGED_DATABASE_GZIP_PATTERN", "catalog.sqlite.gz.part-*"
    )
    monkeypatch.setattr(settings, "PACKAGED_DATA", data_directory)
    monkeypatch.setattr(settings.tempfile, "tempdir", str(runtime_directory))

    materialized = settings.catalog_database_path()

    with sqlite3.connect(materialized) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == "binary-ready"


def test_concurrent_catalog_materialization_reuses_one_atomic_database(
    tmp_path, monkeypatch
) -> None:
    source = tmp_path / "source.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES ('concurrent-ready')")
    compressed = gzip.compress(source.read_bytes(), compresslevel=9, mtime=0)
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    midpoint = len(compressed) // 2
    (data_directory / "catalog.sqlite.gz.part-00").write_bytes(compressed[:midpoint])
    (data_directory / "catalog.sqlite.gz.part-01").write_bytes(compressed[midpoint:])
    runtime_directory = tmp_path / "runtime"
    runtime_directory.mkdir()

    monkeypatch.setattr(settings, "PACKAGED_DATABASE", data_directory / "missing.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_GZIP", data_directory / "missing.gz")
    monkeypatch.setattr(
        settings, "PACKAGED_DATABASE_GZIP_PATTERN", "catalog.sqlite.gz.part-*"
    )
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_ARCHIVE", data_directory / "legacy")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_ARCHIVE_PATTERN", "legacy.part-*")
    monkeypatch.setattr(settings, "PACKAGED_RELEASE_MANIFEST", data_directory / "missing.json")
    monkeypatch.setattr(settings, "PACKAGED_DATA", data_directory)
    monkeypatch.setattr(settings.tempfile, "tempdir", str(runtime_directory))

    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(lambda _: settings.materialized_packaged_database(), range(16)))

    assert len(set(paths)) == 1
    assert not list(runtime_directory.glob("*.partial"))
    with sqlite3.connect(paths[0]) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == "concurrent-ready"


def test_detail_gzip_parts_materialize_without_legacy_archive_pattern(
    tmp_path, monkeypatch
) -> None:
    source = tmp_path / "detail-source.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES ('detail-ready')")
    compressed = gzip.compress(source.read_bytes(), compresslevel=9, mtime=0)
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    midpoint = len(compressed) // 2
    part_zero = data_directory / "detail.sqlite.gz.part-00"
    part_one = data_directory / "detail.sqlite.gz.part-01"
    part_zero.write_bytes(compressed[:midpoint])
    part_one.write_bytes(compressed[midpoint:])
    runtime_directory = tmp_path / "runtime"
    runtime_directory.mkdir()
    manifest = data_directory / "release-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": "missing-detail.sqlite",
                        "sha256": "a" * 64,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        settings, "PACKAGED_DETAIL_DATABASE", data_directory / "missing-detail.sqlite"
    )
    monkeypatch.setattr(
        settings, "PACKAGED_DETAIL_DATABASE_GZIP", data_directory / "missing-detail.gz"
    )
    monkeypatch.setattr(
        settings,
        "PACKAGED_DETAIL_DATABASE_GZIP_PATTERN",
        "detail.sqlite.gz.part-*",
    )
    monkeypatch.setattr(settings, "PACKAGED_RELEASE_MANIFEST", manifest)
    monkeypatch.setattr(settings, "PACKAGED_DATA", data_directory)
    monkeypatch.setattr(settings.tempfile, "tempdir", str(runtime_directory))

    materialized = settings.materialized_packaged_database(detail=True)

    assert materialized.name == "science-assessment-detail-aaaaaaaaaaaaaaaa.sqlite"
    with sqlite3.connect(materialized) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == "detail-ready"


def test_catalog_uses_detail_package_when_only_detail_is_shipped(
    tmp_path, monkeypatch
) -> None:
    source = tmp_path / "detail-source.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES ('detail-serves-catalog')")
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    (data_directory / "detail.sqlite.gz.part-00").write_bytes(
        gzip.compress(source.read_bytes(), compresslevel=9, mtime=0)
    )
    runtime_directory = tmp_path / "runtime"
    runtime_directory.mkdir()

    monkeypatch.setattr(settings, "DEFAULT_DETAIL_DATABASE", tmp_path / "missing-detail.sqlite")
    monkeypatch.setattr(settings, "DEFAULT_DATABASE", tmp_path / "missing-default.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE", data_directory / "missing.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_GZIP", data_directory / "missing.gz")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_GZIP_PATTERN", "catalog.sqlite.gz.part-*")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_ARCHIVE", data_directory / "legacy")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_ARCHIVE_PATTERN", "legacy.part-*")
    monkeypatch.setattr(settings, "PACKAGED_DETAIL_DATABASE", data_directory / "missing-d.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DETAIL_DATABASE_GZIP", data_directory / "missing-d.gz")
    monkeypatch.setattr(
        settings, "PACKAGED_DETAIL_DATABASE_GZIP_PATTERN", "detail.sqlite.gz.part-*"
    )
    monkeypatch.setattr(settings, "PACKAGED_RELEASE_MANIFEST", data_directory / "none.json")
    monkeypatch.setattr(settings, "PACKAGED_DATA", data_directory)
    monkeypatch.setattr(settings.tempfile, "tempdir", str(runtime_directory))

    catalog = settings.catalog_database_path()

    assert catalog == settings.detail_catalog_database_path()
    assert catalog.name.startswith("science-assessment-detail-")
    assert len(list(runtime_directory.glob("*.sqlite"))) == 1
    with sqlite3.connect(catalog) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == (
            "detail-serves-catalog"
        )


def test_missing_manifest_identity_hashes_archive_contents(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES ('content-addressed')")
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    part = data_directory / "catalog.sqlite.gz.part-00"
    part.write_bytes(gzip.compress(source.read_bytes(), compresslevel=9, mtime=0))
    runtime_directory = tmp_path / "runtime"
    runtime_directory.mkdir()

    monkeypatch.setattr(settings, "PACKAGED_DATABASE", data_directory / "missing.sqlite")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_GZIP", data_directory / "missing.gz")
    monkeypatch.setattr(
        settings, "PACKAGED_DATABASE_GZIP_PATTERN", "catalog.sqlite.gz.part-*"
    )
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_ARCHIVE", data_directory / "legacy")
    monkeypatch.setattr(settings, "PACKAGED_DATABASE_ARCHIVE_PATTERN", "legacy.part-*")
    monkeypatch.setattr(
        settings, "PACKAGED_RELEASE_MANIFEST", data_directory / "missing-manifest.json"
    )
    monkeypatch.setattr(settings, "PACKAGED_DATA", data_directory)
    monkeypatch.setattr(settings.tempfile, "tempdir", str(runtime_directory))

    materialized = settings.materialized_packaged_database()

    assert "unknown" not in materialized.name
    with sqlite3.connect(materialized) as connection:
        assert connection.execute("SELECT value FROM marker").fetchone()[0] == "content-addressed"


def test_science_axes_fall_back_to_packaged_copy(tmp_path, monkeypatch) -> None:
    """The deploy bundle has no repo data/ folder (Vercel 500 on /references, 11-23)."""

    repo_axes = settings.DEFAULT_SCIENCE_AXES
    packaged = tmp_path / "science_axes.json"
    packaged.write_bytes(repo_axes.read_bytes())
    monkeypatch.setattr(settings, "DEFAULT_SCIENCE_AXES", tmp_path / "missing.json")
    monkeypatch.setattr(settings, "PACKAGED_SCIENCE_AXES", packaged)
    settings.science_axes.cache_clear()
    try:
        axes = settings.science_axes()
    finally:
        settings.science_axes.cache_clear()

    assert len(axes["units"]) == 23
    assert axes["activities"]
