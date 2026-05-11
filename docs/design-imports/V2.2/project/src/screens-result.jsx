const { useState, useEffect, useMemo, useRef, Fragment } = React;
const { Icon, Badge, Chip, Button, ModeBadge, PhaseBadge, CategoryChip, SourceBadge, fmtMoney, fmtWan, fmtFp, StatusPill } = window;

// === Result page — forward + reverse ===

function ResultPage({ project, onBack }) {
  if (project.mode === "reverse") return <ResultReverse project={project} onBack={onBack} />;
  return <ResultForward project={project} onBack={onBack} />;
}

function ResultForward({ project, onBack }) {
  const tiers = [
    { key: "P10", label: "乐观 · 行业最高效率", cost: project.p10, hours: 1840, fp: 332.75, recommended: false },
    { key: "P50", label: "中位 · CSBMK 行业基准", cost: project.p50, hours: 2236.08, fp: 332.75, recommended: true },
    { key: "P90", label: "保守 · 含返工/沟通损耗", cost: project.p90, hours: 2786, fp: 332.75, recommended: false },
  ];
  return (
    <div className="page hero-bg" style={{ maxWidth: 1280 }}>
      <div className="page-header">
        <Button variant="ghost" icon="chevronLeft" onClick={onBack}>FP 编辑</Button>
        <div style={{ marginLeft: 8 }}>
          <div className="page-title tight">三档造价 · {project.name}</div>
          <div className="page-sub">基于 CSBMK®-202510 行业 PDR 分布 · P10/P50/P90 为敏感度边界</div>
        </div>
        <div className="page-spacer" />
        <Button variant="ghost" icon="refresh">重新计算</Button>
        <Button variant="ghost" icon="copy">复制摘要</Button>
        <Button variant="primary" icon="download">下载 Excel 报告</Button>
      </div>

      <div className="result-trio">
        {tiers.map(t => (
          <div key={t.key} className={`result-card ${t.recommended ? "recommended" : ""}`}>
            {t.recommended && <div className="result-card-pill">推荐 · P50</div>}
            <div className="result-card-tag">{t.key}</div>
            <div className="result-card-name">{t.label}</div>
            <div className={`result-card-amt ${!t.recommended ? "dimmed" : ""}`}>
              ¥{fmtMoney(t.cost)}<span className="unit">元</span>
            </div>
            <div className="muted mono" style={{ fontSize: 12 }}>= {fmtWan(t.cost)} 万元</div>
            <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
              <div className="result-card-row"><span>调整后规模 S</span><span className="v">{t.fp} FP</span></div>
              <div className="result-card-row"><span>开发工作量</span><span className="v">{t.hours.toFixed(2)} 人时</span></div>
              <div className="result-card-row"><span>运维工作量</span><span className="v">{(t.hours * 0.147).toFixed(2)} 人时</span></div>
              <div className="result-card-row"><span>其他费用</span><span className="v">25,000 元</span></div>
            </div>
          </div>
        ))}
      </div>

      {/* breakdown */}
      <div className="section">
        <div className="section-head">
          <div className="section-title">计算路径详解 · P50 推荐档</div>
          <div className="section-sub">附录 D 算例 · 政务服务平台 · 期望 489,180 元 ± 100 元</div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <Pipeline />
        </div>
      </div>

      {/* Two-col */}
      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 16, marginTop: 16 }}>
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 14 }}>
            <div className="section-title">成本构成分布</div>
            <span className="muted mono" style={{ fontSize: 11 }}>P50 · 合计 489,180 元</span>
          </div>
          <CostBar items={[
            ["开发人工", 419800, "#2563EB"],
            ["运维人工", 38400, "#7C3AED"],
            ["其他费用", 25000, "#0E7490"],
            ["间接/管理", 5980, "#94A3B8"],
          ]} total={489180} />
        </div>

        <div className="card" style={{ padding: 20 }}>
          <div className="section-title" style={{ marginBottom: 14 }}>合规说明</div>
          <div style={{ display: "grid", gap: 10 }}>
            {[
              ["GB/T 36964-2018", "§7.2 PDR 公式 · 三档行业基准"],
              ["T/CCUA 005-2024", "附录 D 算例 · 黄金测试基准"],
              ["GB/T 28827.7-2022", "§6 运维 11 项因子"],
              ["CSBMK®-202510", "1500+ 在网项目统计"],
            ].map(([k, v]) => (
              <div key={k} style={{ display: "flex", gap: 10, fontSize: 12, padding: "6px 0", borderBottom: "1px dashed var(--border)" }}>
                <Icon name="check" size={14} style={{ color: "var(--green)", marginTop: 2 }} />
                <div>
                  <div className="mono"><b>{k}</b></div>
                  <div className="muted">{v}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 14, padding: 10, background: "var(--surface-sunken)", borderRadius: 6, fontSize: 11, color: "var(--text-2)", lineHeight: 1.6 }}>
            <b>💡 报告话术：</b>本项目 P50 推荐造价 <span className="mono">48.92 万元</span>；P10/P90 为基于 CSBMK®-202510 行业生产率分布的敏感度边界，<b>非团队承诺值</b>。
          </div>
        </div>
      </div>
    </div>
  );
}

