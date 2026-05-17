from io import BytesIO

from openpyxl import load_workbook

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _make_project_with_fp(c) -> str:
    rp = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    pid = rp.json()["data"]["id"]
    await c.post(f"/api/projects/{pid}/functions",
                 headers={**H, "Content-Type": "application/json"},
                 json={"name": "首页", "category": "EQ", "complexity": "low",
                       "ufp": 4.0, "us": 4.0})
    return pid


async def test_download_excel(client_factory, tmp_data_dir):
    async with await client_factory() as c:
        pid = await _make_project_with_fp(c)
        r = await c.get(f"/api/reports/excel/{pid}", headers=H)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
        wb = load_workbook(BytesIO(r.content))
        # 必备 7 Sheet
        for s in ["封面声明", "评估结果摘要", "评估报告书", "调整因子表",
                  "功能点计数表", "详细计算过程", "参数附录"]:
            assert s in wb.sheetnames
        # 摘要值
        summary = wb["评估结果摘要"]
        # us=4 * cf=1.21 = 4.84
        assert summary["C2"].value == 4.84


async def test_reverse_report_total_matches_target(client_factory, tmp_data_dir):
    """反算项目的报告：总费用应复现目标造价（口径与结果页一致）。"""
    async with await client_factory() as c:
        rp = await c.post("/api/projects", headers=H, json={
            "name": "反算项目", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "reverse",
            "target_cost": 88.0,  # 万元
            "basis_data_ver": "CSBMK®-202510",
        })
        pid = rp.json()["data"]["id"]
        # 反算不依赖 FP 数值，但报告仍要求项目有 FP（FP 表作参考设计）
        await c.post(f"/api/projects/{pid}/functions",
                     headers={**H, "Content-Type": "application/json"},
                     json={"name": "首页", "category": "EQ", "complexity": "low",
                           "ufp": 4.0, "us": 4.0})
        r = await c.get(f"/api/reports/excel/{pid}", headers=H)
        assert r.status_code == 200
        wb = load_workbook(BytesIO(r.content))
        summary = wb["评估结果摘要"]
        # 摘要表 C 列里应出现总费用 ≈ 88 万元（反算口径下 forward 复现目标）
        c_vals = [summary.cell(row=row, column=3).value
                  for row in range(1, summary.max_row + 1)]
        nums = [v for v in c_vals if isinstance(v, (int, float))]
        assert any(abs(v - 88.0) < 0.5 for v in nums), \
            f"总费用应 ≈ 88 万元，摘要 C 列实际为 {nums}"


async def test_download_no_fp_returns_400(client_factory, tmp_data_dir):
    async with await client_factory() as c:
        pid = await _make_project_with_fp(c)
        # 删掉刚加的 FP
        fps_r = await c.get(f"/api/projects/{pid}/functions", headers=H)
        fp_id = fps_r.json()["data"][0]["id"]
        await c.delete(f"/api/projects/{pid}/functions/{fp_id}", headers=H)
        r = await c.get(f"/api/reports/excel/{pid}", headers=H)
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "FP_EMPTY"
