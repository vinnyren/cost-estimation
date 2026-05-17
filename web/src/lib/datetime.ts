/**
 * 时间显示统一工具。
 *
 * 后端时间戳是 naive UTC —— 形如 "2026-05-17T07:10:24"，无时区后缀。
 * 直接 `new Date(s)` 会被浏览器按本地时区解释，造成偏差；这里统一按 UTC
 * 解析后转东八区（北京时间 Asia/Shanghai）显示。
 */

const BEIJING_TZ = "Asia/Shanghai";

/** 给无时区后缀的时间戳补 'Z'，让 Date 按 UTC 解析。 */
function asUtc(iso: string): string {
  return /([zZ]|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`;
}

/**
 * 格式化为北京时间 "YYYY-MM-DD HH:mm"。
 * 空值返回 "—"；无法解析时原样返回。
 */
export function formatBeijing(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(asUtc(iso));
  if (Number.isNaN(d.getTime())) return iso;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: BEIJING_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(d);
  const get = (t: string): string => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
}

/** 北京时间含秒 "YYYY-MM-DD HH:mm:ss"。 */
export function formatBeijingFull(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(asUtc(iso));
  if (Number.isNaN(d.getTime())) return iso;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: BEIJING_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(d);
  const get = (t: string): string => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}:${get("second")}`;
}
