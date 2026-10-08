---
name: powerbi-crawler-data-prep
description: 把爬虫抓来的多源数据（JSON/CSV/Excel 混杂）清洗进本地 Power BI Desktop 的完整链路：M 清洗流 → 星型模型（事实/维度、关系、计算列、度量值）→ 多页看板 → **最终交付 .pbit 模板**（2026-10 定规，PBIP 只是中间工程）→ 交付后用本机 Power BI MCP 连活模型真机验证（刷新/行数/勾稽/逐页截图）。覆盖三类入口、每日增量管道、爬虫特有清洗、M 与 TMDL 工程规范（UTF-8 无 BOM 铁律）、PBIR 可视化、PBIT 真实内部结构与 Desktop 导出自动化的能力边界。触发场景：爬虫数据进 Power BI、多格式合并、每日/每比赛日增量刷新、篮球/比赛数据清洗、CC指数/伤病/首发可视化、星型模型/维度建模/度量值/计算列、要在 Power BI 里直接看到/帮我打开 Power BI、做成 pbip/Power BI 项目/模板/pbit、导出 pbit、Power BI MCP、写 Power Query M 代码。
license: GPL-3.0（方法论部分源自 data-goblin/power-bi-agentic-development，爬虫模式为原创补充）
---

# 爬虫数据清洗进 Power BI（本地 Desktop 专用）

## 适用场景

- 数据由网络爬虫抓取，格式混杂（JSON / CSV / Excel 同时存在）
- 本地 Power BI Desktop，不碰 Fabric 云端
- 每天/每比赛日增量更新，爬虫持续产出新文件
- 典型字段：比赛日期、球队、球员、CC指数、伤病情况、首发情况

## 铁律（本项目环境已验证的前提）

1. **查询折叠不存在**。平面文件（JSON/CSV/Excel）没有查询引擎，所有折叠知识不适用，性能优化只能靠「列裁剪尽早、行过滤尽早」。
2. **爬虫数据永远脏**。列名不统一、数字存成文本、同一名称多种写法，清洗步骤一个都不能省。
3. **每日增量 = 文件夹连接器**。爬虫每天把新文件丢进同一个文件夹，Power BI 用 `Folder.Files` 自动合并全部文件，用户动作只有「跑爬虫 → 丢文件 → 点刷新」。
4. **去重键必须显式定义**。爬虫重复抓取是常态，按「比赛日期 + 球员」（或业务主键）去重，防止重复导入。

## 标准工作流（五步走）

### 第 1 步：统一入口

爬虫文件三种格式，各用一个入口查询，统一列结构后再合并：

- JSON → `Json.Document`
- CSV → `Csv.Document`
- Excel → `Excel.Workbook`

三套完整模板见 `references/sources-and-pipeline.md`。

### 第 2 步：合并多源

三路统一列名、列序、类型后 `Table.Combine` 纵向拼接（Append）。列不一致时先在各自入口里补齐缺失列（补 null），再合并。

### 第 3 步：爬虫特有清洗

按固定顺序处理（完整代码见 `references/crawler-cleaning-patterns.md`）：

1. **字段映射**：用映射表 `Table.RenameColumns` 一步批量改名，禁止一列一个步骤
2. **名称归一**：球队/球员别名表合并查询（如「湖人」「洛杉矶湖人」「LAL」统一为一个标准名）
3. **文本转数值**：CC指数这类字段爬虫常存成文本，用 `Number.FromText` 配合 `try...otherwise null` 显式转换，异常值变 null 而不是报错
4. **缺失值标记**：关键字段为 null 的行，宁可加「是否缺失」标记列也不直接删，方便后续排查爬虫问题

### 第 4 步：每日增量管道

`Folder.Files(数据文件夹)` 列出全部文件 → 按扩展名分流到对应入口函数 → 合并 → 去重。详见 `references/sources-and-pipeline.md` 的增量管道章节。

### 第 5 步：验证

改完任何 M 代码，过一遍检查清单（见下文）。

## M 语言核心规范（每题必过，压缩版）

完整版见 `references/m-core.md`，以下是最高频的 8 条：

1. **结构**：`let ... in` 步骤链，每步一个命名变量；步骤名带空格/中文时用 `#"步骤名"` 引用
2. **命名**：步骤名说人话（`筛选有效比赛`，不要 `Step3`）；查询名 = 业务表名（`球员CC指数`）
3. **类型尽早转**：入口之后立刻 `Table.TransformColumnTypes`，常用类型：`type text`、`type date`、`Int64.Type`、`type number`、`type logical`
4. **批量改名**：多列重命名必须一步 `Table.RenameColumns(上一步, {{"旧名1","新名1"},{"旧名2","新名2"}})`，禁止逐列一个步骤
5. **裁剪尽早**：`Table.SelectColumns` 只留可视化要的列，`Table.SelectRows` 只留要的行，都放在链条前段
6. **别滥用 `Table.Buffer`**：平面文件场景基本不需要，加了反而妨碍引擎优化
7. **分步调试**：报错或结果不对时，把 `in` 后面的步骤名改成中间某一步，逐段预览数据定位问题
8. **错误处理要显式**：转换可能失败的字段用 `each try Number.FromText([字段]) otherwise null`，让错误变成可见的 null，而不是静默吞掉或整表报错

