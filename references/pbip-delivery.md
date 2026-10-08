# PBIP 工程（中间产物）怎么写

> 本文讲**过程产物 PBIP 工程**：它是纯文本，方便用 Python 生成、用 MCP 离线改模型和报表。
> ⭐ **最终交付物是 `.pbit`**（2026-10 用户定规），导出方法、真实结构与自动化边界见 `pbit-export.md`。
> 本文全部内容在 Windows + Power BI Desktop 26.09 实测跑通（2026-10）。

## 为什么先做 PBIP，再导出 PBIT

- `.pbix` / `.pbit` **都是二进制 OPC 包，无法离线手写**（试过两次，见 `pbit-export.md` §2）。
- `.pbip` 是 **100% 纯文本工程**：模型用 TMDL，报表用 PBIR JSON，全部可以用文本工具生成，Desktop 原生支持双击打开。
- 所以链路是：**文本生成 PBIP → 真机验证 → Desktop 自己导出成 `.pbit` 交付**。
- 用户想要单文件可编辑版：在 Desktop 里「文件 → 另存为 `.pbix`」。

## 文件夹结构（实测可用）

```
<项目名>/
├── <项目名>.pbip                        ← 双击这个
├── .gitignore
├── <项目名>.SemanticModel/
│   ├── definition.pbism
│   └── definition/
│       ├── database.tmdl                ← compatibilityLevel
│       ├── model.tmdl                   ← culture + ref table 列表
│       ├── expressions.tmdl             ← 参数 / 自定义函数 / 不加载的中间查询
│       ├── relationships.tmdl
│       └── tables/
│           ├── <表1>.tmdl               ← 列定义 + partition 的 M
│           └── <表2>.tmdl
└── <项目名>.Report/
    ├── definition.pbir
    └── definition/                       ← PBIR 增强格式（要加可视化就必用；legacy 单 report.json 与它互斥）
        ├── report.json
        ├── version.json
        └── pages/                        ← 页面与视觉对象都放这里
```

## 各文件模板

### `<项目名>.pbip`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  "version": "1.0",
  "artifacts": [
    { "report": { "path": "<项目名>.Report" } }
  ],
  "settings": { "enableAutoRecovery": true }
}
```

**坑（实测）**：`$schema` 是必填；`artifacts` 里**只能有 report 一项**（schema `additionalProperties: false`），多写 `semanticModel` 会让 Desktop 拒绝打开模型。模型是靠 `definition.pbir` 里的 `byPath` 相对路径找到的。

### `definition.pbism`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  "version": "4.0",
  "settings": {}
}
```

### `definition.pbir`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
  "version": "4.0",
  "datasetReference": { "byPath": { "path": "../<项目名>.SemanticModel" } }
}
```

### TMDL 关键规则

`database.tmdl`：

```tmdl
database Database
	compatibilityLevel: 1567
```

`model.tmdl`（**必须有 `ref table`，否则表不进模型**）：

```tmdl
model Model
	culture: zh-CN
	defaultPowerBIDataSourceVersion: powerBI_V3
	sourceQueryCulture: zh-CN
	dataAccessOptions
		legacyRedirects
		returnErrorValuesAsNull

annotation __PBI_TimeIntelligenceEnabled = 0

annotation PBI_QueryOrder = ["表1","表2"]

ref table 表1
ref table 表2
```

⛔ **`annotation` 和 `ref table` 必须顶格（第 0 列）**，只有属性行（`culture:` 等）缩进一个 tab。缩进一级会被当成上一行 `annotation` 的子对象 → `Parsing error type - InvalidLineType / Unexpected line type: ReferenceObject!`。顶格语句之间**留空行**。

`expressions.tmdl`（参数 / 函数 / 不加载的中间查询）：

```tmdl
expression 数据文件夹路径 = "D:\爬虫数据" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression 清洗单CSV =
		(Content as binary, 文件名 as text) =>
		let
		    ...
		in
		    结果

expression 比赛宽表 =
		let
		    ...
		in
		    去重

	annotation PBI_ResultType = Table
```

- **表达式名不加引号**（`expression 比赛宽表 =`）：中文标识符可直接解析，加 `'…'` 也能读但没必要。
- **不加载到模型的中间查询**（Desktop 里「启用加载」不勾）在 PBIP 里就是 `expressions.tmdl` 的 shared expression，别的 partition 直接按名字引用它（如 `源 = 比赛宽表`）。
- **多行 M 的缩进**：属性行（`= `）之后的 M 体要**深于**随后的 `annotation`（M 体 2 tab、annotation 1 tab），并且两者之间**留一个空行**最稳。反过来（M 体与 annotation 同级）会被吞进 M 文本报语法错。
- 参数加 `IsParameterQueryRequired=true`，Desktop 打开时会弹框让用户确认路径 —— 模板交付正需要这个行为。

`tables/<表名>.tmdl`：

```tmdl
table 比赛数据

	column 编号
		dataType: int64
		summarizeBy: none
		sourceColumn: 编号

	column 比赛日期
		dataType: dateTime
		formatString: Short Date
		summarizeBy: none
		sourceColumn: 比赛日期

	partition 比赛数据 = m
		mode: import
		source =
			let
			    源 = 比赛宽表,
			    选列 = Table.SelectColumns(源, {...})
			in
			    选列

	annotation PBI_ResultType = Table
