# 交付形态：能双击打开的 Power BI 项目（PBIP）

> 目标：不用让用户在 Power BI 里手动建查询，直接给他一个**双击就在 Power BI Desktop 里打开、点刷新就有数据**的产物。
> 本文全部内容在 Windows + Power BI Desktop 26.09 实测跑通（2026-10）。

## 为什么是 PBIP（Power BI 项目）而不是 .pbix / .pbit

- `.pbix` / `.pbit` **都是二进制 OPC 包，无法离线手写**；`pbi-tools compile` 生成时要用到 Desktop 自带的打包接口（见文末限制）。
- `.pbip` 是 **100% 纯文本工程**：模型用 TMDL，报表用 report.json，全部可以用文本工具生成，Desktop 原生支持双击打开。
- 想要单文件 `.pbix`：让用户在 Desktop 里「文件 → 另存为」即可（PBIP ↔ PBIX 可互相另存）。

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
    └── report.json                      ← legacy 报表格式，最小可用
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

`expressions.tmdl`（参数 / 函数 / 不加载的中间查询）：

```tmdl
expression '数据文件夹路径' = "D:\爬虫数据" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression '清洗单CSV' =
		(Content as binary, 文件名 as text) =>
		let
		    ...
		in
		    结果

expression '比赛宽表' =
		let
		    ...
		in
		    去重
	annotation PBI_ResultType = Table
```

- **不加载到模型的中间查询**（Desktop 里「启用加载」不勾）在 PBIP 里就是 `expressions.tmdl` 的 shared expression，别的 partition 直接按名字引用它（如 `源 = 比赛宽表`）。
- **多行 M 的缩进**：属性行（`= `）之后至少再缩进一级；要跟 `annotation` 同级会被吞进 M 文本里报语法错。
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
- `dataType` 用 TOM 名称：`int64` / `double` / `string` / `dateTime` / `boolean`。
- 编号、ID 这类列必须 `summarizeBy: none`，否则仪表盘上会被自动求和；分数类用 `summarizeBy: sum`。
- 关系写在 `relationships.tmdl`：

```tmdl
relationship <guid>
	fromColumn: 首发名单.编号
	toColumn: 比赛数据.编号
```

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

## 已知限制：离线生成 .pbit/.pbix

- `pbi-tools compile <PbixProj> <out.pbit> PBIT` 需要 PbixProj 结构（`Version.txt` + `Report/report.json`+`config.json`+`sections/` + `ReportMetadata.json` + `ReportSettings.json` + `Model/`），这些都能手写（骨架留在 `_tools\pbixproj-build\`）。
- 但打包那一步会调 Desktop 自带的 `Microsoft.PowerBI.Packaging.PowerBIPackager.Save(...)`，**新版 Desktop（26.09 实测）签名已变**，pbi-tools 1.2.0（2025-01，最后一版）抛 `MissingMethodException`。
- **想要 .pbit 就别走这条路**：唯一可靠方式是让 Desktop 自己导出（文件 → 导出 → Power BI 模板），详见下文「导出 .pbit 的真相」。要单文件 .pbix 则用「文件 → 另存为」。

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

## 导出 .pbit 的真相（2026-10 实测）

### PBIT 内部结构（解剖自真实包）

```
Version          UTF-16LE 的版本号（如 "1.12"/"1.25"，8 字节）
DataModelSchema  UTF-16LE 的 TMSL JSON —— PBIT 的关键：模型是文本，且 M 代码内联在分区的 source.expression 里
DataMashup       二进制：8 字节头（4 字节 0 + 4 字节长度）+ zip（Config/Package.xml + [Content_Types].xml + Formulas/Section1.m）
Report/...       报表部件（legacy 是单个 Report/Layout，UTF-16LE JSON）
Settings / Metadata / DiagramState / SecurityBindings  小部件
[Content_Types].xml
```

`pbi-tools convert <definition文件夹> <输出> Raw` 导出的 `model.bim` **自带内联 M**（`source.expression` 是字符串数组），是造 PBIT/模板的现成料。

### 但这两条路都走不通（别重复踩）

1. **pbi-tools compile → PBIT**：打包那步要调 Desktop 的 `Microsoft.PowerBI.Packaging.PowerBIPackager.Save(...)`，新版 Desktop（26.09 实测）签名已变 → `MissingMethodException`；pbi-tools 最新版停在 2025-01，无解。
2. **手工构造 PBIT 包**：即使补齐 DataMashup、写上真实 OPC 内容类型、对齐 UTF-16LE 编码，Desktop 26.09 仍报「**无法打开模板：文件可能已加密或已损坏**」（试了 2 版）。现代的 PBIT 包格式比 2018 年样本严格得多，盲造不划算。

### 唯一可靠路径

**用 Desktop 自己导出**：打开项目 → 「文件 → 导出 → Power BI 模板」→ 保存。
- 不要试图用 ctypes 鼠标/键盘自动化点这个菜单：实测桌面会话前台状态不稳（窗口频繁被最小化、`GetForegroundWindow()` 返回 0），点击会落空甚至点到别的窗口上。
- 正确姿势：把这一步交给用户（3 次点击），然后**用 MCP `pbix_inspect` + 打开验证**他导出的 pbit。

## 给用户的交付话术模板

> 双击 `<项目名>.pbip` → 打开时会弹参数框（默认值已填好）→ 点确定 → 主页点「刷新」→ 左侧字段面板立刻出现两张表和全部字段。想单文件就「另存为 .pbix」。
