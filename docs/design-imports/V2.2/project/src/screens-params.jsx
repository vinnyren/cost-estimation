const { useState, useEffect, useMemo, useRef, Fragment } = React;
const { Icon, Badge, Chip, Button, ModeBadge, PhaseBadge, CategoryChip, SourceBadge, fmtMoney, fmtWan, fmtFp, StatusPill } = window;

// === Parameter Manager — 6 tabs ===

function ParamManager({ project, onBack }) {
  const [tab, setTab] = useState("rate");
  const TABS = [
    ["rate", "费率", "37 城 × 开发/运维"],
    ["productivity", "生产率", "7 行业 × P10/P50/P90"],
    ["factors_dev", "开发因子", "5 项"],
    ["factors_ops", "运维因子", "11 项"],
    ["scale_change", "规模变更", "5 项"],
    ["snapshots", "快照", "3 个"],
  ];
  return (
    <div className="page">
      <div className="page-header">
        <Button variant="ghost" icon="chevronLeft" onClick={onBack}>返回 FP 编辑</Button>
        <div style={{ marginLeft: 8 }}>
          <div className="page-title tight">参数管理 · {project.name}</div>
          <div className="page-sub">项目级覆盖优先于全局参数 · 当前数据基准 CSBMK®-202510</div>
        </div>
        <div className="page-spacer" />
        <Button variant="ghost" icon="refresh">恢复默认</Button>
        <Button variant="primary" icon="download">导出参数表</Button>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div className="tabs" style={{ padding: "0 12px", marginBottom: 0 }}>
          {TABS.map(([k, name, sub]) => (
            <div key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>
              {name}<span className="count">{sub}</span>
            </div>
          ))}
        </div>
        <div style={{ padding: 16 }}>
          {tab === "rate" && <TabRate />}
          {tab === "productivity" && <TabProductivity />}
          {tab === "factors_dev" && <TabFactorsDev />}
          {tab === "factors_ops" && <TabFactorsOps />}
          {tab === "scale_change" && <TabScaleChange />}
          {tab === "snapshots" && <TabSnapshots />}
        </div>
      </div>
    </div>
  );
}

function OverrideTag() {
  return <span className="badge badge-amber" style={{ marginLeft: 6 }}>自定义</span>;
}