```

- 每个列都要 `sourceColumn` 绑定 **M 输出的列名**（不是显示名），名字对不上刷新就报错。
- `dataType` 用 TOM 名称：`int64` / `double` / `string` / `dateTime` / `boolean`，**没有 `date`**（日期列写 `dateTime` + `formatString: Short Date`）。
- 编号、ID 这类列必须 `summarizeBy: none`，否则仪表盘上会被自动求和；分数类用 `summarizeBy: sum`。
- partition 的 M **不能只写一个裸查询名**，要包成完整 `let … in …`：

```tmdl
	partition 比赛数据 = m
		mode: import
		source =
			let
			    源 = 比赛宽表
			in
			    源
```

- 关系写在 `relationships.tmdl`（**方向必须是 事实 → 维度**）：

```tmdl
relationship <guid>
	fromColumn: 事实表.维度键

	toColumn: 维度表.键

relationship <guid>
	isActive: false
	fromColumn: 事实表.客队
	toColumn: 维度表.球队
```

⛔ `isActive: false` 写在 `fromColumn` **之前**（官方序列化顺序），并且与上一条之间留空行。

### report.json（legacy 报表，最小可用）

```json
{
  "config": "{\"version\":\"5.43\",\"activeSectionIndex\":0,\"defaultDrillFilterOtherVisuals\":true,\"settings\":{\"useNewFilterPaneExperience\":true,\"allowChangeFilterTypes\":true,\"useStylableVisualContainerHeader\":true,\"exportDataMode\":1}}",
  "layoutOptimization": 0,
  "publicCustomVisuals": [],
  "resourcePackages": [],
  "sections": [
    {
      "config": "{}",
      "displayName": "概览",
      "displayOption": 1,
      "filters": "[]",
      "height": 720,
      "name": "ReportSection",
      "ordinal": 0,
      "visualContainers": [],
      "width": 1280
    }
  ],
  "settings": {}
}
```

`config` / `filters` / 页面 `config` 都是**字符串化的 JSON**（不是嵌套对象）。视觉对象（visualContainers）留空 —— 空页面不影响打开，用户自己拖字段更快。

## 交付前离线校验（必做）

### 1. 用官方 TOM 解析器验 TMDL（关键一步）

```bash
gh release download -R pbi-tools/pbi-tools -p "pbi-tools.1.2.0.zip" -D <工具目录>
# 解压出 pbi-tools.exe（单文件，需 .NET Framework 4.7.2+）

pbi-tools.exe convert "<项目>\<名>.SemanticModel\definition" "<输出目录>" Tmdl -overwrite
```

- `convert` 会把 TMDL **读进 TOM 再重新序列化**（产物字节会变，会补 `ref table`、去掉默认属性），**退出码 0 = 语法合法**。
- 更好：把 convert 的产物**覆盖回项目**，这样模型文件就是官方序列化器产出。
- ⚠️ **但 convert 的产物带 UTF-8 BOM，必须手工剥掉再用**（见下节「编码铁律」）。Desktop 26.09 对 TMDL 的 BOM 是**零容忍**的：
  `Cannot read '...\definition\database.tmdl'. Only text with UTF8 encoding without BOM (byte order marks) is supported. Detected BOM: 'UTF-8'`
  这条坑我是真踩过的——覆盖回项目后没有去 BOM，用户双击直接打不开（2026-10-01 实测）。
- 注意：`convert` 的 source 必须是 **`definition` 文件夹本身**（不是 `.SemanticModel`）。

### 编码铁律（Power BI Desktop 26.09 实测）

| 文件 | 编码 | BOM | 换行 |
| --- | --- | --- | --- |
| `*.tmdl`（模型定义） | UTF-8 | **绝对不要有 BOM** | CRLF/LF 都可以 |
| `.pbip` / `definition.pbir` / `definition.pbism` | UTF-8 | 不要 BOM | LF 可以 |
| `report.json` | UTF-8 | 不要 BOM | LF 可以 |

一律按「UTF-8 无 BOM」交付，最省事：

```python
# 剥 BOM（对所有项目文件跑一遍）
import glob, os
for p in glob.glob(PROJ + '/**/*', recursive=True):
    if os.path.isfile(p):
        b = open(p, 'rb').read()
        if b.startswith(b'\xef\xbb\xbf'):
            open(p, 'wb').write(b[3:])
