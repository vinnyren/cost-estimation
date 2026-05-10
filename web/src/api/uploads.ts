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
    return api.post<UploadResult>(`/api/projects/${projectId}/uploads`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};
