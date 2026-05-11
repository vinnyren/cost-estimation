const { useState, useEffect, useMemo, useRef, Fragment } = React;
const { Icon, Badge, Chip, Button, ModeBadge, PhaseBadge, CategoryChip, SourceBadge, fmtMoney, fmtWan, fmtFp, StatusPill } = window;

// === Project List ===

function ProjectList({ onOpen, onNew }) {
  const projects = window.AppData.PROJECTS;
  const [filter, setFilter] = useState("全部");
  const [view, setView] = useState("table");

  const stats = useMemo(() => {
    const total = projects.length;
    const draft = projects.filter(p => p.status === "草稿").length;
    const inProgress = projects.filter(p => p.status === "计算中" || p.status === "已计算").length;
    const archived = projects.filter(p => p.status === "已归档").length;
    return [
      ["全部", total, "folder"],
      ["草稿", draft, "edit"],
      ["计算中", inProgress, "refresh"],
      ["已归档", archived, "archive"],
    ];
  }, [projects]);

  const filtered = filter === "全部" ? projects : projects.filter(p => p.status === filter);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">项目工作台</div>
          <div className="page-sub">软件造价咨询项目 · 基于 GB/T 36964-2018 + CSBMK®-202510</div>
        </div>
        <div className="page-spacer" />
        <Button variant="ghost" icon="upload">导入</Button>
        <Button variant="ghost" icon="download">批量导出</Button>
        <Button variant="primary" icon="plus" onClick={onNew}>新建项目</Button>
      </div>

      <div className="kpi-row">
        {stats.map(([name, val, ico]) => (
          <div key={name} className={`kpi-card ${filter === name ? "active" : ""}`} onClick={() => setFilter(name)}>
            <div className="kpi-icon"><Icon name={ico} size={16} /></div>
            <div>
              <div className="kpi-label">{name}</div>
              <div className="kpi-val mono">{val}</div>
            </div>
          </div>
        ))}
        <div className="kpi-card kpi-summary">
          <div>
            <div className="kpi-label">本月总造价（P50）</div>
            <div className="kpi-val mono">¥4,287<span className="kpi-unit">万</span></div>
          </div>
          <div className="kpi-trend up"><Icon name="trending" size={12} /> +18.4%</div>
        </div>
      </div>

      <div className="toolbar">
        <input type="text" placeholder="搜索项目名 / 编码 / 客户..." style={{ flex: 1, maxWidth: 280 }} />
        <Button size="sm" variant="ghost" icon="filter">城市</Button>
        <Button size="sm" variant="ghost" icon="filter">行业</Button>
        <Button size="sm" variant="ghost" icon="filter">阶段</Button>
        <div style={{ flex: 1 }} />
        <div className="seg">
          <button className={view === "table" ? "active" : ""} onClick={() => setView("table")}><Icon name="grid" size={13} /></button>
          <button className={view === "card" ? "active" : ""} onClick={() => setView("card")}><Icon name="layers" size={13} /></button>
        </div>
        <span className="muted" style={{ fontSize: 12 }}>{filtered.length} / {projects.length}</span>
      </div>

      {view === "table" && (
        <div className="card" style={{ padding: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 26 }}><input type="checkbox" /></th>
                <th>项目名 / 编码</th>
                <th style={{ width: 80 }}>模式</th>
                <th>客户 · 城市 · 行业</th>
                <th>阶段</th>
                <th style={{ textAlign: "right" }}>规模 (FP)</th>
                <th style={{ textAlign: "right", width: 140 }}>P50 造价</th>
                <th style={{ width: 90 }}>状态</th>
                <th style={{ width: 110 }}>更新时间</th>
                <th style={{ width: 36 }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} className="row-link" onClick={() => onOpen(p)}>
                  <td onClick={(e) => e.stopPropagation()}><input type="checkbox" /></td>
                  <td>
                    <div style={{ fontWeight: 500 }}>{p.name}</div>
                    <div className="muted mono" style={{ fontSize: 11 }}>{p.code}</div>
                  </td>
                  <td><ModeBadge mode={p.mode} /></td>
                  <td>
                    <div style={{ fontSize: 12 }}>{p.customer}</div>
                    <div className="muted" style={{ fontSize: 11 }}>{p.city} · {p.industry}</div>
                  </td>
                  <td><PhaseBadge phase={p.phase} /></td>
                  <td className="mono" style={{ textAlign: "right" }}>{p.fp || "—"}</td>
                  <td className="mono" style={{ textAlign: "right", fontWeight: 500 }}>
                    {p.p50 ? `¥${(p.p50/10000).toFixed(2)}万` : <span className="muted">—</span>}
                  </td>
                  <td><StatusPill status={p.status} /></td>
                  <td className="muted mono" style={{ fontSize: 11 }}>{p.updated}</td>
                  <td onClick={(e) => e.stopPropagation()}><Button size="sm" variant="ghost" icon="more" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {view === "card" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
          {filtered.map(p => (
            <div key={p.id} className="card row-link" style={{ padding: 18 }} onClick={() => onOpen(p)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</div>
                  <div className="muted mono" style={{ fontSize: 11 }}>{p.code}</div>
                </div>
                <ModeBadge mode={p.mode} />
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
                <Chip>{p.city}</Chip><Chip>{p.industry}</Chip><PhaseBadge phase={p.phase} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                <div>
                  <div className="muted" style={{ fontSize: 11 }}>规模</div>
                  <div className="mono">{p.fp || "—"} FP</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="muted" style={{ fontSize: 11 }}>P50 造价</div>
                  <div className="mono" style={{ fontWeight: 600, color: "var(--accent)" }}>
                    {p.p50 ? `¥${(p.p50/10000).toFixed(1)}万` : "—"}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

window.ProjectList = ProjectList;
