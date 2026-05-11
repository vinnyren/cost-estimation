const { useState, useEffect, useMemo, useRef, Fragment } = React;
const { Icon, Badge, Chip, Button, ModeBadge, PhaseBadge, CategoryChip, SourceBadge, fmtMoney, fmtWan, fmtFp, StatusPill } = window;

// === FP Editor ===

function FpEditor({ project, onCalculate, onParams }) {
  const fps = window.AppData.FUNCTION_POINTS;
  const [activeNode, setActiveNode] = useState("all");
  const [expanded, setExpanded] = useState(() => new Set(["受理子系统","审批子系统","监督子系统","用户子系统","报表子系统","接口子系统"]));
  const [showAi, setShowAi] = useState(false);

  // build module tree
  const tree = useMemo(() => {
    const map = {};
    fps.forEach(f => {
      if (!map[f.sub]) map[f.sub] = { name: f.sub, total: 0, count: 0, l1: {} };
      map[f.sub].count++;
      map[f.sub].total += f.ufp;
      if (!map[f.sub].l1[f.l1]) map[f.sub].l1[f.l1] = { name: f.l1, count: 0, total: 0 };
      map[f.sub].l1[f.l1].count++;
      map[f.sub].l1[f.l1].total += f.ufp;
    });
    return map;
  }, [fps]);

  const filtered = useMemo(() => {
    if (activeNode === "all") return fps;
    const [type, ...rest] = activeNode.split("::");
    if (type === "sub") return fps.filter(f => f.sub === rest[0]);
    if (type === "l1") return fps.filter(f => f.sub === rest[0] && f.l1 === rest[1]);
    return fps;
  }, [activeNode, fps]);

  const totalUfp = fps.reduce((a,f) => a + f.ufp, 0);
  const totalUs = fps.reduce((a,f) => a + f.ufp * (1 - f.reuse*0.5 - f.modify*0.25), 0);
  const cf = window.AppData.PHASES[project.phase].cf;
  const adjusted = totalUs * cf;

  function toggle(name) {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  }

  return (
    <div className="page" style={{ paddingTop: 16, paddingBottom: 0, height: "calc(100vh - 56px)", display: "flex", flexDirection: "column", maxWidth: "none" }}>
      <div className="page-header" style={{ marginBottom: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div className="page-title tight">{project.name}</div>
            <ModeBadge mode={project.mode} />
            <Chip>{project.city}</Chip>
            <Chip>{project.industry}</Chip>
            <PhaseBadge phase={project.phase} />
          </div>
          <div className="page-sub">{project.code} · 客户：{project.customer} · 数据基准 CSBMK®-202510</div>
        </div>
        <div className="page-spacer" />
        <Button icon="upload" variant="ghost">上传文档</Button>
        <Button icon="sparkles" variant="ghost" onClick={() => setShowAi(true)}>AI 提取</Button>
        <Button icon="settings" variant="ghost" onClick={onParams}>参数管理</Button>
        <Button variant="primary" iconRight="chevronRight" onClick={onCalculate}>计算 → 结果</Button>
      </div>

      <div className="banner banner-amber" style={{ marginBottom: 12 }}>
        <Icon name="info" size={16} />
        <div>参数已变更（运维因子 user_scale: 1.00 → 1.10），需要重新计算才能更新三档造价</div>
        <div className="spacer" />
        <Button size="sm" icon="refresh">重新计算</Button>
      </div>

      <div className="fp-layout" style={{ flex: 1, height: "auto" }}>
        {/* Tree */}
        <div className="module-tree">
          <div className="tree-head">
            <div className="label">模块树</div>
            <span className="mono muted" style={{ fontSize: 11 }}>{fps.length} 行</span>
          </div>
          <div className={`tree-node ${activeNode === "all" ? "active" : ""}`} onClick={() => setActiveNode("all")}>
            <Icon name="layers" size={13} />
            <span>全部模块</span>
            <span className="tree-count">{fps.length}</span>
          </div>
          {Object.values(tree).map(sub => (
            <div key={sub.name}>
              <div className={`tree-node ${activeNode === `sub::${sub.name}` ? "active" : ""}`} onClick={() => { setActiveNode(`sub::${sub.name}`); toggle(sub.name); }}>
                <Icon name={expanded.has(sub.name) ? "chevronDown" : "chevronRight"} size={11} style={{ color: "var(--text-3)" }} />
                <Icon name="folder" size={13} />
                <span>{sub.name}</span>
                <span className="tree-count">{sub.count}</span>
              </div>
              {expanded.has(sub.name) && Object.values(sub.l1).map(l1 => (
                <div key={l1.name} className={`tree-node l2 ${activeNode === `l1::${sub.name}::${l1.name}` ? "active" : ""}`} onClick={() => setActiveNode(`l1::${sub.name}::${l1.name}`)}>
                  <span>{l1.name}</span>
                  <span className="tree-count">{l1.count}</span>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Main */}
        <div className="fp-main">
          <div className="fp-main-head">
            <Button size="sm" variant="ghost" icon="plus">新增功能点</Button>
            <Button size="sm" variant="ghost" icon="download">导出 Excel</Button>
            <div className="fp-stats">
              <div><span className="fp-stat-label">总 UFP</span><span className="fp-stat-val mono">{totalUfp}</span></div>
              <div><span className="fp-stat-label">US</span><span className="fp-stat-val mono">{totalUs.toFixed(2)}</span></div>
              <div><span className="fp-stat-label">× CF {cf}</span></div>
              <div><span className="fp-stat-label">S (调整后)</span><span className="fp-stat-val mono" style={{ color: "var(--accent)" }}>{adjusted.toFixed(2)} FP</span></div>
            </div>
            <div style={{ flex: 1 }} />
            <span className="muted" style={{ fontSize: 11 }}>{filtered.length} / {fps.length} 行</span>
          </div>
          <div className="fp-table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 36 }}>#</th>
                  <th>子系统 / 模块</th>
                  <th>二级模块</th>
                  <th style={{ width: 60 }}>类别</th>
                  <th style={{ width: 70, textAlign: "right" }}>UFP</th>
                  <th style={{ width: 60, textAlign: "right" }}>重用</th>
                  <th style={{ width: 60, textAlign: "right" }}>修改</th>
                  <th style={{ width: 80, textAlign: "right" }}>US</th>
                  <th style={{ width: 110 }}>来源</th>
                  <th style={{ width: 36 }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((f, i) => {
                  const us = f.ufp * (1 - f.reuse*0.5 - f.modify*0.25);
                  const cls = [
                    f.source === "allocator" && "row-allocator",
                    f.source === "claude_draft" && "row-draft",
                    f.locked && "row-locked",
                  ].filter(Boolean).join(" ");
                  return (
                    <tr key={f.id} className={cls}>
                      <td className="mono muted">{String(i+1).padStart(2,"0")}</td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          {f.locked && <Icon name="lock" size={12} style={{ color: "var(--text-3)" }} />}
                          <span style={{ color: "var(--text-3)" }}>{f.sub} / </span>
                          <span>{f.l1}</span>
                        </div>
                      </td>
                      <td>{f.l2}</td>
                      <td><CategoryChip cat={f.cat} /></td>
                      <td className="mono" style={{ textAlign: "right" }}>{f.ufp}</td>
                      <td className="mono muted" style={{ textAlign: "right" }}>{f.reuse > 0 ? f.reuse.toFixed(2) : "—"}</td>
                      <td className="mono muted" style={{ textAlign: "right" }}>{f.modify > 0 ? f.modify.toFixed(2) : "—"}</td>
                      <td className="mono" style={{ textAlign: "right", fontWeight: 500 }}>{us.toFixed(2)}</td>
                      <td><SourceBadge source={f.source} /></td>
                      <td><Button size="sm" variant="ghost" icon="more" /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showAi && <AiExtractModal onClose={() => setShowAi(false)} />}
    </div>
  );
}

function AiExtractModal({ onClose }) {
  const [phase, setPhase] = useState("running"); // running | done
  const [progress, setProgress] = useState(48);
  useEffect(() => {
    const t = setInterval(() => setProgress(p => {
      if (p >= 87) { setPhase("done"); clearInterval(t); return 87; }
      return p + 3;
    }), 350);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.45)", display: "grid", placeItems: "center", zIndex: 1000 }}>
      <div className="card" style={{ width: 540, padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #2563EB, #7C3AED)", display: "grid", placeItems: "center", color: "white" }}>
            <Icon name="sparkles" size={20} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>Claude 正在解析需求文档</div>
            <div className="muted" style={{ fontSize: 12 }}>政务服务平台-需求规格说明书.docx · 1.8 MB · NESMA 5 类识别</div>
          </div>
          <div style={{ flex: 1 }} />
          <Button variant="ghost" size="sm" onClick={onClose}>取消</Button>
        </div>

        <div style={{ marginTop: 20, padding: 14, background: "var(--surface-sunken)", borderRadius: 8, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-2)" }}>
          <div>▸ <span style={{ color: "var(--green)" }}>✓</span> 文档解析 · 32 页 · 18,420 字</div>
          <div>▸ <span style={{ color: "var(--green)" }}>✓</span> 章节切分 · 识别 6 个子系统</div>
          <div>▸ <span style={{ color: "var(--green)" }}>✓</span> 类别归类 · EI:14 · EO:5 · EQ:7 · ILF:5 · EIF:0</div>
          <div>▸ <span style={{ color: phase === "done" ? "var(--green)" : "var(--accent)" }}>{phase === "done" ? "✓" : "●"}</span> 写入 FP 表 · {progress} / 87 行</div>
          {phase === "done" && <div>▸ <span style={{ color: "var(--green)" }}>✓</span> 完成 · 耗时 38.2s</div>}
        </div>

        <div style={{ marginTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
            <span className="muted">进度</span>
            <span className="mono">{Math.round(progress/87*100)}%</span>
          </div>
          <div style={{ height: 6, background: "var(--surface-sunken)", borderRadius: 3, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${progress/87*100}%`, background: "linear-gradient(90deg, var(--accent), #7C3AED)", transition: "width .3s" }} />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 20 }}>
          <Button variant="ghost" onClick={onClose}>{phase === "done" ? "查看结果" : "后台运行"}</Button>
          {phase === "done" && <Button variant="primary" onClick={onClose}>采纳 87 条 FP</Button>}
        </div>
      </div>
    </div>
  );
}

window.FpEditor = FpEditor;
