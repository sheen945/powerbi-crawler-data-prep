# powerbi-crawler-data-prep

> 把爬虫抓来的多源数据（JSON/CSV/Excel 混杂）清洗进本地 Power BI Desktop 的完整链路：M 清洗流 → 星型模型（事实/维度、关系、计算列、度量值）→ 可直接双击打开的 PBIP 项目与多页看板 → 交付后用本机 Power BI MCP 连活模型真机验证（刷新/行数/勾稽/截图）。覆盖三类入口、每日增量管道、爬虫特有清洗、M 与 TMDL 工程规范（UTF-8 无 BOM 铁律）、PBIR 可视化与 pbit 导出限制。触发场景：爬虫数据进 Power BI、多格式合并、每日/每比赛日增量刷新、篮球/比赛数据清洗、CC指数/伤病/首发可视化、星型模型/维度建模/度量值/计算列、要在 Power BI 里直接看到/帮我打开 Power BI、做成 pbip/Power BI 项目/模板/pbit、Power BI MCP、写 Power Query M 代码。

## 安装

把本仓库的目录内容复制到你的技能目录下，文件夹名保持 `powerbi-crawler-data-prep`：

- WorkBuddy / CodeBuddy：`~/.workbuddy/skills/powerbi-crawler-data-prep/`
- Claude Code：`~/.claude/skills/powerbi-crawler-data-prep/`

重启会话后即可通过触发词自动匹配。

## 技能说明

以下为 `SKILL.md` 正文。

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

## 交付形态：给「能双击打开的项目」，不是一堆 M 文本

用户说「要在 Power BI 里能看到」时，**M 脚本文件不算交付**。正确做法是产出一个 **PBIP 项目**（纯文本工程，双击即在 Desktop 里打开，参数/表/关系/管道全部预置）：

- 文件清单：`.pbip` + `<名>.SemanticModel/definition/*.tmdl` + `<名>.Report/{definition.pbir,report.json}`
- 中间查询（不加载）写进 `expressions.tmdl`，表写进 `tables/*.tmdl`，列必须有 `sourceColumn`
- `model.tmdl` 必须有 `ref table`；`.pbip` 必须有 `$schema` 且 artifacts 只放 report
- ⛔ **全部文件必须 UTF-8 无 BOM**（TMDL 带 BOM 会让 Desktop 直接拒绝打开，报 `Only text with UTF8 encoding without BOM is supported`）
- **交付前用 `pbi-tools convert <definition文件夹> <输出> Tmdl` 过一遍官方 TOM 解析器**（退出码 0 = TMDL 语法合法），产物覆盖回项目后**记得剥掉 BOM**
- 完整模板、坑位清单、编码铁律、`.pbit` 走不通的替代方案 → `references/pbip-delivery.md`

## 交付后必须做：真机验证（本机 Power BI MCP）

**「文件看着对」不算交付**。产出 PBIP 后必跑这条链（细节、工具速查表、坑位、补丁说明全在 `references/powerbi-mcp.md`）：

1. 离线：`pbip_load_project` → `pbip_validate` → `pbir_validate_report`（三者全绿才继续）
2. 打开：`PBIDesktop.exe "<pbip 绝对路径>"`；**窗口标题变成项目名 = 打开成功**（「无标题」= 失败，去抓对话框看原因）
3. 连活模型：`desktop_discover_instances` 拿端口 → `desktop_connect` → `desktop_list_tables/columns`
4. 刷新：**MCP 没有刷新工具**，用脚本 `_tools/刷新并验证.py <端口>`（TOM `RequestRefresh(Full)` + `SaveChanges`）
5. 验数：`desktop_execute_dax` 查行数与勾稽；`COUNTROWS` 返回 null = 从未刷新，不是模型错
6. 截图：`bridge_status` → `bridge_screenshot`；桥接报「Host is not ready」= 窗口被最小化，先还原；桥接挂掉就用 `_tools/窗口截图3.py <pid>`（ctypes PrintWindow）

> 本机 MCP 已打 3 个补丁（桥接 `args` 契约、并发写锁、备份落 temp），改动在 `tools/powerbi-mcp/src/`，升级会丢——细节见 `references/powerbi-mcp.md` §5。

## 建模：星型模型 + 计算列 + 度量值（要点）

- 事实表存「发生了什么」、维度表存「属性」、中间查询不加载；**维度表从同一条事实管道派生**（刷新即同步）
- **只建 事实→维度 的关系**：事实表互连 = Desktop 报「不明确的路径」直接拒绝打开；角色扮演维度用 `isActive: false`
- 计算列只放**静态属性**（分档、标记）；一切聚合走**度量值**，且必须带 `格式串 + 显示文件夹 + 中文描述`
- 日期属性（年/季/月/星期）在维度的 M 里生成，别用 DAX 计算列
- 完整规范 + 18 个度量值模板 + 看板排版坐标 → `references/star-schema-and-dax.md`

## 参考文件

- `references/m-core.md` — M 语言核心规范完整版（命名、类型、反模式、调试法）
- `references/sources-and-pipeline.md` — JSON/CSV/Excel 三套入口模板 + Folder.Files 每日增量管道完整代码
- `references/crawler-cleaning-patterns.md` — 字段映射、名称归一、文本转数值、去重的完整代码模板
- `references/star-schema-and-dax.md` — 星型模型与 DAX 规范：表角色划分、关系铁律、计算列 vs 度量值、度量值模板、看板排版约定
- `references/pbip-delivery.md` — PBIP 工程怎么写：结构、各文件模板、编码铁律（无 BOM）、离线校验、PBIR 可视化、pbit 的真相
- `references/powerbi-mcp.md` — Power BI MCP 使用手册：工具速查、真机验证链、刷新缺口、报表创作坑、本机 3 处补丁、脚本清单

## 署名

本技能的 M 语言规范部分方法论源自 [data-goblin/power-bi-agentic-development](https://github.com/data-goblin/power-bi-agentic-development)（GPL-3.0 协议）的 power-query 技能，已针对本地 Desktop + 平面文件场景裁剪（删除查询折叠、Fabric 云端验证等不适用内容）；爬虫数据清洗模式为原创补充。

