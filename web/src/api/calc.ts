import { api } from "./client";

export type Band = "P10" | "P50" | "P90";
export type BandValues = { P10: number; P50: number; P90: number };

export interface PipelineTrace {
  us: number;
  cf: number;
  s_adjusted: number;
  pdr_p50: number;
  dev_factor: number;
  eff_pm_p50: number;
  eff_hours_p50: number;
  f_city: number;
  ops_plus_other: number;
  total_p50: number;
}

export interface CostComposition {
  dev_labor: number;
  ops_labor: number;
  other: number;
  indirect: number;
}

/**
 * Forward 正向计算返回值（与 server `app/core/forward.py:ForwardResult` 一一对应）。
 *
 * - effort_*_hours / cost_*_yuan 是三档 dict（P10/P50/P90）。
 * - cost_total_yuan 是 P10/P50/P90 三档总价。
 */
export interface ForwardResult {
  scale_us: number;
  scale_adjusted: number;
  cf_used: number;
  effort_dev_hours: BandValues;
  effort_ops_hours: BandValues;
  cost_dev_yuan: BandValues;
  cost_ops_yuan: BandValues;
  cost_other_yuan: number;
  cost_total_yuan: BandValues;
  warning_messages?: string[];
  // v2.2 新增
  trace?: PipelineTrace;
  composition?: CostComposition;
}

/** 反算 UFP 细化分摊到一级模块的单行。 */
export interface ModuleUfpAllocation {
  subsystem: string;
  l1_module: string;
  current_ufp: number;
  allocated_ufp: number;
  delta_ufp: number;
  ratio: number;
}

/** 反算三级模块树节点。subsystem/l1_module/l2_module 三层各一种形状。 */
export interface ModuleTreeL2 {
  l2_module: string;
  current_ufp: number;
  allocated_ufp: number;
  delta_ufp: number;
  ratio: number;
}
export interface ModuleTreeL1 {
  l1_module: string;
  current_ufp: number;
  allocated_ufp: number;
  delta_ufp: number;
  ratio: number;
  children: ModuleTreeL2[];
}
export interface ModuleTreeSubsystem {
  subsystem: string;
  current_ufp: number;
  allocated_ufp: number;
  delta_ufp: number;
  ratio: number;
  children: ModuleTreeL1[];
}

/**
 * Reverse 反算返回值（与 server `app/core/reverse.py:ReverseResult` 对齐）。
 *
 * 三档语义见 server 类注释：
 * - P10 乐观 / P50 中位 / P90 保守。
 * - 单一规模模型：scale_*_bands 为开发与运维共用的功能点规模（FP）。
 * - budget_for_dev / budget_for_ops 是该规模下推导出的成本拆分（推荐档）。
 * - target_ufp / module_allocation：以 UFP 为核心，把反算总规模按现有 FP
 *   表各一级模块的 UFP 占比细化分摊。
 */
export interface ReverseResult {
  budget_for_dev: number;
  budget_for_ops: number;
  scale_adjusted_bands: BandValues;
  scale_unadjusted_bands: BandValues;
  cf_used: number;
  recommended_band: Band;
  target_ufp: number;
  module_allocation: ModuleUfpAllocation[];
  module_allocation_tree?: ModuleTreeSubsystem[];
}

/**
 * Allocate 分摊返回值（与 server `app/core/allocator.py:AllocatorOutput` 对齐）。
 */
export interface AllocateOutput {
  name: string;
  us: number;
  locked: boolean;
  audit_tag: string | null;
}

export interface AllocateValidation {
  recalc_total_us: number;
  recalc_total_adjusted: number;
  error_pct: number;
}

export interface AllocateResult {
  items: AllocateOutput[];
  validation: AllocateValidation;
}

export const calcApi = {
  forward: (body: { project_id: string }) =>
    api.post<ForwardResult>("/api/calc/forward", body),
  reverse: (body: { project_id: string; target_total: number; other_cost: number }) =>
    api.post<ReverseResult>("/api/calc/reverse", body),
  allocate: (body: {
    project_id: string;
    target_us: number;
    cf: number;
    drafts: Array<{ name: string; weight: number; locked?: boolean; locked_us?: number }>;
  }) => api.post<AllocateResult>("/api/calc/allocate", body),
};