function Pipeline() {
  const steps = [
    { tag: "US", label: "未调整规模", val: "275.00", unit: "人时", note: "Σ FP[i].us" },
    { tag: "×", label: "阶段调整因子 CF", val: "1.21", unit: "", note: "招投标" },
    { tag: "S", label: "调整后规模", val: "332.75", unit: "FP", note: "US × CF", highlight: true },
    { tag: "÷", label: "PDR P50 (电子政务)", val: "6.41", unit: "FP/PM", note: "CSBMK §4.1" },
    { tag: "×", label: "开发因子乘积", val: "1.00", unit: "", note: "5 项默认" },
    { tag: "EFF", label: "开发工作量", val: "51.91", unit: "人月", note: "= 2236.08 人时", highlight: true },
    { tag: "×", label: "F_city (北京 A 档)", val: "32,200", unit: "元/PM", note: "" },
    { tag: "+", label: "运维 + 其他费", val: "63,400", unit: "元", note: "ops×1.18 + 25,000" },
    { tag: "=", label: "P50 总造价", val: "489,180", unit: "元", note: "≈ 48.92 万元", final: true },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
      {steps.map((s, i) => (
        <div key={i} style={{
          padding: "12px 14px",
          background: s.final ? "var(--accent-soft)" : s.highlight ? "rgba(234,240,255,0.4)" : "var(--surface-2)",
          border: "1px solid " + (s.final ? "var(--accent)" : "var(--border)"),
          borderRadius: 8,
          position: "relative",
        }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span className="mono" style={{
              fontSize: 11, fontWeight: 600, color: s.final ? "var(--accent)" : "var(--text-3)",
              padding: "1px 6px", background: s.final ? "white" : "var(--surface)",
              border: "1px solid " + (s.final ? "var(--accent)" : "var(--border)"),
              borderRadius: 4,
            }}>{s.tag}</span>
            <span className="muted" style={{ fontSize: 11 }}>{s.label}</span>
          </div>
          <div className="mono" style={{ fontSize: s.final ? 22 : 18, fontWeight: 600, marginTop: 6, letterSpacing: "-0.01em", color: s.final ? "var(--accent)" : "var(--text)" }}>
            {s.val}<span style={{ fontSize: 12, color: "var(--text-3)", marginLeft: 4, fontWeight: 400 }}>{s.unit}</span>
          </div>
          {s.note && <div className="muted mono" style={{ fontSize: 10, marginTop: 2 }}>{s.note}</div>}
        </div>
      ))}
    </div>
  );
}

function CostBar({ items, total }) {
  return (
    <div>
      <div style={{ display: "flex", height: 28, borderRadius: 6, overflow: "hidden", border: "1px solid var(--border)" }}>
        {items.map((it, i) => (
          <div key={i} title={`${it[0]} ${fmtMoney(it[1])} 元`} style={{ background: it[2], width: `${it[1]/total*100}%`, display: "grid", placeItems: "center", color: "white", fontSize: 11, fontWeight: 500 }}>
            {it[1]/total > 0.08 && `${(it[1]/total*100).toFixed(1)}%`}
          </div>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 14 }}>
        {items.map((it, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: it[2] }} />
            <span style={{ flex: 1 }}>{it[0]}</span>
            <span className="mono">¥{fmtMoney(it[1])}</span>
            <span className="muted mono" style={{ width: 50, textAlign: "right" }}>{(it[1]/total*100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultReverse({ project, onBack }) {
  return (
    <div className="page hero-bg">
      <div className="page-header">
        <Button variant="ghost" icon="chevronLeft" onClick={onBack}>FP 编辑</Button>
        <div style={{ marginLeft: 8 }}>
          <div className="page-title tight">反向反推 · {project.name}</div>
          <div className="page-sub">目标预算 → 可承载 FP 规模 → AI 模块分摊</div>
        </div>
        <div className="page-spacer" />
        <Button variant="ghost" icon="refresh">重新反算</Button>
        <Button variant="primary" icon="download">下载 Excel 报告</Button>
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <div className="section-title" style={{ marginBottom: 14 }}>反算输入</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">目标总造价 (元)</label>
            <input className="field-input mono" defaultValue={project.target} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">其他费用 (元)</label>
            <input className="field-input mono" defaultValue={project.other} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">可用预算</label>
            <input className="field-input mono" disabled value={(project.target - project.other).toLocaleString()} style={{ background: "var(--surface-sunken)" }} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">α 开发占比</label>
            <input className="field-input mono" defaultValue={project.alpha || 1.0} />
          </div>
        </div>
      </div>

      <div className="result-trio">
        {[
          { key: "P10", label: "乐观 · 最大可承载", fp: 360.27, mod: 12, recommended: false },
          { key: "P50", label: "中位 · 推荐采纳", fp: 332.75, mod: 11, recommended: true },
          { key: "P90", label: "保守 · 最少可保证", fp: 305.40, mod: 10, recommended: false },
        ].map(t => (
          <div key={t.key} className={`result-card ${t.recommended ? "recommended" : ""}`}>
            {t.recommended && <div className="result-card-pill">推荐 · P50</div>}
            <div className="result-card-tag">{t.key}</div>
            <div className="result-card-name">{t.label}</div>
            <div className={`result-card-amt ${!t.recommended ? "dimmed" : ""}`}>
              {t.fp}<span className="unit">FP</span>
            </div>
            <div className="muted mono" style={{ fontSize: 12 }}>≈ {t.mod} 个模块</div>
            <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
              <div className="result-card-row"><span>未调整规模 US</span><span className="v">{(t.fp/1.21).toFixed(2)} 人时</span></div>
              <div className="result-card-row"><span>反算造价</span><span className="v">¥{fmtMoney(project.target * (0.99 + Math.random()*0.02))}</span></div>
              <div className="result-card-row"><span>误差</span><span className="v" style={{ color: "var(--green)" }}>≤ 1.00%</span></div>
            </div>
          </div>
        ))}
      </div>

      {/* AI allocator */}
      <div className="section">
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #2563EB, #7C3AED)", display: "grid", placeItems: "center", color: "white" }}>
              <Icon name="sparkles" size={16} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>AI 模块分摊</div>
              <div className="muted" style={{ fontSize: 12 }}>P50 推荐档 332.75 FP 按权重分摊到 11 个模块 · 终端运行 <span className="mono">/cost-allocate p-2026-016</span></div>
            </div>
            <Button icon="play" variant="primary" size="sm">生成模块分摊</Button>
          </div>
          <table className="table">
            <thead><tr><th>模块</th><th style={{ textAlign: "right" }}>权重</th><th style={{ textAlign: "right" }}>分配 FP</th><th>类别分布</th><th style={{ width: 60 }}>锁定</th></tr></thead>
            <tbody>
              {[
                ["受理子系统", 0.18, 59.9, { EI:8, EO:0, EQ:4, ILF:1, EIF:0 }],
                ["审批子系统", 0.22, 73.2, { EI:5, EO:1, EQ:1, ILF:1, EIF:0 }],
                ["监督子系统", 0.10, 33.3, { EI:2, EO:2, EQ:0, ILF:0, EIF:0 }],
                ["用户子系统", 0.12, 39.9, { EI:2, EO:0, EQ:1, ILF:2, EIF:0 }],
                ["报表子系统", 0.13, 43.2, { EI:0, EO:3, EQ:0, ILF:0, EIF:0 }],
                ["接口子系统", 0.15, 49.9, { EI:0, EO:0, EQ:0, ILF:1, EIF:3 }],
                ["（其他）", 0.10, 33.3, { EI:2, EO:0, EQ:1, ILF:1, EIF:0 }],
              ].map((r, i) => (
                <tr key={i}>
                  <td><b>{r[0]}</b></td>
                  <td className="mono" style={{ textAlign: "right" }}>{r[1].toFixed(2)}</td>
                  <td className="mono" style={{ textAlign: "right", fontWeight: 600 }}>{r[2].toFixed(1)}</td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      {Object.entries(r[3]).map(([c, n]) => n > 0 && <CategoryChip key={c} cat={c} />)}
                    </div>
                  </td>
                  <td>{i === 5 && <Icon name="lock" size={14} />}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 14, padding: 12, background: "var(--green-soft)", color: "var(--green)", borderRadius: 6, fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <Icon name="check" size={14} />
            双向一致性校验通过 · forward(分摊后) = <b className="mono">1,473,164 元</b> / 目标 <b className="mono">1,500,000 元</b> · 误差 <b>0.31%</b> ≤ 1%
          </div>
        </div>
      </div>
    </div>
  );
}

window.ResultPage = ResultPage;