```

不要照抄「技能文件统一 LF」的习惯去动 TMDL 的换行（没必要），**BOM 才是必须处理的**。

### 2. 结构自检脚本

用 Python 过一遍：JSON 能否解析、`.pbip` 的 `$schema`/artifacts 要件、`definition.pbir` 的 byPath 能否解析到目录、`model.tmdl` 有 `ref table`、每个 `column` 都有 `sourceColumn`、列数与 M 输出一致、关系两端的表名存在。脚本样例见本项目 `_tools\自检脚本.py`。

### 3. 官方 JSON Schema 位置

`github.com/microsoft/json-schemas`：`fabric/pbip/pbipProperties/1.0.0/`、`fabric/item/report/definitionProperties/1.0.0/`、`fabric/item/semanticModel/definitionProperties/1.0.0/`。版本号写错会打不开，用这些 schema 核对。

## 离线生成 .pbit / .pbix：走不通

- `pbi-tools compile` 打包那步要调 Desktop 的 `Microsoft.PowerBI.Packaging.PowerBIPackager.Save(...)`，**Desktop 26.09 签名已变** → `MissingMethodException`（pbi-tools 停在 2025-01，无解）。
- 手拼 OPC 包也不行，试过两次都撞墙。
- **要 `.pbit` 只有一个来源：Desktop 自己导出**（文件 → 导出 → Power BI 模板）→ 完整结构、尸检结论与自动化配方见 `pbit-export.md`。
- 要单文件 `.pbix` 则用「文件 → 另存为」，或在导出流程里选「Power BI 文件」。

## 给报告加可视化（PBIR 增强格式）

**MCP 的 `pbir_add_page` / `pbir_add_visual` 只能用于 PBIR 增强格式**（判定条件：`<名>.Report/definition/pages/` 目录存在）。
旧版（单个 `report.json`）要先把报告层换成增强格式——两者**互斥**，`report.json` 必须删掉。

最小可用的增强格式骨架（实测 Desktop 26.09 可加载）：

```
<名>.Report/
├── definition.pbir            ← 不用动（version 4.0 + byPath 引用模型）
└── definition/
    ├── report.json            ← {"$schema": ".../report/3.3.0/schema.json", "themeCollection": {}}
    ├── version.json           ← {"$schema": ".../versionMetadata/1.0.0/schema.json", "version": "2.0.0"}
    └── pages/                 ← 空目录即可，MCP 的 pbir_add_page 会往里写
