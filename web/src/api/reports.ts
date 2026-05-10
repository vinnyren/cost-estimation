import { api } from "./client";

export const reportsApi = {
  excelUrl: (projectId: number) => `/api/reports/excel/${projectId}`,
  download: async (projectId: number, filename = "造价报告.xlsx"): Promise<void> => {
    // Token is injected by the request interceptor in client.ts — no manual
    // header needed even for direct api.raw.* calls like this blob download.
    const resp = await api.raw.get(`/api/reports/excel/${projectId}`, {
      responseType: "blob",
    });
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
