"""CosmicMethod：CFP = 入口 + 出口 + 读 + 写（GB/T 42452-2023）。"""


class CosmicMethod:
    size_unit = "CFP"
    input_model = "cosmic"

    def compute_entry_size(self, entry: dict) -> float:
        """CFP = sum(cosmic_entry, cosmic_exit, cosmic_read, cosmic_write)。

        任一字段缺失或 None 按 0 处理。
        """
        return float(
            (entry.get("cosmic_entry") or 0)
            + (entry.get("cosmic_exit") or 0)
            + (entry.get("cosmic_read") or 0)
            + (entry.get("cosmic_write") or 0)
        )
