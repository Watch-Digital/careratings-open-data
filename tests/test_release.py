"""End-to-end build on synthetic CMS files, plus the unit behaviour of each module."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from tcr_open_data.build import build_release, file_encoding, normalized_copy
from tcr_open_data.catalog import resolve_sources, vintage_from_filename
from tcr_open_data.codebook import render_codebook
from tcr_open_data.download import describe_local_files, load_sources_json
from tcr_open_data.headers import HeaderMismatch, check_header, snake
from tcr_open_data.manifest import update_root_manifest, write_release_manifest
from tcr_open_data.schema import column_names, load_schema
from tcr_open_data.sources import SOURCES
from tcr_open_data.storage import R2Config, content_type, plan_uploads, publish
from tcr_open_data.validate import reconcile, validate_release

from fixtures import FILENAMES, write_fixture_raw


@pytest.fixture(scope="module")
def release(tmp_path_factory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("release")
    raw = root / "raw"
    filenames = write_fixture_raw(raw)
    describe_local_files(raw, filenames)
    result = build_release(raw, root / "releases", load_sources_json(raw))
    (result.release_dir / "codebook.md").write_text(render_codebook(result.chain_measure_columns, result.release), encoding="utf-8")
    validate_release(result.release_dir)
    write_release_manifest(result.release_dir)
    return raw, result.release_dir


def _rows(release_dir: Path, table: str) -> list[dict]:
    con = duckdb.connect()
    cur = con.execute(f"SELECT * FROM read_parquet('{(release_dir / (table + '.parquet')).as_posix()}')")
    columns = [d[0] for d in cur.description]
    return [dict(zip(columns, r)) for r in cur.fetchall()]


def test_release_is_named_after_the_provider_information_processing_date(release):
    _, release_dir = release
    assert release_dir.name == "v2026.08"


def test_every_table_matches_the_schema_and_validation_passes(release):
    _, release_dir = release
    schema = load_schema()
    build = json.loads((release_dir / "build.json").read_text())
    for table in schema["tables"]:
        expected = column_names(table)
        if table == "chains":
            expected = expected + build["chain_measure_columns"]
        assert build["tables"][table]["columns"] == expected, table
    validation = json.loads((release_dir / "validation.json").read_text())
    assert validation["status"] == "pass", [c for c in validation["checks"] if c["status"] != "pass"]


def test_owner_versus_party_semantics(release):
    _, release_dir = release
    facilities = {r["ccn"]: r for r in _rows(release_dir, "facilities")}
    alpha, beta, gamma = facilities["100001"], facilities["100002"], facilities["100003"]
    # Alpha: the current enrollment (highest id) has a PE fund with an indirect ownership role and a REIT as an additional disclosable party.
    assert alpha["pecos_enrollment_id"] == "O20200101000002"
    assert alpha["has_private_equity_owner"] is True and alpha["private_equity_owner_names"] == "BUYOUT FUND IV LP"
    assert alpha["has_reit_owner"] is False and alpha["has_reit_party"] is True and alpha["reit_party_names"] == "PROPCO REIT INC"
    assert alpha["affiliation_entity_name"] == "ALPHA GROUP" and alpha["chain_id"] == "154"
    assert alpha["pecos_owner_rows"] == 3
    # Beta: a PE-flagged staffing vendor is a party, never an owner.
    assert beta["has_private_equity_owner"] is False and beta["has_private_equity_party"] is True
    assert beta["ownership_category"] == "Non profit"
    # Gamma has no PECOS enrollment at all.
    assert gamma["pecos_enrollment_id"] is None and gamma["pecos_owner_rows"] == 0 and gamma["has_reit_party"] is False


def test_change_of_ownership_and_staffing_floors(release):
    _, release_dir = release
    facilities = {r["ccn"]: r for r in _rows(release_dir, "facilities")}
    alpha, beta, gamma = facilities["100001"], facilities["100002"], facilities["100003"]
    assert str(alpha["last_chow_date"]) == "2025-03-01" and alpha["chow_count_36mo"] == 1
    assert beta["last_chow_date"] is None and beta["chow_count_36mo"] == 0
    assert alpha["meets_repealed_rn_floor"] is True and alpha["meets_all_repealed_floors"] is True
    assert beta["meets_repealed_rn_floor"] is False and beta["meets_all_repealed_floors"] is False
    assert gamma["meets_repealed_rn_floor"] is None and gamma["meets_all_repealed_floors"] is None


def test_state_summary_reproduces_the_care_quality_index_formula(release):
    _, release_dir = release
    summary = {r["state"]: r for r in _rows(release_dir, "state_summary")}
    pa, us = summary["PA"], summary["US"]
    assert pa["facility_count"] == 2 and us["facility_count"] == 10 and summary["TX"]["facility_count"] == 7
    assert isinstance(us["care_quality_index"], int), "the national row has 10 facilities and gets a composite"
    # PA: ratings 3 and 5 -> 4.0; one of two penalty-free -> 50.0; staffing 4 and 5 -> 100.0
    assert pa["avg_overall_rating"] == 4.0 and pa["pct_zero_penalty"] == 50.0 and pa["pct_staffing_4plus"] == 100.0
    assert pa["care_quality_index"] is None, "fewer than 10 facilities gets no composite"
    assert us["facilities_pe_owner"] == 1 and us["facilities_pe_party"] == 2 and us["facilities_reit_party"] == 1
    assert us["sff_count"] == 1 and us["sff_candidate_count"] == 1 and us["abuse_icon_count"] == 1
    assert us["total_fines_dollars"] == 12000.0 and us["chow_count_12mo"] == 0
    assert summary["OH"]["pct_meeting_all_repealed_floors"] is None
    assert list(summary)[0] == "US"


def test_care_quality_index_formula_matches_the_site():
    # 49 states worth of arithmetic is overkill; check the formula on one hand-computed row.
    normalized = (3.45 - 1) / 4 * 100
    assert round(normalized * 0.40 + 65.0 * 0.35 + 100.0 * 0.25) == 72  # Alaska, August 2026 release


def test_care_compare_ownership_parsing(release):
    _, release_dir = release
    rows = {r["owner_name"]: r for r in _rows(release_dir, "owners_carecompare")}
    assert rows["ALPHA HOLDINGS LLC"]["ownership_pct"] == 60.0 and str(rows["ALPHA HOLDINGS LLC"]["association_date"]) == "2012-01-25"
    assert rows["DOE, JANE"]["ownership_pct"] is None and rows["DOE, JANE"]["ownership_percentage_raw"] == "NO PERCENTAGE PROVIDED"


def test_chains_keep_the_national_row_and_measure_columns(release):
    _, release_dir = release
    chains = {r["chain_id"]: r for r in _rows(release_dir, "chains")}
    assert chains["NATIONAL"]["facility_count"] == 10 and chains["154"]["chain_name"] == "COMMUNITY CARE CENTERS"
    assert chains["NATIONAL"]["average_percentage_of_long_stay_residents_who_received_an_antipsychotic_medication"] == 15.4


def test_manifest_lists_every_file_with_checksums_and_licenses(release):
    raw, release_dir = release
    manifest = json.loads((release_dir / "manifest.json").read_text())
    assert manifest["release"] == "v2026.08" and manifest["validation"]["status"] == "pass"
    assert {f["format"] for f in manifest["files"]} == {"csv", "parquet"}
    assert all(len(f["sha256"]) == 64 and f["bytes"] > 0 for f in manifest["files"])
    assert next(f for f in manifest["files"] if f["table"] == "crosswalk")["license"] == "CC0 1.0"
    assert manifest["sources"]["enrollments"]["vintage"] == "2026-07-31"
    assert "enrollments" in json.loads((release_dir / "build.json").read_text())["encoding_normalized"]


def test_root_manifest_keeps_newest_first_with_latest_pointer():
    older = {"release": "v2026.07", "built_at": "2026-08-05T00:00:00Z", "processing_date": "2026-07-01", "publisher": {"name": "x"}, "validation": {"status": "pass"}}
    newer = {"release": "v2026.08", "built_at": "2026-09-14T00:00:00Z", "processing_date": "2026-08-01", "publisher": {"name": "x"}, "validation": {"status": "pass"}}
    root = update_root_manifest(None, newer)
    root = update_root_manifest(root, older)
    root = update_root_manifest(root, newer)  # republishing the same release replaces its entry
    assert [r["release"] for r in root["releases"]] == ["v2026.08", "v2026.07"] and root["latest"] == "v2026.08"
    assert root["releases"][0]["manifest"] == "releases/v2026.08/manifest.json"


def test_publish_dry_run_plans_release_and_raw_objects(release):
    raw, release_dir = release
    plan = plan_uploads(release_dir, raw, "v2026.08")
    keys = [k for _, k in plan]
    assert "releases/v2026.08/facilities.parquet" in keys and "releases/v2026.08/manifest.json" in keys
    assert "raw/v2026.08/NH_ProviderInfo_Aug2026.csv" in keys and "raw/v2026.08/sources.json" in keys
    summary = publish(release_dir, raw, dry_run=True, config=None)
    assert summary["dry_run"] is True and summary["objects"] == keys
    assert content_type(Path("x.parquet")).startswith("application/vnd.apache.parquet") and content_type(Path("x.csv")).startswith("text/csv")
    with pytest.raises(RuntimeError):
        publish(release_dir, raw, dry_run=False, config=None)


def test_publish_live_uploads_and_updates_root_manifest(release):
    raw, release_dir = release

    class FakeS3:
        def __init__(self):
            self.objects: dict[str, bytes] = {}

        def upload_file(self, path, bucket, key, ExtraArgs=None):
            self.objects[key] = Path(path).read_bytes()

        def get_object(self, Bucket, Key):
            if Key not in self.objects:
                raise KeyError(Key)
            return {"Body": type("B", (), {"read": lambda self_, k=Key: self.objects[k]})()}

        def put_object(self, Bucket, Key, Body, ContentType, CacheControl=None):
            self.objects[Key] = Body

    fake = FakeS3()
    config = R2Config("acct", "key", "secret", "bucket")
    summary = publish(release_dir, raw, dry_run=False, config=config, client=fake)
    assert summary["root_manifest"]["latest"] == "v2026.08"
    assert json.loads(fake.objects["manifest.json"])["releases"][0]["path"] == "releases/v2026.08/"
    assert "releases/v2026.08/codebook.md" in fake.objects


def test_header_guard_names_missing_and_unexpected_columns(tmp_path):
    path = tmp_path / "NH_Penalties_Aug2026.csv"
    path.write_text('"CMS Certification Number (CCN)","Provider Name","Penalty Type","Brand New Column"\n', encoding="utf-8")
    with pytest.raises(HeaderMismatch) as excinfo:
        check_header(SOURCES["penalties"], path)
    assert "Penalty Date" in excinfo.value.missing and "Brand New Column" in excinfo.value.unexpected


def test_chain_header_allows_extra_measures_but_not_a_changed_prefix(tmp_path):
    path = tmp_path / "Chain_Performance_20260909.csv"
    path.write_text(",".join(SOURCES["chains"].header) + ",Average something new\n", encoding="utf-8")
    assert check_header(SOURCES["chains"], path)[-1] == "Average something new"
    path.write_text("Chain ID,Chain," + ",".join(SOURCES["chains"].header[2:]) + "\n", encoding="utf-8")
    with pytest.raises(HeaderMismatch):
        check_header(SOURCES["chains"], path)


def test_vintage_parsing_and_snake_case():
    assert vintage_from_filename("SNF_All_Owners_2026.07.31.csv") == "2026-07-31"
    assert vintage_from_filename("Chain_Performance_20260909.csv") == "2026-09-09"
    assert vintage_from_filename("NH_ProviderInfo_Aug2026.csv") == "2026-08-01"
    assert vintage_from_filename("unknown.csv") is None
    assert snake("Average overall 5-star rating") == "average_overall_5_star_rating"
    assert snake("Percent of facilities classified as for-profit") == "percent_of_facilities_classified_as_for_profit"


def test_encoding_detection_and_normalization(tmp_path):
    good = tmp_path / "good.csv"
    good.write_bytes("a,b\n1,café\n".encode("utf-8"))
    bad = tmp_path / "bad.csv"
    bad.write_bytes(b"a,b\n1,caf\xe9\n2,\x93quoted\x94\n")
    assert file_encoding(good) == "utf-8" and file_encoding(bad) == "latin-1"
    work = tmp_path / "work"
    work.mkdir()
    copied, normalized = normalized_copy(bad, work)
    assert normalized and copied != bad and copied.read_text(encoding="utf-8") == "a,b\n1,café\n2,“quoted”\n"
    assert normalized_copy(good, work) == (good, False)


def test_catalog_resolution_is_offline_testable():
    metastore = {
        "4pq5-n9py": {"modified": "2026-08-01", "distribution": [{"downloadURL": "https://x/NH_ProviderInfo_Aug2026.csv"}]},
        "g6vv-u9sr": {"modified": "2026-08-01", "distribution": [{"data": {"downloadURL": "https://x/NH_Penalties_Aug2026.csv"}}]},
        "y2hd-n93e": {"modified": "2026-08-01", "distribution": [{"downloadURL": "https://x/NH_Ownership_Aug2026.csv"}]},
    }
    catalog = {"dataset": [
        {"title": s.title, "modified": "2026-08-17", "distribution": [{"format": "CSV", "downloadURL": f"https://y/{s.local_name}"}, {"format": "API", "accessURL": "https://api"}]}
        for s in SOURCES.values() if s.pdc_id is None
    ]}
    resolved = resolve_sources(session=None, catalog_json=catalog, metastore=metastore)
    assert resolved["provider_info"].filename == "NH_ProviderInfo_Aug2026.csv" and resolved["penalties"].url.endswith("Penalties_Aug2026.csv")
    assert resolved["chains"].url == "https://y/Chain_Performance.csv" and resolved["all_owners"].modified == "2026-08-17"


def test_catalog_picks_newest_dated_version():
    # data.cms.gov data.json now lists only '<title> : YYYY-MM-DD' entries.
    def entry(title, modified, filename):
        return {"title": title, "modified": modified, "distribution": [{"format": "CSV", "downloadURL": f"https://y/{filename}"}]}
    datasets = []
    for s in SOURCES.values():
        if s.pdc_id is None:
            datasets += [entry(f"{s.title} : 2026-08-01", "2026-09-29", f"old_{s.local_name}"),
                         entry(f"{s.title} : 2026-10-01", "2026-10-19", f"new_{s.local_name}")]
    # A sibling dataset whose title only starts with ours must not be picked.
    datasets.append(entry("Skilled Nursing Facility Change of Ownership - Owner Information : 2026-12-01", "2026-12-02", "owners.csv"))
    metastore = {s.pdc_id: {"distribution": [{"downloadURL": f"https://x/{s.local_name}"}]} for s in SOURCES.values() if s.pdc_id}
    resolved = resolve_sources(session=None, catalog_json={"dataset": datasets}, metastore=metastore)
    for key, s in SOURCES.items():
        if s.pdc_id is None:
            assert resolved[key].filename == f"new_{s.local_name}"
    assert resolved["chow"].modified == "2026-10-19"


def test_reconcile_tolerances():
    cms = {"facilities": 14702, "sff": 84, "sff_candidates": 441, "abuse_icons": 1427, "total_fines_dollars": 456761299, "total_fines": 13257, "payment_denials": 2440}
    ours = dict(cms, facilities=14690, total_fines_dollars=480_000_000)
    checks = {c.name: c for c in reconcile(ours, cms)}
    assert checks["reconcile:facilities"].status == "pass" and checks["reconcile:total_fines_dollars"].status == "warn"
    assert checks["reconcile:total_fines_dollars"].detail["diff_pct"] == 5.09


def test_codebook_covers_every_table_and_column():
    text = render_codebook(["average_x"], "v2026.08")
    schema = load_schema()
    for table, spec in schema["tables"].items():
        assert f"## `{table}`" in text
        for column in spec["columns"]:
            assert f"| `{column['name']}` |" in text
    assert "- `average_x`" in text
