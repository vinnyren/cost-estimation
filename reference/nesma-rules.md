# NESMA 估算法规则（v2.3 简化版，对齐 GB/T 36964 附录）

NESMA（Netherlands Software Metrics Association）估算法把功能项分为 5 大类，按"未调整功能点（UFP）"权重打分。本仓库实现 NESMA 估算变体（不含详细数据元素 DET / 文件类型引用 FTR 计数），按"低/中/高"复杂度三档赋值。

## 5 大类与权重

| 类别 | 全称 | 含义 | 复杂度（低/中/高 UFP） |
|---|---|---|---|
| **EI** | External Input | 外部输入：用户提交数据更新内部数据（增/改/删） | 3 / 4 / 6 |
| **EO** | External Output | 外部输出：含派生计算的对外输出（报表、统计） | 4 / 5 / 7 |
| **EQ** | External Inquiry | 外部查询：检索数据但不含派生计算（搜索、列表） | 3 / 4 / 6 |
| **ILF** | Internal Logical File | 内部逻辑文件：应用维护的核心实体（用户、订单） | 7 / 10 / 15 |
| **EIF** | External Interface File | 外部接口文件：跨系统引用的只读数据 | 5 / 7 / 10 |

NESMA 估算（Estimated）默认所有项取"中"档权重；如需更细，按下方 DET/FTR 阈值调整。

## 复杂度判定（详尽计数模式）

### EI / EO / EQ 复杂度（基于 DET + FTR）

| FTR \ DET | 1-4 | 5-15 | ≥16 |
|---|---|---|---|
| 0-1 | 低 | 低 | 中 |
| 2 | 低 | 中 | 高 |
| ≥3 | 中 | 高 | 高 |

### ILF / EIF 复杂度（基于 DET + RET）

| RET \ DET | 1-19 | 20-50 | ≥51 |
|---|---|---|---|
| 1 | 低 | 低 | 中 |
| 2-5 | 低 | 中 | 高 |
| ≥6 | 中 | 高 | 高 |

DET = Data Element Types（字段数）  
FTR = File Types Referenced（引用的文件数）  
RET = Record Element Types（子记录类型数）

## 类别识别提示

读用户文档（功能清单/用户手册）时，按以下关键词归类：

- **EI**：「新增」「修改」「删除」「批量导入」「保存」「提交表单」「上传文件并存库」
- **EO**：「报表」「图表」「日报/月报」「导出 Excel（含计算）」「KPI 仪表盘」
- **EQ**：「查询」「搜索」「筛选」「列表展示」「详情查看」「下拉选项」
- **ILF**：「<实体>管理」（如用户管理 → User ILF）；新建一类核心数据
- **EIF**：「调用<外部系统>接口获取……」「读取来自……的字典数据」

## NESMA 估算模式（本系统默认）

启用 estimated 模式时：
- EI = 4 UFP / EO = 5 UFP / EQ = 4 UFP / ILF = 10 UFP / EIF = 7 UFP（中复杂度）
- 重用率（reuse_ratio）默认 0.0，修改率（modify_ratio）默认 0.0
- US（unadjusted size）= UFP × (1 - reuse_ratio × 0.5 - modify_ratio × 0.25)

实施规程附录 A 模板（功能点计数表）的列：

| 子系统 | 一级模块 | 二级模块 | 描述 | 类别 | UFP | 重用率 | 修改率 | US |

## 写回到 API

调用 `POST /api/projects/{id}/functions/bulk`，body：

```json
{
  "items": [
    {
      "subsystem": "用户子系统",
      "module_l1": "用户管理",
      "module_l2": "新增用户",
      "description": "管理员新增用户并设置角色",
      "category": "EI",
      "ufp": 4,
      "reuse_ratio": 0.0,
      "modify_ratio": 0.0,
      "source": "ai_extracted"
    }
  ]
}
```

> 后端会按 NESMA 计算 US 并写入触发器快照。
