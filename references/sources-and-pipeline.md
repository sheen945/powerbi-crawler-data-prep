# 三类入口模板 + 每日增量管道

> 爬虫数据入口与管道化完整代码。所有路径统一走参数，不写死。

## 0. 参数定义（先做这两个参数）

在 Power BI「管理参数 → 新建参数」里建，或直接在高级编辑器建查询：

**参数 1：数据文件夹路径**（查询名 `数据文件夹路径`）

```
"C:\爬虫数据\篮球比赛" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

**参数 2：球队别名表路径**（查询名 `别名表路径`，可选）

```
"C:\爬虫数据\配置\球队别名表.xlsx" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

## 1. JSON 入口模板

爬虫 JSON 常见两种形态：整个文件是一个记录数组，或每行一条 JSON（JSONL）。

### 1.1 标准 JSON（数组）单文件

```
let
    Source = Json.Document(File.Contents("C:\爬虫数据\篮球比赛\games_20260930.json")),
    转表 = Table.FromRecords(Source),
    转类型 = Table.TransformColumnTypes(转表, {{"比赛日期", type date}, {"CC指数", type number}})
in
    转表
```

### 1.2 JSON 嵌套展开

爬虫 JSON 常把数据藏在 `data.list` 这类嵌套里：

```
let
    Source = Json.Document(File.Contents(文件路径)),
    取列表 = Source[data][list],                          // 按实际嵌套层级取
    转表 = Table.FromRecords(取列表),
    展开嵌套列 = Table.ExpandRecordColumn(转表, "球员信息", {"姓名", "位置"}, {"球员姓名", "位置"})
in
    展开嵌套列
```

### 1.3 JSONL（每行一条）

```
let
    Source = Lines.FromBinary(File.Contents(文件路径)),
    逐行解析 = List.Transform(Source, each Json.Document(_)),
    转表 = Table.FromRecords(逐行解析)
in
    转表
```

## 2. CSV 入口模板

```
let
    Source = Csv.Document(
        File.Contents("C:\爬虫数据\篮球比赛\games_20260930.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    提升标题 = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    转类型 = Table.TransformColumnTypes(提升标题, {{"比赛日期", type date}, {"CC指数", type number}})
in
    转类型
```

注意：

- `Encoding = 65001` 是 UTF-8。爬虫 CSV 如果是 GBK（中文 Windows 默认），改成 `Encoding = 936`，否则中文乱码
- 字段里带逗号时必须 `QuoteStyle.QuoteStyle.Csv`

## 3. Excel 入口模板

```
let
    Source = Excel.Workbook(File.Contents("C:\爬虫数据\篮球比赛\games_20260930.xlsx"), null, true),
    取Sheet = Source{[Item="Sheet1", Kind="Sheet"]}[Data],
    转类型 = Table.TransformColumnTypes(取Sheet, {{"比赛日期", type date}, {"CC指数", type number}})
in
    转类型
```

注意：第三个参数 `true` = 自动识别首行为标题。Sheet 名写错会报 `The key didn't match any rows`，先单独预览 `Source` 这步确认 Sheet 名。

## 4. 每日增量管道（核心）

爬虫每天把新文件丢进同一个文件夹，Power BI 自动合并全部文件。

### 4.1 单一格式的文件夹管道

```
let
    Source = Folder.Files(数据文件夹路径),
    只留CSV = Table.SelectRows(Source, each [Extension] = ".csv"),
    加内容列 = Table.AddColumn(只留CSV, "数据", each 清洗单CSV([Content], [Name])),
    展开 = Table.ExpandTableColumn(加内容列, "数据", {"比赛日期","主队","客队","球员","CC指数","伤病情况","是否首发"}),
    按主键去重 = Table.Distinct(展开, {"比赛日期", "球员"})
in
    按主键去重
```

其中 `清洗单CSV` 做成自定义函数（输入二进制内容和文件名，输出清洗好的表），保证每个文件走同一套清洗逻辑：

```
(Content as binary, 文件名 as text) =>
let
    Source = Csv.Document(Content, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    提升标题 = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    加来源列 = Table.AddColumn(提升标题, "来源文件", each 文件名),   // 溯源用，排查脏数据出自哪个文件
    转类型 = Table.TransformColumnTypes(加来源列, {{"比赛日期", type date}, {"CC指数", type number}})
in
    转类型
```

### 4.2 多格式混杂文件夹管道

JSON/CSV/Excel 都丢同一文件夹时，按扩展名分流：

```
let
    Source = Folder.Files(数据文件夹路径),
    分流 = Table.AddColumn(Source, "格式", each Text.TrimStart([Extension], ".")),
    加内容列 = Table.AddColumn(分流, "数据", each
        if [Extension] = ".json" then 清洗单JSON([Content], [Name])
        else if [Extension] = ".csv" then 清洗单CSV([Content], [Name])
        else if [Extension] = ".xlsx" then 清洗单Excel([Content], [Name])
        else null),
    去空 = Table.SelectRows(加内容列, each [数据] <> null),
    // 关键：三路出口列结构必须一致（列名、顺序、类型），缺失列在各自函数里补 null
    展开 = Table.ExpandTableColumn(去空, "数据", {"比赛日期","主队","客队","球员","CC指数","伤病情况","是否首发","来源文件"}),
    按主键去重 = Table.Distinct(展开, {"比赛日期", "球员"})
in
    按主键去重
```

### 4.3 管道要点

1. **三个清洗函数出口必须列结构一致**：列名、列顺序、列类型都对齐，缺的列在函数内补 `null`
2. **来源文件列必加**：数据出问题时能定位是哪个文件带来的脏数据
3. **去重键显式定义**：`{"比赛日期", "球员"}`，爬虫重抓也不会翻倍
4. **用户日常动作**：跑爬虫 → 新文件丢进文件夹 → Power BI 点刷新，完事
5. **可选优化**：只保留最近 N 天文件——在 `Folder.Files` 后加 `Table.SelectRows(Source, each [Date modified] >= Date.AddDays(DateTime.Date(DateTime.LocalNow()), -30))`
