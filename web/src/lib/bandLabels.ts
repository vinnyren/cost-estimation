/** 成本档位（P10/P50/P90）中文标签。 */
export type CostBand = "P10" | "P50" | "P90";

/** 计算路径详解 / 卡片标题用的档位中文名。 */
export const BAND_DETAIL_LABEL: Record<CostBand, string> = {
  P10: "P10 乐观档",
  P50: "P50 推荐档",
  P90: "P90 保守档",
};