```

- `report.json` 的必填项只有 `$schema` + `themeCollection`（可以是空对象，主题走默认）
- `version.json` 的 `version` 形如 `major.minor.0`（patch 必须为 0）
- 骨架建好后：`pbip_load_project` → `pbip_add_measures`（离线加度量值）→ 再 `pbip_load_project` 一次（否则新度量值对视觉对象不可见）→ `pbir_add_page` → `pbir_add_visual` → `pbir_validate_report`

### 两个必须知道的坑（实测，细节见 `powerbi-mcp.md` §4）

1. **值角色里的文本列会被包成聚合**。`pbir_add_visual` 对 `Values`/`Y` 这类角色会给列自动套聚合（数值 Sum、文本 CountNonNull），结果明细表/切片器会显示成「比赛日期的计数」这种鬼东西。
   修法：传**显式投影规格**并用 `pbir_bind_fields` 的 `replace` 模式重绑：

   ```json
   {"Values": [{"table": "比赛数据", "field": "比赛日期", "kind": "Column"},
               {"table": "比赛数据", "field": "主队",     "kind": "Column"}]}
   ```

   （dict 形式会被原样透传，不再套聚合；度量值绑定时不需要 dict，MCP 能自己识别成 Measure）

2. **一条角色只放一个字段**。实测一条角色给多个字段时只渲染第一个（`tableEx` 7 列只出 1 列、矩阵 5 个 Rows 只出 1 个）。
   要"表格"效果用 `pivotTable`（Rows 一个维度 + Columns 日期 + Values 单指标），**别用 `tableEx`**（只渲染第一列）。
   真要多列明细，让用户在 Desktop 里拖一次字段，Power BI 自己会写对格式。

> 桌面桥接的参数契约（`{"args": {...}}`）、窗口最小化导致桥接不可用、以及本机已打的补丁 → `powerbi-mcp.md`

## 星型模型铁律：事实表之间不要建关系

从「宽表 + 明细表直连」升级成星型模型时，最容易踩的坑是**保留原来那条事实表对事实表的 relationship**。

实测后果：Desktop 打开项目直接弹「**发现问题**」对话框，原文是
`"首发名单"和"维度_日期"之间存在不明确的路径: '首发名单'->'比赛数据'->'维度_日期' 和 '首发名单'->'维度_日期'`
—— 因为事实 A 直连事实 B，又都连同一张维度，维度就有了两条路径，模型直接不合法。

正确做法：**只保留 事实→维度 的关系**（共享维度可以同时连多张事实表），事实表之间的业务关联通过共享维度表达。改完 Desktop 一次通过。
（角色扮演维度：同一张维度表连同一张事实表两次可以，一条 active、一条 `isActive: false`，不构成路径冲突。）

## `.pbit` 导出 → 见 `pbit-export.md`

这里是**过程产物**（PBIP）的文档。最终交付物的全部内容——真实 PBIT 的部件结构（26.09 已无 `DataMashup`，改用 `UnappliedChanges`）、手搓为什么不行、Desktop 导出的自动化能力边界、UI 坐标标定与控件定位、导出后验收、交付话术——**都在 `references/pbit-export.md`**，本文不再重复。

一句话版：**别自造，用 Desktop「文件 → 导出 → Power BI 模板」。**

## 给用户的交付话术模板

**交付物是 `.pbit`**（过程版的 PBIP 可以一并留着，方便以后改）：

> 双击 `<项目名>-数据清洗模板.pbit` → Power BI Desktop 会用模板新建报表 → 弹参数框时把「数据文件路径」指到原始数据文件 → 确定 → 主页点「刷新」（约 2 万行，1~2 分钟）→ 三页看板就有数据了。想存成可编辑单文件：文件 → 另存为 `.pbix`。

（PBIP 版本也可以留着做开发用：双击 `<项目名>.pbip` 即可，两者内容一致。）

## TMDL 格式死线速查（错一条 `pbi-tools convert` 就抛 `TmdlFormatException`）

上面的示例已经是正确写法，这里是**逐条自查清单**：

| # | 死线 | 错了会怎样 |
| --- | --- | --- |
| 1 | `annotation` / `ref table` **顶格**（第 0 列），只有属性行缩进；顶格语句之间留空行 | `Parsing error type - InvalidLineType / Unexpected line type: ReferenceObject!` |
| 2 | 表达式名**不加引号**：`expression 比赛宽表 =` | —（加 `'…'` 也能读，但没必要） |
| 3 | `isActive: false` 写在 `fromColumn` **之前** | —（官方序列化顺序） |
| 4 | 多行 M 体缩进**深于**随后的 `annotation`（M 体 2 tab、annotation 1 tab），两者间留空行 | annotation 被吞进 M 文本 → 语法错 |
| 5 | partition 的 M 要包成完整 `let … in …`，不能只写裸查询名 | 解析不过 |
| 6 | `dataType` **没有 `date`**，日期用 `dateTime` + `formatString: Short Date` | — |

**最稳的参照物是本机已跑通的项目**（`WorkBuddy/<示例项目>/PowerBI项目-篮球比赛数据-20260930`）：照抄它的缩进与字段顺序，比查 schema 快得多。

### 生成与校验流程（Python 生成器 + 官方序列化器回灌）

```
① Python 生成器：列清单作为唯一数据源，同时驱动 M 代码与 TMDL 列定义（82 列手写必错）
② 全部文件 UTF-8 无 BOM（BOM 会让 Desktop 26.09 直接拒收）
③ pbi-tools convert "<项目>\<名>.SemanticModel\definition" <临时输出> Tmdl -overwrite
④ 剥掉输出文件开头的 BOM，再覆盖回项目 → 模型层就是官方序列化器产物
⑤ 结构自检：JSON 可解析 / byPath 解析得到 .SemanticModel / ref table 与 tables\ 一致 /
   sourceColumn 无重复 / 关系端点表存在且方向为 事实→维度
```

- `pbi-tools convert` 的输入必须是 `definition` 文件夹**本身**；退出码 0 且无异常栈 = TMDL 合法。
- 它会顺手归一化（`isKey: true` → `isKey`、M 体多缩进一级），属正常，M 代码逐字保留。
- 实测 `annotation PBI_ResultType = Function` 对自定义函数是合法的，会被保留。

## 真机验证与逐页取证 → 见 `powerbi-mcp.md`

Desktop Bridge（热重载 `file.reload/v1`、按 pageId 截图 `report.snapshot.capture/v2`）、AS 端口怎么找（**别用 `netstat`**）、截图三招、本机补丁、脚本清单，**统一放在 `references/powerbi-mcp.md`**，本文不重复。
