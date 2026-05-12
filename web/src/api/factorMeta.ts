import { api } from "./client";

export interface FactorOptionMeta {
  label: string;
  description: string;
}

export interface FactorMeta {
  label: string;
  description: string;
  options: Record<string, FactorOptionMeta>;
}

export interface FactorMetaPayload {
  version?: string;
  factors_dev: Record<string, FactorMeta>;
  factors_ops: Record<string, FactorMeta>;
}

export const factorMetaApi = {
  async get(): Promise<FactorMetaPayload> {
    const r = await api.raw.get<FactorMetaPayload>("/api/params/factor-meta");
    return r.data;
  },
};
