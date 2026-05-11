const { useState, useEffect, useMemo, useRef, Fragment } = React;
const { Icon, Badge, Chip, Button, ModeBadge, PhaseBadge, CategoryChip, SourceBadge, fmtMoney, fmtWan, fmtFp, StatusPill } = window;

// === Audit Log Timeline ===

function AuditPage({ onBack }) {
  const events = [
    { type: "user", action: "create_snapshot", who: "李工程师", t: "2026-05-11 14:25:08", title: "创建快照 投标版-2026Q2", desc: "覆盖 8 个项目级字段：rates_dev:beijing, ops_factors[3].user_scale, ...", id: "evt_241" },
    { type: "calc", action: "calculate", who: "系统", t: "2026-05-11 14:24:51", title: "重新计算 P50 造价", desc: "489,180 元（前次 478,400）·  Δ +10,780 元 · 触发：参数变更 user_scale 1.00→1.10", id: "evt_240" },
    { type: "user", action: "override", who: "李工程师", t: "2026-05-11 14:23:30", title: "覆盖 ops_factors.user_scale", desc: "1.00 → 1.10（项目级覆盖 · 大型政务用户量级）", id: "evt_239" },
    { type: "ai", action: "ai_extract", who: "Claude AI", t: "2026-05-11 13:45:12", title: "AI 提取需求文档 → 87 条 FP", desc: "源：政务服务平台-需求规格说明书.docx 1.8 MB · EI:14 EO:5 EQ:7 ILF:5 EIF:0 · 用户采纳 87 / 92", id: "evt_238" },
    { type: "user", action: "upload", who: "李工程师", t: "2026-05-11 13:43:50", title: "上传文档", desc: "政务服务平台-需求规格说明书.docx · MD5 8a3f2c...e91d", id: "evt_237" },
    { type: "calc", action: "calculate", who: "系统", t: "2026-05-11 13:30:01", title: "首次三档造价计算", desc: "P10: 415,200 · P50: 478,400 · P90: 564,800", id: "evt_236" },
    { type: "system", action: "snapshot_baseline", who: "系统", t: "2026-04-25 10:08:00", title: "建立立项基线快照", desc: "覆盖 5 项参数 · 用于后续对比", id: "evt_220" },
    { type: "user", action: "create_project", who: "李工程师", t: "2026-04-22 16:08:11", title: "创建项目 政务服务平台", desc: "城市：北京 · 行业：电子政务 · 阶段：招投标 · 模式：正向", id: "evt_201" },
  ];

  const iconForType = { user: "user", calc: "refresh", ai: "sparkles", system: "settings" };
  const colorForType = { user: "var(--accent)", calc: "var(--text-2)", ai: "#7C3AED", system: "var(--text-3)" };

  return (
    <div className="page">
      <div className="page-header">
        <Button variant="ghost" icon="chevronLeft" onClick={onBack}>返回结果页</Button>
        <div style={{ marginLeft: 8 }}>
          <div className="page-title tight">审计日志 · 政务服务平台</div>
          <div className="page-sub">{events.length} 条事件 · 不可变 append-only · 支持事件溯源</div>
        </div>
        <div className="page-spacer" />
        <div className="toolbar" style={{ gap: 6, padding: 0, background: "transparent" }}>
          <input type="text" placeholder="搜索动作 / 字段..." style={{ width: 220 }} />
          <Button variant="ghost" icon="filter" size="sm">类型</Button>
        </div>
        <Button variant="ghost" icon="download">导出 CSV</Button>
      </div>

      <div className="card" style={{ padding: "20px 24px" }}>
        <div className="timeline">
          {events.map((e, i) => (
            <div key={e.id} className="tl-item">
              <div className="tl-dot" style={{ background: colorForType[e.type] }}>
                <Icon name={iconForType[e.type]} size={11} />
              </div>
              {i < events.length - 1 && <div className="tl-line" />}
              <div className="tl-body">
                <div className="tl-head">
                  <span className="tl-title">{e.title}</span>
                  <span className="tl-time mono">{e.t}</span>
                </div>
                <div className="tl-meta">
                  <Badge tone={e.type === "ai" ? "violet" : e.type === "calc" ? "blue" : "default"}>{e.action}</Badge>
                  <span className="muted">{e.who}</span>
                  <span className="muted mono" style={{ fontSize: 11 }}>{e.id}</span>
                </div>
                <div className="tl-desc">{e.desc}</div>
                {e.action === "calculate" && (
                  <div className="tl-attach">
                    <Icon name="file" size={12} />
                    <span className="mono">snapshot_pre.json</span>
                    <span className="muted">vs</span>
                    <span className="mono">snapshot_post.json</span>
                    <div className="spacer" />
                    <Button size="sm" variant="ghost">查看差异</Button>
                  </div>
                )}
                {e.action === "ai_extract" && (
                  <div className="tl-attach">
                    <Icon name="sparkles" size={12} style={{ color: "#7C3AED" }} />
                    <span>耗时 38.2s · token 22,418</span>
                    <div className="spacer" />
                    <Button size="sm" variant="ghost">查看 AI 痕迹</Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

window.AuditPage = AuditPage;
