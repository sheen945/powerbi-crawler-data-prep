# M 语言核心规范（本地 Desktop + 平面文件版）

> 源自 data-goblin/power-bi-agentic-development 的 power-query 技能（GPL-3.0），已删除查询折叠、Fabric 云端相关内容。

## 1. 基本结构

M 表达式是 `let ... in` 步骤链：

```
let
    Source = Csv.Document(File.Contents("C:\data\games.csv")),
    提升标题 = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    转类型 = Table.TransformColumnTypes(提升标题, {{"比赛日期", type date}, {"CC指数", type number}})
in
    转类型
```

规则：

- 每步是一个命名变量，后面用逗号连接，最后一步 `in` 后面跟输出步骤名
- 步骤名带空格/中文/特殊字符 → 用 `#"步骤名"` 声明和引用；纯英文无空格可直接写
- 注释：单行 `// 注释`，多行 `/* 注释 */`

## 2. 命名规范

| 对象 | 规范 | 好例子 | 坏例子 |
|---|---|---|---|
| 步骤名 | 动词开头说人话，说明这步干了什么 | `筛选有效比赛`、`转类型` | `Step3`、`Table1` |
| 查询名 | 业务表名，复数或名词 | `球员CC指数`、`伤病明细` | `Query1`、`Sheet1` |
| 参数名 | 用途 + 含义清晰 | `数据文件夹路径` | `Param1` |

## 3. 类型系统

入口之后立刻转类型，越早越好。

常用类型：

| M 类型 | 对应含义 | 备注 |
|---|---|---|
| `type text` | 文本 | 爬虫字段默认全是这个 |
| `type number` | 小数 | CC指数等评分字段 |
| `Int64.Type` | 整数 | 得分、篮板等计数 |
| `type date` | 日期 | 比赛日期 |
| `type datetime` | 日期时间 | 带时间的抓取时间戳 |
| `type logical` | 真/假 | 是否首发、是否缺阵 |

**文本转数值安全写法**（爬虫字段常混着 "N/A"、"-" 这类脏值）：

```
Table.TransformColumns(上一步, {{"CC指数", each try Number.FromText(_) otherwise null, type number}})
```

- `Number.FromText` 遇到 "23.5" 转 23.5，遇到 "N/A" 会报错 → 包 `try...otherwise null` 变空值
- 别用隐式转换，脏数据直接让整列报错

## 4. 编写顺序模板（平面文件安全顺序）

```
let
    Source = <入口>,                                    // 1. 读文件
    提升标题 = Table.PromoteHeaders(Source, ...),        // 2. 第一行变列名（CSV/Excel 需要）
    保留列 = Table.SelectColumns(提升标题, {...}),        // 3. 列裁剪尽早
    改列名 = Table.RenameColumns(保留列, {...}),          // 4. 一步批量改名
    筛行 = Table.SelectRows(改列名, each ...),           // 5. 行过滤尽早
    转类型 = Table.TransformColumnTypes(筛行, {...}),     // 6. 类型转换
    清洗 = ...                                           // 7. 业务清洗（归一、去重等）
in
    清洗
```

原则：列裁剪和行过滤尽早，减少后续步骤处理的数据量。

## 5. 高频函数速查

| 场景 | 函数 |
|---|---|
| 筛行 | `Table.SelectRows(表, each [列] = "值")` |
| 保留/删列 | `Table.SelectColumns` / `Table.RemoveColumns` |
| 批量改名 | `Table.RenameColumns(表, {{"旧","新"},...})` |
| 转类型 | `Table.TransformColumnTypes(表, {{"列", type text},...})` |
| 逐列自定义转换 | `Table.TransformColumns(表, {{"列", each ..., type number}})` |
| 加自定义列 | `Table.AddColumn(表, "新列名", each 表达式)` |
| 条件列 | `Table.AddColumn(表, "标记", each if [A] = null then "缺失" else "正常")` |
| 合并查询（横向 Join） | `Table.NestedJoin` + `Table.ExpandTableColumn` |
| 纵向拼接 | `Table.Combine({表1, 表2, 表3})` |
| 去重 | `Table.Distinct(表, {"比赛日期", "球员"})` |
| 限行预览 | `Table.FirstN(表, 100)` |
| 文本清洗 | `Text.Trim`、`Text.Clean`、`Text.Replace` |

## 6. 反模式（别这么干）

1. **整表拉进来再过滤**——先裁剪后处理
2. **一列一个改名步骤**——一步 `Table.RenameColumns` 批量
3. **滥用 `Table.Buffer`**——平面文件场景基本不需要，反而妨碍优化
4. **跨查询层层引用**——A 引用 B 引用 C 引用 D，刷新慢难维护，能合并就合并
5. **静默吞错**——`try 整段查询 otherwise 空表` 会把所有错误藏起来；`try...otherwise` 只用在单个字段转换上
6. **硬编码路径散落在各处**——文件路径统一做成参数，一处修改全局生效
7. **类型全靠猜**——不转类型直接可视化，求和报错、日期排序错乱

## 7. 分步调试法

报错或结果不对时：

1. 把 `in` 后面的步骤名改成中间某一步，逐段预览
2. 每步检查：列名和列数对不对、行数对不对、类型对不对、抽几行值看看正不正常
3. 数据量大时配合 `Table.FirstN(表, 100)` 限行，调试更快

```
let
    Source = ...,
    提升标题 = ...,
    转类型 = ...
in
    提升标题    // 临时改成中间步骤，看这步的输出
```

## 8. 交付前检查清单

1. **语法**：高级编辑器无红色报错
2. **数据**：列名、列数符合预期
3. **类型**：逐列确认（数值字段不是文本）
4. **空值**：关键字段空值数量符合预期
5. **行数**：过滤/去重后行数合理