function TabRate() {
  const cities = window.AppData.CITIES;
  const overridden = ["北京"];
  return (
    <div>
      <div style={{ display: "flex", gap: 16, marginBottom: 12, alignItems: "center" }}>
        <div className="muted" style={{ fontSize: 12 }}>城市分级</div>
        {["A","B","C","D","E"].map(d => <Chip key={d}>{d} 档</Chip>)}
        <div style={{ flex: 1 }} />
        <span className="muted" style={{ fontSize: 12 }}>{cities.length} 城市</span>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>城市</th>
            <th style={{ width: 80 }}>档位</th>
            <th style={{ width: 200, textAlign: "right" }}>开发费率 (元/人月)</th>
            <th style={{ width: 200, textAlign: "right" }}>运维费率 (元/人月)</th>
            <th style={{ width: 60 }}></th>
          </tr>
        </thead>
        <tbody>
          {cities.map(([name, tier, dev, ops]) => {
            const o = overridden.includes(name);
            return (
              <tr key={name} className={o ? "override-row" : ""}>
                <td><b>{name}</b></td>
                <td><Badge tone={tier === "A" ? "blue" : tier === "B" ? "teal" : "default"}>{tier}</Badge></td>
                <td className={"mono" + (o ? " override-cell" : "")} style={{ textAlign: "right" }}>
                  {o && <span style={{ color: "var(--text-3)", textDecoration: "line-through", marginRight: 8 }}>{(dev-1000).toLocaleString()}</span>}
                  {dev.toLocaleString()}
                  {o && <OverrideTag />}
                </td>
                <td className="mono" style={{ textAlign: "right" }}>{ops.toLocaleString()}</td>
                <td>{o && <Button size="sm" variant="ghost" icon="refresh" title="恢复默认" />}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TabProductivity() {
  const inds = window.AppData.INDUSTRIES;
  return (
    <div>
      <div className="banner banner-blue" style={{ marginBottom: 12 }}>
        <Icon name="info" size={14} />
        <div>PDR 三档来自 CSBMK®-202510 行业分布；调整 P10/P90 会显著改变 P10/P90 造价区间</div>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>行业</th>
            <th style={{ textAlign: "right" }}>P10 (乐观)</th>
            <th style={{ textAlign: "right" }}>P50 (推荐)</th>
            <th style={{ textAlign: "right" }}>P90 (保守)</th>
            <th style={{ textAlign: "right" }}>运维 P50</th>
            <th>分布</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(inds).map(([k, v]) => (
            <tr key={k}>
              <td><b>{k}</b></td>
              <td className="mono" style={{ textAlign: "right" }}>{v.devP10}</td>
              <td className="mono" style={{ textAlign: "right", color: "var(--accent)", fontWeight: 600 }}>{v.devP50}</td>
              <td className="mono" style={{ textAlign: "right" }}>{v.devP90}</td>
              <td className="mono muted" style={{ textAlign: "right" }}>{v.opsP50}</td>
              <td>
                <div className="sparkbar">
                  {[v.devP10, v.devP50*1.4, v.devP50, v.devP50*0.7, v.devP90].map((h, i) => (
                    <i key={i} style={{ height: `${Math.min(h*2, 16)}px` }} />
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TabFactorsDev() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      {window.AppData.DEV_FACTORS.map(f => (
        <div key={f.key} className="card" style={{ padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <div style={{ fontWeight: 600 }}>{f.label}</div>
            <span className="mono muted">{f.key}</span>
          </div>
          <table className="table" style={{ background: "transparent" }}>
            <tbody>
              {f.options.map(([n, v]) => (
                <tr key={n}>
                  <td>{n.replace(/\s*\([^)]+\)\s*/, "")}</td>
                  <td className="mono" style={{ textAlign: "right", width: 80 }}>×{v.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function TabFactorsOps() {
  return (
    <div>
      <div className="banner banner-blue" style={{ marginBottom: 12 }}>
        <Icon name="info" size={14} />
        <div>当前项目运维因子乘积 = <b className="mono">1.18</b> · 政务服务平台案例（GB/T 28827.7-2022 §6.1）</div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
        {window.AppData.OPS_FACTORS.map(f => (
          <div key={f.key} className="card" style={{ padding: "12px 16px", display: "flex", alignItems: "center" }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500 }}>{f.label}</div>
              <div className="muted mono" style={{ fontSize: 11 }}>{f.key}</div>
            </div>
            <div className="mono" style={{ fontWeight: 600, fontSize: 16, color: f.value !== 1.00 ? "var(--accent)" : "var(--text)" }}>×{f.value.toFixed(2)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TabScaleChange() {
  const rows = [
    ["新增", 1.00, "scale_change.add", "全新功能点（默认）"],
    ["修改", 0.70, "scale_change.modify", "对现有功能点修改"],
    ["删除", 0.40, "scale_change.delete", "删除既有功能"],
    ["转换", 0.60, "scale_change.convert", "技术栈迁移/转换"],
    ["变更率门槛", 0.05, "scale_change.threshold", "<5% 不计入规模"],
  ];
  return (
    <table className="table">
      <thead><tr><th>变更类型</th><th>键</th><th>说明</th><th style={{ textAlign: "right", width: 120 }}>系数</th></tr></thead>
      <tbody>
        {rows.map(([name, v, k, d], i) => (
          <tr key={i}><td><b>{name}</b></td><td className="mono muted">{k}</td><td className="muted">{d}</td>
            <td className="mono" style={{ textAlign: "right", fontWeight: 600 }}>{v.toFixed(2)}</td></tr>
        ))}
      </tbody>
    </table>
  );
}

function TabSnapshots() {
  const snaps = [
    { id: "s12", note: "投标版-2026Q2", time: "2026-05-11 14:25", current: true, fields: 8 },
    { id: "s11", note: "立项基线", time: "2026-04-25 10:08", current: false, fields: 5 },
    { id: "s10", note: "默认 CSBMK 202510", time: "2026-04-22 16:08", current: false, fields: 0 },
  ];
  return (
    <div>
      <div className="toolbar" style={{ marginBottom: 12 }}>
        <input type="text" placeholder="快照备注..." defaultValue="投标版-2026Q3" style={{ flex: 1, maxWidth: 320 }} />
        <Button variant="primary" icon="plus" size="sm">立即快照</Button>
        <div style={{ flex: 1 }} />
        <span className="muted" style={{ fontSize: 12 }}>{snaps.length} 个快照</span>
      </div>
      <table className="table">
        <thead><tr><th style={{ width: 80 }}>ID</th><th>备注</th><th style={{ width: 160 }}>时间</th><th style={{ width: 120 }}>覆盖字段</th><th style={{ width: 180 }}>操作</th></tr></thead>
        <tbody>
          {snaps.map(s => (
            <tr key={s.id}>
              <td className="mono"><b>{s.id}</b></td>
              <td>{s.note} {s.current && <Badge tone="green">当前</Badge>}</td>
              <td className="mono muted">{s.time}</td>
              <td className="mono">{s.fields} 项</td>
              <td>
                <Button size="sm" variant="ghost" icon="refresh">恢复</Button>
                <Button size="sm" variant="ghost" icon="download">导出</Button>
                {!s.current && <Button size="sm" variant="ghost" icon="trash" />}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

window.ParamManager = ParamManager;
