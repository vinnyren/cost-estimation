const { useState, useEffect, useMemo, useRef, Fragment } = React;
const { Icon, Badge, Chip, Button, ModeBadge, PhaseBadge, CategoryChip, SourceBadge, fmtMoney, fmtWan, fmtFp, StatusPill } = window;

// === Wizard screen — 7 steps ===

function Wizard({ onCancel, onCreate }) {
  const [step, setStep] = useState(1);
  const [data, setData] = useState({
    name: "智慧园区综合管理平台",
    city: "深圳",
    industry: "金融",
    customer: "深圳前海管理局",
    assessor: "中通服咨询设计研究院",
    type: "dev_and_ops",
    alpha: 0.85,
    includeOps: true,
    phase: "bidding",
    mode: "forward",
    target: 1500000,
    devFactors: { app_type: 1.00, integrity: 1.00, non_func: 1.05, platform: 1.00, team_bg: 0.80 },
    opsFactors: { biz_importance: 1.10, security: 1.05, support: 0.89, update_freq: 0.95, response: 1.10, integrity: 1.00, platform: 1.00, team_exp: 1.00, deployment: 1.00, user_scale: 1.10, relevance: 1.00 },
  });
  const upd = (k, v) => setData(d => ({ ...d, [k]: v }));

  const STEPS = [
    { n: 1, title: "基础信息", sub: "名称 / 城市 / 行业 / 客户" },
    { n: 2, title: "项目类型", sub: "dev / ops / 含运维 α" },
    { n: 3, title: "评估阶段", sub: "CF 调整因子" },
    { n: 4, title: "计算模式", sub: "正向 / 反向" },
    { n: 5, title: "开发因子", sub: "5 项 乘积" },
    { n: 6, title: "运维因子", sub: data.includeOps ? "11 项 乘积" : "跳过 (未含运维)" },
    { n: 7, title: "确认创建", sub: "字段摘要" },
  ];

  const devChain = Object.values(data.devFactors).reduce((a,b) => a*b, 1);
  const opsChain = Object.values(data.opsFactors).reduce((a,b) => a*b, 1);
  const cf = window.AppData.PHASES[data.phase].cf;

  return (
    <div className="page hero-bg">
      <div className="page-header">
        <div>
          <div className="page-title tight">新建项目</div>
          <div className="page-sub">按 7 步向导完成项目元数据 · GB/T 36964 + T/CCUA 005-2024</div>
        </div>
        <div className="page-spacer" />
        <Button variant="ghost" onClick={onCancel}>取消</Button>
      </div>

      <div className="wizard">
        <div className="card wizard-steps">
          {STEPS.map(s => (
            <div key={s.n} className={`wizard-step ${step === s.n ? "active" : ""} ${step > s.n ? "done" : ""}`} onClick={() => setStep(s.n)} style={{ cursor: "pointer" }}>
              <div className="wizard-dot">{step > s.n ? <Icon name="check" size={13} /> : s.n}</div>
              <div>
                <div className="wizard-step-title">{s.title}</div>
                <div className="wizard-step-sub">{s.sub}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="card wizard-main">
          {step === 1 && <Step1 data={data} upd={upd} />}
          {step === 2 && <Step2 data={data} upd={upd} />}
          {step === 3 && <Step3 data={data} upd={upd} cf={cf} />}
          {step === 4 && <Step4 data={data} upd={upd} />}
          {step === 5 && <Step5 data={data} upd={upd} chain={devChain} />}
          {step === 6 && <Step6 data={data} upd={upd} chain={opsChain} />}
          {step === 7 && <Step7 data={data} cf={cf} devChain={devChain} opsChain={opsChain} />}

          <div className="wizard-foot">
            <Button variant="ghost" icon="chevronLeft" disabled={step === 1} onClick={() => setStep(s => Math.max(1, s-1))}>上一步</Button>
            <span className="muted" style={{ fontSize: 12, marginLeft: 4 }}>Step {step} / 7</span>
            <div style={{ flex: 1 }} />
            {step < 7
              ? <Button variant="primary" iconRight="chevronRight" onClick={() => setStep(s => s+1)}>下一步</Button>
              : <Button variant="primary" icon="check" onClick={onCreate}>创建项目</Button>}
          </div>
        </div>
      </div>
    </div>
  );
}

function Step1({ data, upd }) {
  return (
    <div>
      <SectionHead n={1} title="基础信息" sub="项目元数据 + 客户 / 评估方（用于 Excel 封面声明）" />
      <div className="field"><label className="field-label">项目名称 *</label><input className="field-input" value={data.name} onChange={e => upd("name", e.target.value)} /></div>
      <div className="field-row">
        <div className="field">
          <label className="field-label">城市 *</label>
          <select className="field-select" value={data.city} onChange={e => upd("city", e.target.value)}>
            {window.AppData.CITIES.map(c => <option key={c[0]} value={c[0]}>{c[0]} · {c[1]} 档 · {c[2].toLocaleString()} 元/人月</option>)}
          </select>
          <div className="field-hint">影响人月费率 F_city · 37 个 CSBMK 标定城市</div>
        </div>
        <div className="field">
          <label className="field-label">行业 *</label>
          <select className="field-select" value={data.industry} onChange={e => upd("industry", e.target.value)}>
            {Object.entries(window.AppData.INDUSTRIES).map(([k,v]) => <option key={k} value={k}>{k} · P50 {v.devP50} FP/人月</option>)}
          </select>
          <div className="field-hint">影响 PDR 三档生产率</div>
        </div>
      </div>
      <div className="field-row">
        <div className="field"><label className="field-label">客户单位</label><input className="field-input" value={data.customer} onChange={e => upd("customer", e.target.value)} /></div>
        <div className="field"><label className="field-label">评估机构</label><input className="field-input" value={data.assessor} onChange={e => upd("assessor", e.target.value)} /></div>
      </div>
    </div>
  );
}

function Step2({ data, upd }) {
  return (
    <div>
      <SectionHead n={2} title="项目类型" sub="决定开发 / 运维成本是否纳入" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
        {[
          ["dev_only", "仅开发", "新建系统、不含 SLA 运维"],
          ["ops_only", "仅运维", "存量系统运维改造"],
          ["dev_and_ops", "开发 + 运维", "建设 + N 年 SLA 运维"],
        ].map(([k,name,desc]) => (
          <button key={k} className={`phase-card ${data.type === k ? "selected" : ""}`} onClick={() => { upd("type", k); upd("includeOps", k !== "dev_only"); }}>
            <div className="phase-card-name">{name}</div>
            <div className="phase-card-desc">{desc}</div>
          </button>
        ))}
      </div>
      {data.type === "dev_and_ops" && (
        <div className="card" style={{ padding: 16, background: "var(--surface-sunken)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
            <div><b>α — 开发占比</b> <span className="muted" style={{ marginLeft: 8 }}>反向反推使用</span></div>
            <div className="mono" style={{ fontSize: 18, fontWeight: 600 }}>{data.alpha.toFixed(3)}</div>
          </div>
          <input type="range" min="0.5" max="1.0" step="0.001" value={data.alpha} onChange={e => upd("alpha", parseFloat(e.target.value))} style={{ width: "100%" }} />
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>
            <span>0.5 (运维主导)</span><span>0.75</span><span>1.0 (仅开发)</span>
          </div>
          <div className="field-hint" style={{ marginTop: 10 }}>开发预算 = (T − 其他费) × α &nbsp;&nbsp;|&nbsp;&nbsp; 运维预算 = (T − 其他费) × (1 − α) = <span className="mono">{(1-data.alpha).toFixed(3)}</span></div>
        </div>
      )}
    </div>
  );
}

function Step3({ data, upd, cf }) {
  return (
    <div>
      <SectionHead n={3} title="评估阶段" sub="不同阶段对应不同的不确定性，CF 实时预览" />
      <div className="phase-cards">
        {Object.entries(window.AppData.PHASES).map(([k,p]) => (
          <button key={k} className={`phase-card ${data.phase === k ? "selected" : ""}`} onClick={() => upd("phase", k)}>
            <div className="phase-card-name">{p.label}</div>
            <div className="phase-card-cf">{p.cf}</div>
            <div className="phase-card-desc">{p.desc}</div>
          </button>
        ))}
      </div>
      <div className="cf-preview">
        <div className="cf-preview-formula">
          调整后规模 S = <span className="var">US</span> × <span className="var">CF</span> &nbsp; · &nbsp; 当前阶段 = <b>{window.AppData.PHASES[data.phase].label}</b>
          <div style={{ marginTop: 4, color: "var(--text-3)" }}>CF 取自 GB/T 36964-2018 附录 B 阶段调整因子表</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: "var(--text-3)", letterSpacing: "0.1em", textTransform: "uppercase", textAlign: "right" }}>CF</div>
          <div className="cf-preview-result">{cf}</div>
        </div>
      </div>
    </div>
  );
}

function Step4({ data, upd }) {
  return (
    <div>
      <SectionHead n={4} title="计算模式" sub="正向：文档 → FP → 三档造价  |  反向：预算 → FP 规模 → 模块分摊" />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        {[
          ["forward", "正向估算", "已知功能清单，输出三档造价", "blue"],
          ["reverse", "反向反推", "已知预算上限，反推可承载 FP 规模", "amber"],
        ].map(([k, name, desc, tone]) => (
          <button key={k} className={`phase-card ${data.mode === k ? "selected" : ""}`} onClick={() => upd("mode", k)}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div className="phase-card-name">{name}</div>
              <Badge tone={tone}>{k}</Badge>
            </div>
            <div className="phase-card-desc">{desc}</div>
          </button>
        ))}
      </div>
      {data.mode === "reverse" && (
        <div className="card" style={{ padding: 16, background: "var(--surface-sunken)" }}>
          <div className="field"><label className="field-label">目标总造价 (元) *</label>
            <input className="field-input mono" value={data.target} onChange={e => upd("target", parseFloat(e.target.value) || 0)} />
            <div className="field-hint">= {fmtWan(data.target)} 万元 · 减去其他费后按 PDR 三档反推 FP 规模</div>
          </div>
        </div>
      )}
    </div>
  );
}

function Step5({ data, upd, chain }) {
  return (
    <div>
      <SectionHead n={5} title="开发因子" sub="5 项调整因子 · 乘积链式实时显示" />
      <div className="factor-grid">
        {window.AppData.DEV_FACTORS.map(f => (
          <div key={f.key} className="field">
            <label className="field-label">{f.label}</label>
            <select className="field-select" value={data.devFactors[f.key]} onChange={e => upd("devFactors", { ...data.devFactors, [f.key]: parseFloat(e.target.value) })}>
              {f.options.map(([n,v]) => <option key={n} value={v}>{n}</option>)}
            </select>
          </div>
        ))}
      </div>
      <div className="factor-chain">
        <span className="muted">dev_factor = </span>
        {Object.values(data.devFactors).map((v,i) => (
          <Fragment key={i}>{i > 0 && <span style={{ color: "var(--text-3)" }}> × </span>}<span>{v.toFixed(2)}</span></Fragment>
        ))}
        <span className="chain-out">= {chain.toFixed(4)}</span>
      </div>
    </div>
  );
}

function Step6({ data, upd, chain }) {
  if (!data.includeOps) {
    return (
      <div>
        <SectionHead n={6} title="运维因子" sub="项目类型未启用运维，跳过此步" />
        <div style={{ padding: 40, textAlign: "center", color: "var(--text-3)" }}>
          <Icon name="info" size={32} />
          <div style={{ marginTop: 8 }}>当前项目类型为 <b>{data.type === "dev_only" ? "仅开发" : "仅运维"}</b>，11 项运维因子已跳过。</div>
        </div>
      </div>
    );
  }
  return (
    <div>
      <SectionHead n={6} title="运维因子" sub="11 项调整因子 · GB/T 28827.7-2022 §6.1" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {window.AppData.OPS_FACTORS.map(f => (
          <div key={f.key} className="field" style={{ marginBottom: 0 }}>
            <label className="field-label">{f.label}</label>
            <input className="field-input mono" value={data.opsFactors[f.key]} onChange={e => upd("opsFactors", { ...data.opsFactors, [f.key]: parseFloat(e.target.value) || 1 })} />
          </div>
        ))}
      </div>
      <div className="factor-chain" style={{ marginTop: 16 }}>
        <span className="muted">ops_factor 乘积 = </span>
        <span className="chain-out">{chain.toFixed(4)}</span>
      </div>
    </div>
  );
}

function Step7({ data, cf, devChain, opsChain }) {
  const rows = [
    ["项目名称", data.name],
    ["客户 / 评估方", `${data.customer || "—"} / ${data.assessor || "—"}`],
    ["城市 · 行业", `${data.city} · ${data.industry}`],
    ["项目类型", data.type + (data.type === "dev_and_ops" ? ` · α = ${data.alpha.toFixed(3)}` : "")],
    ["评估阶段", `${window.AppData.PHASES[data.phase].label} · CF = ${cf}`],
    ["计算模式", data.mode === "forward" ? "正向估算" : `反向反推 · 目标 ${fmtMoney(data.target)} 元`],
    ["开发因子乘积", devChain.toFixed(4)],
    ["运维因子乘积", data.includeOps ? opsChain.toFixed(4) : "—"],
    ["数据基准", "CSBMK®-202510"],
  ];
  return (
    <div>
      <SectionHead n={7} title="确认创建" sub="检查所有字段后点击底部「创建项目」" />
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {rows.map(([k, v], i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "180px 1fr", padding: "12px 16px", borderBottom: i < rows.length-1 ? "1px solid var(--border)" : 0 }}>
            <div className="muted" style={{ fontSize: 12 }}>{k}</div>
            <div className="mono" style={{ fontSize: 13 }}>{v}</div>
          </div>
        ))}
      </div>
      <div className="banner banner-blue" style={{ marginTop: 16 }}>
        <Icon name="info" size={16} />
        <div>创建后将跳转 FP 编辑屏 · 上传需求文档后可在终端执行 <span className="mono">/cost &lt;project_id&gt;</span> 让 Claude 写第一稿</div>
      </div>
    </div>
  );
}

function SectionHead({ n, title, sub }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Badge tone="blue">Step {n} / 7</Badge>
        <div style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-0.01em" }}>{title}</div>
      </div>
      <div className="muted" style={{ marginTop: 4, fontSize: 12 }}>{sub}</div>
    </div>
  );
}

window.Wizard = Wizard;
window.NewProjectWizard = Wizard;
