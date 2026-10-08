# powerbi-crawler-data-prep

> 把爬虫抓来的多源数据（JSON/CSV/Excel 混杂）清洗进本地 Power BI Desktop 的完整链路技能：M 清洗流 → 星型模型 → 多页看板 → **.pbit 模板交付** → Power BI MCP 真机验证。

## 简介

这是一个 WorkBuddy / Claude Code Agent 技能（Agent Skill），专为「爬虫数据 → 本地 Power BI Desktop」这条链路而生。爬虫每天把 JSON/CSV/Excel 混着丢进同一个文件夹，数据永远脏（列名不统一、数字存成文本、同一名称多种写法、重复抓取），而你要的只是：跑爬虫、丢文件、点刷新，然后看一份多页看板。这个技能把这中间的所有环节都工程化了——从 Power Query M 清洗、星型模型建模、PBIP 工程管理，到最终导出 `.pbit` 模板交付，再到用 Power BI MCP 连活模型做真机验证（刷新 / 行数 / 勾稽 / 逐页截图），每一步都有可复用的模板、踩过坑的清单和自动化脚本。

**触发场景**：爬虫数据进 Power BI、多格式合并、每日/每比赛日增量刷新、篮球/比赛数据清洗、CC指数/伤病/首发可视化、星型模型/维度建模/度量值/计算列、要在 Power BI 里直接看到 / 帮我打开 Power BI、做成 pbip / Power BI 项目 / 模板 / pbit、导出 pbit、Power BI MCP、写 Power Query M 代码。

## 功能特性

- **三类入口统一接入**：JSON → `Json.Document`、CSV → `Csv.Document`、Excel → `Excel.Workbook`，各用一个入口查询，统一列结构后 `Table.Combine` 纵向合并
- **每日增量管道**：基于 `Folder.Files` 文件夹连接器，爬虫新文件丢进同一文件夹即自动纳入合并，用户动作只有「跑爬虫 → 丢文件 → 点刷新」
- **爬虫特有清洗模式**：映射表一步批量改名（`Table.RenameColumns`）、球队/球员别名表名称归一、`Number.FromText` + `try...otherwise null` 文本转数值、缺失字段加标记列而非删行
- **显式去重**：爬虫重复抓取是常态，按「比赛日期 + 球员」（或业务主键）显式去重，防止重复导入导致数据翻倍
- **星型模型建模规范**：事实表存「发生了什么」、维度表存「属性」，维度从同一条事实管道派生；只建事实→维度关系；计算列只放静态属性，一切聚合走度量值（带格式串 + 显示文件夹 + 中文描述）；含 18 个度量值模板与看板排版坐标
- **M 语言工程规范**：8 条高频核心规范（命名说人话、类型尽早转、批量改名、裁剪尽早、分步调试、错误处理显式化……）+ 完整踩坑清单
- **`.pbit` 唯一交付格式**（2026-10-07 定规）：PBIP 只是中间工程载体，最终必须经 Desktop「文件 → 导出 → Power BI 模板」导出 `.pbit`；导出全流程（9 步配方）可自动化，只有参数框需用户 1~2 次操作
- **真机验证闭环**：PBIP 产出后必跑「离线校验（pbip_load_project → pbip_validate → pbir_validate_report）→ 打开 Desktop → TOM 刷新 → DAX 验行数勾稽 → 逐页截图取证」链条，导出 PBIT 后再验一次
- **踩透的坑清单**：12 条「别再做 / 为什么 / 直接做什么」对照表（自造 PBIT、`pbi-tools compile`、`mouse_event` 点后台面板、肉眼估坐标、`netstat` 找端口……每一条都有实测事故记录）
- **配套 MCP 服务端源码**：`mcp/` 目录内置 Power BI MCP 服务端（82 个工具），含 3 处本机实测补丁，打通「本地 Desktop 真机验证」链路

## 工作原理与技术栈

### 四条铁律（本项目环境已验证的前提）

1. **查询折叠不存在**——平面文件（JSON/CSV/Excel）没有查询引擎，性能优化只能靠「列裁剪尽早、行过滤尽早」
2. **爬虫数据永远脏**——清洗步骤一个都不能省
3. **每日增量 = 文件夹连接器**——`Folder.Files` 自动合并全部文件
4. **去重键必须显式定义**——防止爬虫重抓导致重复导入

