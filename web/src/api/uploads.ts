import { api } from "./client";

export interface UploadResult {
  upload_id: number;
  filename: string;
  size: number;
  parsed_text_preview?: string;
}

export const uploadsApi = {
  upload: async (projectId: number, file: File): Promise<UploadResult> => {
    const form = new FormData();
    form.append("file", file);
    // Do NOT set Content-Type manually — axios detects FormData and generates
    // the correct multipart/form-data header with a boundary. Hand-writing
    // "multipart/form-data" without a boundary breaks server-side parsing.
    return api.post<UploadResult>(`/api/projects/${projectId}/uploads`, form);
  },
};
