import { api } from "./client";

export interface UploadResult {
  upload_id: number;
  filename: string;
  size: number;
  parsed_text_preview?: string;
}

export interface UploadRecord {
  id: number;
  project_id: string;
  filename: string;
  size: number;
  filetype: string;
  uploaded_at: string;
  parsed_text_path: string | null;
}

export const uploadsApi = {
  upload: async (projectId: string, file: File): Promise<UploadResult> => {
    const form = new FormData();
    form.append("file", file);
    // Do NOT set Content-Type manually — axios detects FormData and generates
    // the correct multipart/form-data header with a boundary. Hand-writing
    // "multipart/form-data" without a boundary breaks server-side parsing.
    return api.post<UploadResult>(`/api/projects/${projectId}/uploads`, form);
  },

  list: async (projectId: string): Promise<UploadRecord[]> => {
    return api.get<UploadRecord[]>(
      `/api/projects/${encodeURIComponent(projectId)}/uploads`
    );
  },

  remove: async (projectId: string, uploadId: number): Promise<void> => {
    // DELETE returns 204 No Content — use raw axios to skip envelope unwrapping.
    await api.raw.delete(
      `/api/projects/${encodeURIComponent(projectId)}/uploads/${uploadId}`
    );
  },
};