### 五步标准工作流

1. **统一入口**：三种格式各用一个入口查询，统一列结构
2. **合并多源**：统一列名/列序/类型后 `Table.Combine` 纵向拼接
3. **爬虫特有清洗**：字段映射 → 名称归一 → 文本转数值 → 缺失值标记（固定顺序）
4. **每日增量管道**：`Folder.Files` 列出全部文件 → 按扩展名分流 → 合并 → 去重
5. **验证**：语法、数据、类型、空值、行数五项检查清单

### 交付六步链（固定顺序，不跳步不改序）

```
① 生成 PBIP 工程（Python 生成器，列清单同时驱动 M 代码与 TMDL 列定义）
② 离线校验（pbip_load_project → pbip_validate → pbir_validate_report 全绿）
③ 真机验证（打开 Desktop → TOM 刷新 → DAX 验行数/勾稽）
④ 导出 PBIT（Desktop 文件 → 导出 → Power BI 模板，9 步自动化配方）
⑤ 验收（真机打开后弹出以模板名命名的参数框 = 铁证）
⑥ 打包交付（压缩包：pbit + PBIP 工程 + 原始数据 + 截图 + 提示词 + 说明，
   并写明需要的最低 Desktop 版本）
```

⛔ **硬规则：不要自造 PBIT**。已经三次撞墙（含按真实结构全量重做、补齐 `lineageTag`），Desktop 仍报「文件已损坏或版本无法识别」。尸检结论见 `references/pbit-export.md`。

### 技术栈

- **Power Query M**：清洗与转换层（技能方法论部分源自 [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development)，已针对本地 Desktop + 平面文件场景裁剪）
- **PBIP / TMDL / PBIR**：Power BI 工程化格式，纯文本、可被 MCP 离线读写（铁律：TMDL 文件必须 UTF-8 无 BOM）
- **Power BI MCP**（`mcp/powerbi-mcp/`）：Python MCP 服务端，82 个工具；TOM/ADOMD 连活模型、Desktop Bridge 命名管道热重载与逐页截图
- **Python 脚本**：PBIP 生成器、TOM 刷新脚本（`RequestRefresh(Full)` + `SaveChanges`）、ctypes PrintWindow 窗口截图兜底
- **本机 Desktop 专用**：不碰 Fabric 云端；Azure 云凭据为可选项

## 安装与使用

### 安装技能

把本仓库目录内容复制到你的技能目录下，文件夹名保持 `powerbi-crawler-data-prep`：

- WorkBuddy / CodeBuddy：`~/.workbuddy/skills/powerbi-crawler-data-prep/`
- Claude Code：`~/.claude/skills/powerbi-crawler-data-prep/`

重启会话后即可通过触发词自动匹配（如「爬虫数据进 Power BI」「导出 pbit」「写 Power Query M 代码」等）。

### 接入配套 Power BI MCP（可选，用于真机验证）