## 常见反模式（踩坑清单）

- 整表拉进来再过滤 → 列裁剪和行过滤必须尽早
- 一列一个改名步骤 → 一步 `Table.RenameColumns` 批量搞定
- 数字字段没转类型 → 可视化求和直接报错或结果错
- 用 `try...otherwise` 包住整段查询 → 错误被静默吞掉，排查无门；只包单个字段的转换
- 跨查询层层引用 → 一个查询依赖五六个中间查询，刷新慢且难维护；能合并就合并
- 不做去重 → 爬虫重抓导致数据翻倍

## 交付前检查清单（本地 Desktop 版）

1. **语法**：粘贴进高级编辑器无红色报错
2. **数据**：预览结果列名、列数符合预期
3. **类型**：每列类型正确（CC指数必须是数值型，不是 ABC 文本）
4. **空值**：关键字段空值数量符合预期（爬虫缺数据是常态，但要心里有数）
5. **行数**：去重后行数合理，新丢一天的文件后行数增量正确

## 交付形态：`.pbit`（唯一交付格式，2026-10-07 用户定规）

**用户说的「清洗完的那个文件」= `.pbit` 模板。** PBIP 只是过程中的工程载体（纯文本、方便用 MCP 离线改模型和报表），最终**必须导出成 `.pbit` 交出去**。

固定顺序（不要跳步、不要改序）：

```
① 生成 PBIP 工程 —— Python 生成器，列清单同时驱动 M 代码与 TMDL 列定义（列一多手写必错）
② 离线校验 —— pbip_load_project → pbip_validate → pbir_validate_report（三者全绿才继续）
③ 真机验证 —— 打开 Desktop → TOM 刷新 → DAX 验行数/勾稽（见 powerbi-mcp.md）
④ 导出 PBIT —— 文件 → 导出 → Power BI 模板（**全流程可自动**，9 步配方见 `pbit-export.md` §3.2）
⑤ 验收 —— 部件齐全 + 真机打开后弹出「以模板名命名的参数框」（这才是有效的铁证）
⑥ 打包交付 —— 打**压缩包**（pbit + PBIP 工程 + 原始数据 + 截图 + 提示词 + 说明），**并在说明里写明需要的最低 Desktop 版本**
   （只发一个 pbit 文件 = 对方打不开时无路可退。跨版本处置见 `pbit-export.md` §6）
```

⛔ **硬规则：不要自造 PBIT。** 已经两次撞墙（含按真实结构全量重做、补齐 `lineageTag`）——尸检结论见 `references/pbit-export.md` §2，别再花时间。

- PBIP 侧要求（结构、TMDL 格式死线、UTF-8 无 BOM 铁律）→ `references/pbip-delivery.md`
- PBIT 侧一切（真实内部结构、导出自动化、坐标标定）→ `references/pbit-export.md`

## ⏱ 省时间清单：这些坑已经踩透，别再探索

