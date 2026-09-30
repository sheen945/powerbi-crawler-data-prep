# powerbi-crawler-data-prep

把**爬虫抓来的多源数据（JSON / CSV / Excel 混杂）**清洗进本地 Power BI Desktop，并交付成「双击就能打开」的项目的完整方案。
本仓库同时包含一套**配套的 Power BI MCP 增强包**（第三方开源件的本地补丁 + 可复用脚本）。

> 全部内容都在 Windows 10 + Power BI Desktop **26.09** 上实测跑通过，不是纸面方案。

---

## 这套东西解决什么问题

1. **爬虫数据到看板的全链路**：三类文件入口 → 统一列结构 → 爬虫特有清洗 → 文件夹增量管道 → 星型模型 → 多页看板，每一步都有可复制的模板。
2. **交付物是「能打开的工程」而不是脚本**：产出 PBIP 项目（纯文本、可进 git、双击即用），而不是一堆 M 代码片段。
3. **交付前有真机验证**：用 Power BI MCP 连上活的模型引擎验行数与勾稽，再截图确认渲染——而不是"文件看着对"。

---

## 仓库结构

- `skill/` — 技能本体（WorkBuddy / Claude 类 Agent 可直接用）
  - `SKILL.md` — 主文件（工作流、规范、交付形态、验证链）
  - `references/m-core.md` — M 语言核心规范
  - `references/sources-and-pipeline.md` — 三类入口模板 + 每日增量管道
  - `references/crawler-cleaning-patterns.md` — 字段映射 / 名称归一 / 文本转数值 / 去重
  - `references/star-schema-and-dax.md` — 星型模型与 DAX 规范（含 18 个度量值模板）
  - `references/pbip-delivery.md` — PBIP 工程怎么写（编码铁律、各文件模板、pbit 真相）
  - `references/powerbi-mcp.md` — Power BI MCP 使用手册（工具速查、验证链、本机补丁）
