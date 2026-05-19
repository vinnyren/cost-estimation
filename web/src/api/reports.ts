import { api } from "./client";

async function _extractBlobError(err: unknown): Promise<string> {
  const e = err as { response?: { data?: unknown }; message?: string };
  let msg = e.message ?? "下载失败";
  const data = e.response?.data;
  if (data instanceof Blob) {
    try {
      const json = JSON.parse(await data.text());
      const env = json?.error ?? json?.detail?.error;
      msg =
        env?.fix ||
        env?.problem ||
        env?.message ||
        env?.code ||
        (typeof json?.detail === "string" ? json.detail : msg);
    } catch {
      /* 非 JSON 错误体 —— 保留原始 message */
    }
  }
  return msg;
}

export const reportsApi = {
  excelUrl: (projectId: string) => `/api/reports/excel/${projectId}`,
  download: async (projectId: string, filename = "造价报告.xlsx", band?: "P10" | "P50" | "P90"): Promise<void> => {
    // Token is injected by the request interceptor in client.ts — no manual
    // header needed even for direct api.raw.* calls like this blob download.
    const apiUrl = band
      ? `/api/reports/excel/${projectId}?band=${band}`
      : `/api/reports/excel/${projectId}`;
    let resp;
    try {
      resp = await api.raw.get(apiUrl, {
        responseType: "blob",
      });
    } catch (err: unknown) {
      // responseType:blob 时错误体也是 Blob —— 默认错误处理读不到 JSON，
      // 只会得到「Request failed with status code 5xx」。这里把错误 Blob
      // 读成文本解析，抛出后端给的真实原因。
      throw new Error(await _extractBlobError(err));
    }
    const blob = new Blob([resp.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
};
