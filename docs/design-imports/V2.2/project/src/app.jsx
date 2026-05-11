const { useState, useEffect, useMemo, useRef, Fragment } = React;
const { Icon, Badge, Chip, Button, ModeBadge, PhaseBadge, CategoryChip, SourceBadge, fmtMoney, fmtWan, fmtFp, StatusPill } = window;

// === App Shell — sidebar + topbar + router ===

function App() {
  const [route, setRoute] = useState({ name: "projects" });
  const [project, setProject] = useState(null);

  // helpers
  const go = (name, p) => { if (p) setProject(p); setRoute({ name }); };

  return (
    <div className="app">
      <Sidebar route={route.name} onNav={go} />
      <div className="app-main">
        <Topbar route={route.name} project={project} onNav={go} />
        <div className="app-content">
          {route.name === "projects" && <window.ProjectList onOpen={(p) => go("fp", p)} onNew={() => go("wizard")} />}
          {route.name === "wizard" && <window.NewProjectWizard onCancel={() => go("projects")} onCreate={(p) => go("fp", p)} />}
          {route.name === "fp" && project && <window.FpEditor project={project} onCalculate={() => go("result")} onParams={() => go("params")} />}
          {route.name === "params" && project && <window.ParamManager project={project} onBack={() => go("fp")} />}
          {route.name === "result" && project && <window.ResultPage project={project} onBack={() => go("fp")} />}
          {route.name === "audit" && <window.AuditPage onBack={() => go("result")} />}
        </div>
      </div>
    </div>
  );
}

function Sidebar({ route, onNav }) {
  const items = [
    { key: "projects", label: "项目工作台", icon: "folder" },
    { key: "params", label: "全局参数库", icon: "settings", disabled: true },
    { key: "templates", label: "模板与场景", icon: "layers", disabled: true },
    { key: "reports", label: "报告中心", icon: "file", disabled: true },
    { key: "audit", label: "审计日志", icon: "history" },
  ];
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" stroke="white" strokeWidth="1.6" fill="none"/>
            <circle cx="16.5" cy="16.5" r="2" fill="white"/>
          </svg>
        </div>
        <div>
          <div className="brand-name">FP-Studio</div>
          <div className="brand-sub mono">v2.4 · CSBMK 202510</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">主导航</div>
        {items.map(it => (
          <a key={it.key} className={`nav-item ${route === it.key ? "active" : ""} ${it.disabled ? "disabled" : ""}`}
             onClick={() => !it.disabled && onNav(it.key)}>
            <Icon name={it.icon} size={15} />
            <span>{it.label}</span>
            {it.disabled && <span className="nav-soon">敬请期待</span>}
          </a>
        ))}

        <div className="nav-section" style={{ marginTop: 18 }}>当前项目</div>
        <a className={`nav-item sub ${route === "fp" ? "active" : ""}`} onClick={() => onNav("fp")}>
          <Icon name="grid" size={14} /><span>FP 编辑</span>
        </a>
        <a className={`nav-item sub ${route === "result" ? "active" : ""}`} onClick={() => onNav("result")}>
          <Icon name="trending" size={14} /><span>三档造价</span>
        </a>
        <a className={`nav-item sub`}><Icon name="file" size={14} /><span>报告</span></a>
      </nav>

      <div className="sidebar-foot">
        <div className="sidebar-help">
          <Icon name="info" size={13} />
          <div>
            <div style={{ fontWeight: 500, fontSize: 11.5 }}>本期标准</div>
            <div className="muted mono" style={{ fontSize: 10.5 }}>CSBMK®-202510</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

function Topbar({ route, project, onNav }) {
  const crumbs = [];
  crumbs.push({ label: "项目工作台", on: () => onNav("projects") });
  if (route === "wizard") crumbs.push({ label: "新建项目" });
  if (project && (route === "fp" || route === "params" || route === "result")) {
    crumbs.push({ label: project.name, on: () => onNav("fp", project) });
    if (route === "params") crumbs.push({ label: "参数管理" });
    if (route === "result") crumbs.push({ label: "三档造价" });
  }
  if (route === "audit") crumbs.push({ label: "审计日志" });

  return (
    <div className="topbar">
      <div className="crumbs">
        {crumbs.map((c, i) => (
          <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            {i > 0 && <Icon name="chevronRight" size={12} style={{ color: "var(--text-3)" }} />}
            <a className={`crumb ${i === crumbs.length-1 ? "current" : ""}`} onClick={c.on}>{c.label}</a>
          </span>
        ))}
      </div>
      <div className="topbar-spacer" />
      <div className="topbar-search">
        <Icon name="search" size={13} style={{ color: "var(--text-3)" }} />
        <input placeholder="搜索项目、城市、模块… (⌘K)" />
      </div>
      <div className="topbar-actions">
        <button className="icon-btn" title="审计日志" onClick={() => onNav("audit")}><Icon name="history" size={16} /></button>
        <button className="icon-btn" title="帮助"><Icon name="info" size={16} /></button>
        <div className="user-chip">
          <div className="avatar">李</div>
          <div className="user-meta">
            <div>李工程师</div>
            <div className="muted">咨询编辑</div>
          </div>
        </div>
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