- `mcp/` — **Power BI MCP** 源码（第三方开源件 [sulaiman013/powerbi-mcp](https://github.com/sulaiman013/powerbi-mcp)，MIT 许可，见 `mcp/LICENSE`）
  - 已包含本仓库作者的 **3 处本地补丁**（详见 `patches/`）
  - 未附带 `adomd/`（微软的 ADOMD/TOM 客户端 DLL 与 NuGet 解包碎片，共约 97 MB）——获取方式见 `mcp/ADOMD-DLL-说明.md`
- `patches/` — 3 处补丁的说明与**可重放的应用脚本**（上游升级后重新打一遍即可）
- `tools/` — 可复用脚本（刷新验证 / 桥接截图 / 窗口截图 / 技能自检）

---

## 快速开始

### 1. 安装技能

把 `skill/` 整个目录拷到 Agent 的技能目录即可（WorkBuddy / Claude Code 通用）：

```
<技能目录>/powerbi-crawler-data-prep/SKILL.md
<技能目录>/powerbi-crawler-data-prep/references/*.md
```

WorkBuddy 的技能目录默认是 `%USERPROFILE%/.workbuddy/skills/`。

### 2. 装 Power BI MCP

```jsonc
// %USERPROFILE%/.workbuddy/mcp.json
{
  "mcpServers": {
    "powerbi": {
      "command": "<python.exe 路径>",
      "args": ["<本仓库>/mcp/src/server.py"],
      "env": {
        "PYTHONPATH": "<本仓库>/mcp/src",
        "ADOMD_DLL_PATH": "<本仓库>/mcp/adomd",
        "TOM_DLL_PATH": "<本仓库>/mcp/adomd"
      }
    }
  }
}
```

依赖：`pythonnet`、以及 `adomd/` 下的微软客户端库（见 `mcp/ADOMD-DLL-说明.md`）。
配置改完需要重启 MCP 服务（常驻进程）才生效。

### 3. 如果你 clone 的是上游原始版本

```bash
python patches/apply_patches.py --mcp-dir <你的 powerbi-mcp 目录>
```

脚本是幂等的（已打过会提示跳过），可重复执行；`--check` 只检查不修改。

---

## 实测踩过的坑（本仓库最值钱的部分）

- **TMDL 文件带 UTF-8 BOM → Power BI Desktop 直接拒绝打开**
  报错：`Only text with UTF8 encoding without BOM is supported. Detected BOM: 'UTF-8'`。
  交付出包前一律剥 BOM（`pbip-delivery.md` 有代码）。
- **事实表之间建关系 → 模型不合法**
  Desktop 报 `"A"和"维度_X"之间存在不明确的路径` 并拒绝加载。星型模型只保留 **事实 → 维度** 的关系。
- **报表视觉对象「一条角色只渲染第一个字段」**
  表格（`tableEx`）实测只渲染第一列；一条角色放多个字段时只出第一个。要"表格"效果用 `pivotTable`（Rows 一个维度 + Columns 日期 + Values 单指标）。
- **`.pbit` 模板只能由 Power BI Desktop 自己导出**（文件 → 导出 → Power BI 模板）
  pbi-tools 的离线打包接口与新版 Desktop 不兼容（`MissingMethodException`）；手工构造 PBIT 包会被判「文件可能已加密或已损坏」。
- **MCP 没有"刷新本地模型"的工具** → 用 TOM 兜底（`tools/refresh_and_verify.py`）。
- **并发调用会写坏工程文件**、**桥接参数契约在 26.07+ 变了**、**备份目录乱丢** → 见下一节。

---

## `patches/` 里的 3 处补丁（配套 MCP 的增强）

1. `desktop_bridge.py` — 新增 `call_with_args()`：26.07+ 的 Desktop Bridge 要求业务参数包在 `{"args": {...}}` 里，原代码传平铺参数会报 `-32602 Request arguments are required`；现在两种形态自动兼容，截图优先用 v2 接口。
2. `powerbi_pbip_connector.py` — `_write_text()` 加**进程级锁 + 唯一临时文件名**：并发工具调用原先共用 `<name>.tmp`，会 `WinError 32` 写坏 `Report/definition/pages/pages.json`。
3. 同文件 `create_backup()` — 备份目录从「项目旁边」改到系统临时目录 `%TEMP%/powerbi-mcp-backups/`，不再往用户工作区丢 `*_backup_<时间戳>` 文件夹。

回归验证：`tools/verify_mcp_patches.py`（并发写 4×150 次、桥接真机截图、备份路径断言）。

---

## 已验证环境

- Windows 10（19045）+ Power BI Desktop **2.158.1177.0 (26.09)**
- Python 3.13 + pythonnet；Power BI MCP（MIT）本地补丁版
- 示例场景：篮球比赛数据（多格式爬虫输出 → 23 场比赛 / 230 条首发 → 三页看板：联赛概览 / 球队分析 / 球员表现）

---

## 许可与致谢

- 本仓库的**技能部分**：GPL-3.0（`LICENSE`）。其中 M 语言规范的方法论参考了 [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development) 的 power-query 技能（GPL-3.0），已针对本地 Desktop + 平面文件场景裁剪；爬虫清洗模式、星型模型规范、PBIP 交付链路与全部补丁为原创补充。
- **`mcp/` 目录**：第三方项目 [sulaiman013/powerbi-mcp](https://github.com/sulaiman013/powerbi-mcp)，MIT 许可，版权归 Sulaiman Ahmed（见 `mcp/LICENSE`）。本仓库在其基础上带入 3 处本地补丁，补丁内容同时以脚本形式放在 `patches/`。
- `adomd/` 下的微软客户端库（ADOMD.NET / Tabular Object Model）版权归 Microsoft，未随仓库分发，请按 `mcp/ADOMD-DLL-说明.md` 自行获取。
