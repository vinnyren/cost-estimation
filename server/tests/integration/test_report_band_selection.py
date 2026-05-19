"""Integration tests for Project.selected_band and band-parameterized Excel export.

Tests (TDD order):
1. Project model has selected_band column, default "P50".
2. Creating a project with selected_band="P90" persists it;
   ProjectPatch can change it.
3. GET /api/reports/excel/{id}?band=P10 / ?band=P90 / (no band) each return 200
   with a non-empty xlsx blob.
4. generate_excel with band="P10" vs band="P90" produces DIFFERENT bytes
   (band actually flows through to report content).
"""
import pytest
from io import BytesIO

from app.db.models import Project, FunctionPoint

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}
HJ = {**H, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# 1. Model column existence and default
# ---------------------------------------------------------------------------

def test_project_has_selected_band_column(db_session):
    """Project ORM has selected_band column with default 'P50'."""
    cols = {c.name for c in Project.__table__.columns}
    assert "selected_band" in cols


def test_project_selected_band_default_is_p50(db_session):
    p = Project(
        id="p-band-default",
        name="band default test",
        project_type="dev_only",
        phase="bidding",
        city="北京",
        industry="电子政务",
        mode="forward",
        basis_data_ver="CSBMK-202510",
        assessment_kind="development",
        # selected_band intentionally omitted — should default to "P50"
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    assert p.selected_band == "P50"


# ---------------------------------------------------------------------------
# 2. Create with selected_band="P90"; PATCH to change it
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_project_with_selected_band_p90(client_factory):
    """Creating a project with selected_band='P90' persists it."""
    async with await client_factory() as c:
        r = await c.post("/api/projects", headers=HJ, json={
            "name": "P90 band proj",
            "project_type": "dev_only",
            "phase": "bidding",
            "city": "上海",
            "industry": "金融",
            "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
            "selected_band": "P90",
        })
        assert r.status_code == 201, r.text
        data = r.json()["data"]
        assert data["selected_band"] == "P90"


@pytest.mark.asyncio
async def test_patch_project_selected_band(client_factory):
    """PATCH /api/projects/{id} can update selected_band."""
    async with await client_factory() as c:
        # Create with default P50
        rp = await c.post("/api/projects", headers=HJ, json={
            "name": "patch band test",
            "project_type": "dev_only",
            "phase": "bidding",
            "city": "北京",
            "industry": "电子政务",
            "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        assert rp.status_code == 201
        pid = rp.json()["data"]["id"]
        assert rp.json()["data"]["selected_band"] == "P50"

        # Patch to P10
        rp2 = await c.patch(f"/api/projects/{pid}", headers=HJ,
                             json={"selected_band": "P10"})
        assert rp2.status_code == 200, rp2.text
        assert rp2.json()["data"]["selected_band"] == "P10"


# ---------------------------------------------------------------------------
# 3. Report endpoint returns 200 xlsx for each band
# ---------------------------------------------------------------------------

async def _make_project_with_fp(c, selected_band: str = "P50") -> str:
    rp = await c.post("/api/projects", headers=HJ, json={
        "name": "report band test",
        "project_type": "dev_only",
        "phase": "bidding",
        "city": "北京",
        "industry": "电子政务",
        "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
        "selected_band": selected_band,
    })
    pid = rp.json()["data"]["id"]
    await c.post(f"/api/projects/{pid}/functions", headers=HJ,
                 json={"name": "首页", "category": "EQ", "complexity": "low",
                       "ufp": 6.0, "us": 6.0})
    return pid


@pytest.mark.asyncio
async def test_download_excel_with_band_p10(client_factory, tmp_data_dir):
    """GET /api/reports/excel/{id}?band=P10 returns 200 non-empty xlsx."""
    async with await client_factory() as c:
        pid = await _make_project_with_fp(c)
        r = await c.get(f"/api/reports/excel/{pid}?band=P10", headers=H)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith(
            "application/vnd.openxmlformats"
        )
        assert len(r.content) > 0


@pytest.mark.asyncio
async def test_download_excel_with_band_p90(client_factory, tmp_data_dir):
    """GET /api/reports/excel/{id}?band=P90 returns 200 non-empty xlsx."""
    async with await client_factory() as c:
        pid = await _make_project_with_fp(c)
        r = await c.get(f"/api/reports/excel/{pid}?band=P90", headers=H)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith(
            "application/vnd.openxmlformats"
        )
        assert len(r.content) > 0


@pytest.mark.asyncio
async def test_download_excel_no_band_returns_200(client_factory, tmp_data_dir):
    """GET /api/reports/excel/{id} (no band param) returns 200."""
    async with await client_factory() as c:
        pid = await _make_project_with_fp(c)
        r = await c.get(f"/api/reports/excel/{pid}", headers=H)
        assert r.status_code == 200, r.text
        assert len(r.content) > 0


# ---------------------------------------------------------------------------
# 4. Band actually changes report bytes (P10 vs P90 differ)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_band_selection_changes_report_content(client_factory, tmp_data_dir):
    """Reports for P10 and P90 should differ (band flows through to xlsx content)."""
    async with await client_factory() as c:
        pid = await _make_project_with_fp(c)

        r_p10 = await c.get(f"/api/reports/excel/{pid}?band=P10", headers=H)
        r_p90 = await c.get(f"/api/reports/excel/{pid}?band=P90", headers=H)

        assert r_p10.status_code == 200
        assert r_p90.status_code == 200
        # P10 and P90 use different cost figures — the xlsx bytes must differ.
        assert r_p10.content != r_p90.content, (
            "P10 and P90 reports should differ but got identical bytes"
        )


@pytest.mark.asyncio
async def test_band_selection_changes_report_content_directly(
    client_factory, tmp_data_dir, db_session
):
    """Unit-ish: generate_excel with band=P10 vs P90 produces different bytes.

    Uses client_factory (async context) to seed CSBMK params, then calls
    generate_excel directly on db_session with pre-seeded project and FPs.
    """
    from pathlib import Path
    from app.services.reports import generate_excel

    pid = "p-band-diff-test"

    # Use client_factory to trigger CSBMK seeding into db_session.
    async with await client_factory() as _c:
        # Create the project and FPs via the API so CSBMK is seeded.
        rp = await _c.post("/api/projects", headers=HJ, json={
            "name": "band diff direct test",
            "project_type": "dev_only",
            "phase": "bidding",
            "city": "北京",
            "industry": "电子政务",
            "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
            "selected_band": "P50",
        })
        assert rp.status_code == 201, rp.text
        api_pid = rp.json()["data"]["id"]

        # Add two FPs for real calculation data.
        await _c.post(f"/api/projects/{api_pid}/functions", headers=HJ,
                      json={"name": "用户管理", "category": "EI",
                            "complexity": "average", "ufp": 10.0, "us": 10.0})
        await _c.post(f"/api/projects/{api_pid}/functions", headers=HJ,
                      json={"name": "数据存储", "category": "ILF",
                            "complexity": "high", "ufp": 15.0, "us": 15.0})

        out_p10 = generate_excel(db_session, api_pid, band="P10")
        bytes_p10 = Path(out_p10).read_bytes()

        out_p90 = generate_excel(db_session, api_pid, band="P90")
        bytes_p90 = Path(out_p90).read_bytes()

    assert len(bytes_p10) > 0
    assert len(bytes_p90) > 0
    assert bytes_p10 != bytes_p90, (
        "generate_excel(band='P10') and generate_excel(band='P90') "
        "must produce different xlsx content"
    )