`mcp/` 目录下是本技能配套的 **Power BI MCP 服务端源码**（上游：[sulaiman013/powerbi-mcp](https://github.com/sulaiman013/powerbi-mcp)，本副本含 3 处本机补丁：桥接 args 契约、并发写锁、备份落 temp）。在 MCP 配置的 `mcpServers` 中加入：

```json
{
  "mcpServers": {
    "powerbi": {
      "command": "<你的 python 解释器路径>",
      "args": ["<本仓库路径>/mcp/powerbi-mcp/src/server.py"],
      "env": {
        "PYTHONPATH": "<本仓库路径>/mcp/powerbi-mcp/src",
        "ADOMD_DLL_PATH": "<你放置 ADOMD/TOM DLL 的目录>",
        "TOM_DLL_PATH": "<你放置 ADOMD/TOM DLL 的目录>"
      }
    }
  }
}
```

依赖说明：

- 只用「离线分析」能力（PBIP/TMDL/PBIR 编辑、BPA 审计、DAX 校验）→ `pip install -r requirements-core.txt`，**不需要 .NET**
- 要用「连活的 Power BI Desktop」能力（刷新、DAX 实测、桥接截图）→ `pip install -r requirements.txt`，需要 `pythonnet` + `pyadomd`
- ADOMD/TOM 的 .NET 程序集（约 97 MB，微软版权物）不随仓库分发，请从 NuGet 获取 `Microsoft.AnalysisServices.AdomdClient` 与 `Microsoft.AnalysisServices.Tabular`，解压取 `lib/` 下 DLL 放入上述目录

## 项目结构

```
powerbi-crawler-data-prep/
├── SKILL.md                                # 技能定义（触发词 + 完整方法论）
├── README.md                               # 本文件
├── README_EN.md                            # English README
├── references/                             # 参考文档（按「到哪一步了」查）
│   ├── pbit-export.md                      # ⭐ .pbit 真实内部结构 / 导出自动化 / 验收
│   ├── pbip-delivery.md                    # PBIP 结构 / TMDL 死线 / UTF-8 无 BOM / 离线校验
│   ├── powerbi-mcp.md                      # 真机验证：MCP 工具速查 / 验证链 / 本机补丁
│   ├── m-core.md                           # M 语言规范完整版
│   ├── sources-and-pipeline.md             # 三套入口模板 + Folder.Files 每日增量管道
│   ├── crawler-cleaning-patterns.md        # 字段映射 / 名称归一 / 文本转数值 / 去重模板
│   └── star-schema-and-dax.md              # 星型模型与 DAX（18 个度量值模板 + 排版坐标）
└── mcp/
    ├── README.md                           # 配套 MCP 接入说明
    └── powerbi-mcp/                        # Power BI MCP 服务端源码（82 个工具）
        ├── src/                            # server.py / desktop_bridge.py /
        │                                   # powerbi_pbip_connector.py（本机补丁）/
        │                                   # powerbi_tom_connector.py / security/ ...
        ├── config/policies.yaml            # 安全策略
        ├── docs/                           # ARCHITECTURE / TESTING / TOOLS
        ├── tests/                          # 25 个测试文件
        ├── requirements-core.txt           # 纯跨平台依赖（无需 .NET）
        └── requirements.txt                # 含 pythonnet / pyadomd（Windows 全功能）
```

## 注意事项

- **本地 Desktop 专用**：本技能不覆盖 Fabric 云端场景，云端验证相关内容已被裁剪
- **交付物是 `.pbit`，不是 `.pbix`，也不是 PBIP 文件夹**——PBIP 只是中间工程载体
- **交付必须打压缩包**：pbit + PBIP 工程 + 原始数据 + 截图 + 提示词 + 说明，并写明需要的最低 Desktop 版本；只发一个 pbit 文件 = 对方打不开时无路可退
- **兼容级别只能升不能降**（官方 `irreversible`），不要试图产出「向下兼容」的 pbit
- **MCP 无刷新工具**：刷新需用 TOM 脚本（`RequestRefresh(Full)` + `SaveChanges`）；`COUNTROWS` 返回 null = 从未刷新，不是模型错
- **MCP 补丁会随升级丢失**：3 处本机补丁（桥接 args 契约、并发写锁、备份落 temp）改动在 `mcp/powerbi-mcp/src/`，升级上游版本后需重打
- **桌面自动化细节**：打开模型后不要调整 Desktop 窗口尺寸（WebView 子窗口几何不跟随）；点后台面板用 `SendInput` 而非 `mouse_event`；坐标靠暗像素扫描 + `EnumChildWindows` 计算，不靠肉眼读截图
- `mcp/` 源码已做密钥体检，不含真实凭据；日志、缓存、数据库文件不入库

## License

**GPL-3.0**

本技能的 M 语言规范部分方法论源自 [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development)（GPL-3.0 协议）的 power-query 技能，已针对本地 Desktop + 平面文件场景裁剪（删除查询折叠、Fabric 云端验证等不适用内容）；爬虫数据清洗模式为原创补充。`mcp/powerbi-mcp/` 基于开源项目 [sulaiman013/powerbi-mcp](https://github.com/sulaiman013/powerbi-mcp) 修改。

## 作者

[sheen945](https://github.com/sheen945)