| 别再做 | 为什么 | 直接做什么 |
| --- | --- | --- |
| 自造 / 手拼 `.pbit` | 三次撞墙（含按真结构重做 + 补 lineageTag），Desktop 26.09 仍报「文件已损坏或版本无法识别」 | 走 Desktop「文件 → 导出 → Power BI 模板」 |
| `pbi-tools compile → pbit` | 打包接口签名变了，`MissingMethodException`；且它要 PbixProj 目录不是 TMDL 目录 | 同上 |
| 用 `mouse_event` 点 Desktop 的 File 后台面板 | 面板收不到旧 API 的合成输入，点了没反应 | 换 `SendInput`（`pbit-export.md` §4.1） |
| 靠肉眼读截图估坐标 | Read 工具的渲染缩放比未知，必错（实测浪费最多时间的一条） | 暗像素扫描 + `EnumChildWindows` 算包围盒 |
| 打开模型后调整 Desktop 窗口尺寸 | WebView 子窗口几何不跟着变，后面点击全乱 | 一开始定好尺寸，或全程用最大化 |
| `netstat` 找 Desktop 的 AS 端口 | 沙箱里拿不到 LISTENING 行 | MCP `desktop_discover_instances` |
| `python -c` 跑含 `\.\pipe\` 的桥接脚本 | bash 吃掉反斜杠 → 假报"管道不存在" | 写成 `.py` 文件再跑 |
| 追求 Desktop 导出 100% 无人值守 | **已跑通**：导出全流程（含点「保存」）都能自动；只有**打开 pbit 后那个参数框**是 IE 控件填不进去 | 导出用 `pbit-export.md` §3.2 的 9 步配方；参数填写交给用户 1~2 次操作 |
| 交付 pbit 时不写版本要求 | **对方十有八九打不开**（报「此文件与当前版本的 Power BI Desktop 不兼容」），然后回来找你返工。根因是文件太新，不是你做错了 | 交付说明里写明「需要的最低版本」+ 附一份**重建提示词**和**完整 PBIP 工程**（`pbit-export.md` §6）；对方有事还有退路 |
| 试图产出「向下兼容」的 pbit | 兼容级别只能升不能降（官方 `irreversible`），报表又是新版 PBIR 2.0.0 格式，翻译回去=重画；本机只有新版无法验证 | 老实走 §6.4：让对方重建（首选）或升级 Desktop |
| 只发一个 pbit 文件过去 | IM 传输可能截断，且对方缺数据、缺说明、缺退路 | 打**压缩包**：pbit + PBIP 工程 + 原始数据 + 截图 + 提示词 + 说明 |

## 交付后必须做：真机验证（本机 Power BI MCP）

**「文件看着对」不算交付**。产出 PBIP 后必跑这条链（细节、工具速查表、坑位、补丁说明全在 `references/powerbi-mcp.md`）：

1. 离线：`pbip_load_project` → `pbip_validate` → `pbir_validate_report`（三者全绿才继续）
2. 打开：`PBIDesktop.exe "<pbip 绝对路径>"`；**窗口标题变成项目名 = 打开成功**（「无标题」= 失败，去抓对话框看原因）
3. 连活模型：`desktop_discover_instances` 拿端口 → `desktop_connect` → `desktop_list_tables/columns`
4. 刷新：**MCP 没有刷新工具**，用脚本 `_tools/刷新并验证.py <端口>`（TOM `RequestRefresh(Full)` + `SaveChanges`）
5. 验数：`desktop_execute_dax` 查行数与勾稽；`COUNTROWS` 返回 null = 从未刷新，不是模型错
6. 截图：**逐页**取证用 Desktop Bridge（`file.reload/v1` 热重载 + `report.snapshot.capture/v2` 按 pageId 截图，最干净）；桥接报「Host is not ready」= 窗口被最小化或有模态框，先还原；桥接挂掉就用 `_tools/窗口截图3.py <pid>`（ctypes PrintWindow）
7. **导出 PBIT 后再验一次**：打开 pbit，用 Bridge `application.state.get/v1` 看 `currentFilePath` 必须指向这个 pbit（空 = 没真打开）→ 见 `pbit-export.md` §5

> 本机 MCP 已打 3 个补丁（桥接 `args` 契约、并发写锁、备份落 temp），改动在 `tools/powerbi-mcp/src/`，升级会丢——细节见 `references/powerbi-mcp.md` §5。

## 建模：星型模型 + 计算列 + 度量值（要点）

- 事实表存「发生了什么」、维度表存「属性」、中间查询不加载；**维度表从同一条事实管道派生**（刷新即同步）
- **只建 事实→维度 的关系**：事实表互连 = Desktop 报「不明确的路径」直接拒绝打开；角色扮演维度用 `isActive: false`
- 计算列只放**静态属性**（分档、标记）；一切聚合走**度量值**，且必须带 `格式串 + 显示文件夹 + 中文描述`
- 日期属性（年/季/月/星期）在维度的 M 里生成，别用 DAX 计算列
- 完整规范 + 18 个度量值模板 + 看板排版坐标 → `references/star-schema-and-dax.md`

## 参考文件

按「到哪一步了」查：

| 阶段 | 看哪个 |
| --- | --- |
| **交付物 = .pbit**（真实内部结构、导出自动化边界、坐标标定、验收） | `references/pbit-export.md` ⭐ |
| 中间产物 PBIP 怎么写（结构、模板、TMDL 格式死线、无 BOM、离线校验、PBIR 可视化） | `references/pbip-delivery.md` |
| 真机验证（MCP 工具速查、验证链、刷新缺口、本机补丁、脚本清单） | `references/powerbi-mcp.md` |
| M 语言规范（命名、类型、反模式、调试法） | `references/m-core.md` |
| 三套入口模板 + Folder.Files 每日增量管道 | `references/sources-and-pipeline.md` |
| 字段映射、名称归一、文本转数值、去重代码模板 | `references/crawler-cleaning-patterns.md` |
| 星型模型与 DAX（关系铁律、计算列 vs 度量值、度量值模板、看板排版） | `references/star-schema-and-dax.md` |

## 署名

本技能的 M 语言规范部分方法论源自 [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development)（GPL-3.0 协议）的 power-query 技能，已针对本地 Desktop + 平面文件场景裁剪（删除查询折叠、Fabric 云端验证等不适用内容）；爬虫数据清洗模式为原创补充。
