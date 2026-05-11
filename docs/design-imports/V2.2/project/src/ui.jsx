// === Shared UI primitives ===
const { useState, useEffect, useRef, useMemo, Fragment } = React;

// Icons — inline SVG, stroke-based
function Icon({ name, size = 16, strokeWidth = 1.75, style }) {
  // alias map for missing icons
  const ALIAS = { history: "refresh", grid: "layers", trending: "chevronRight", archive: "folder", user: "settings" };
  if (ALIAS[name]) name = ALIAS[name];
  const s = size;
  const sw = strokeWidth;
  const props = { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: sw, strokeLinecap: "round", strokeLinejoin: "round", style };
  const paths = {
    list: <><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></>,
    plus: <><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></>,
    search: <><circle cx="11" cy="11" r="7"/><line x1="20" y1="20" x2="16.65" y2="16.65"/></>,
    folder: <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></>,
    table: <><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></>,
    chart: <><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></>,
    clock: <><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></>,
    chevronRight: <polyline points="9 18 15 12 9 6"/>,
    chevronDown: <polyline points="6 9 12 15 18 9"/>,
    chevronLeft: <polyline points="15 18 9 12 15 6"/>,
    check: <polyline points="20 6 9 17 4 12"/>,
    sparkles: <><path d="M12 3L13.5 8.5 19 10L13.5 11.5 12 17 10.5 11.5 5 10 10.5 8.5z"/><path d="M19 3v3M19 19v3M5 16v3"/></>,
    upload: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></>,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></>,
    play: <polygon points="5 3 19 12 5 21 5 3"/>,
    refresh: <><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></>,
    more: <><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></>,
    lock: <><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></>,
    filter: <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>,
    sort: <><polyline points="3 6 7 2 11 6"/><line x1="7" y1="2" x2="7" y2="22"/></>,
    copy: <><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></>,
    trash: <><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></>,
    edit: <><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4z"/></>,
    info: <><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></>,
    bolt: <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>,
    layers: <><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></>,
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></>,
    flask: <><path d="M9 2h6M10 2v6L4 20a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-6-12V2"/></>,
    branch: <><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></>,
  };
  return <svg {...props}>{paths[name] || null}</svg>;
}

function Badge({ tone = "default", children, dot }) {
  const cls = `badge${tone !== "default" ? " badge-" + tone : ""}`;
  return <span className={cls}>{dot && <span className="badge-dot" />}{children}</span>;
}

function Chip({ children }) { return <span className="chip">{children}</span>; }

function Button({ variant, size, icon, iconRight, children, onClick, disabled, style, title }) {
  const cls = [
    "btn",
    variant === "primary" && "btn-primary",
    variant === "ghost" && "btn-ghost",
    variant === "danger" && "btn-danger",
    size === "sm" && "btn-sm",
    size === "lg" && "btn-lg",
    !children && "btn-icon",
    disabled && "btn-disabled",
  ].filter(Boolean).join(" ");
  return (
    <button className={cls} onClick={onClick} disabled={disabled} style={style} title={title}>
      {icon && <Icon name={icon} size={14} />}
      {children}
      {iconRight && <Icon name={iconRight} size={14} />}
    </button>
  );
}

function ModeBadge({ mode }) {
  if (mode === "reverse") return <Badge tone="amber" dot>反向反推</Badge>;
  return <Badge tone="blue" dot>正向估算</Badge>;
}

function PhaseBadge({ phase }) {
  const p = window.AppData.PHASES[phase];
  if (!p) return null;
  return <Chip>{p.label} · CF {p.cf}</Chip>;
}

function CategoryChip({ cat }) {
  return <span className={`cat cat-${cat}`}>{cat}</span>;
}

function SourceBadge({ source }) {
  const map = {
    manual: ["badge", "手动"],
    ai_extracted: ["badge-blue", "AI 提取"],
    claude_draft: ["badge-purple", "Claude 草稿"],
    allocator: ["badge-amber", "预算倒推"],
    imported: ["badge-green", "Excel 导入"],
  };
  const [tone, label] = map[source] || ["badge", source];
  return <Badge tone={tone.replace("badge-", "").replace("badge","default")}>{label}</Badge>;
}

// number formatter — Chinese currency
function fmtMoney(n) {
  if (n == null) return "—";
  return Math.round(n).toLocaleString("zh-CN");
}
function fmtWan(n) {
  if (n == null) return "—";
  return (n / 10000).toFixed(2);
}
function fmtFp(n) {
  if (n == null) return "—";
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function StatusPill({ status }) {
  const map = {
    "草稿": ["default", "草稿"],
    "计算中": ["amber", "计算中"],
    "已计算": ["green", "已计算"],
    "已归档": ["default", "已归档"],
    "已交付": ["blue", "已交付"],
  };
  const [tone, label] = map[status] || ["default", status];
  return <Badge tone={tone} dot>{label}</Badge>;
}

Object.assign(window, { Icon, Badge, Chip, Button, ModeBadge, PhaseBadge, CategoryChip, SourceBadge, StatusPill, fmtMoney, fmtWan, fmtFp });
