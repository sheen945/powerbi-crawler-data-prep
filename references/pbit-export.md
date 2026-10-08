# PBIT 导出（标准交付物）

> **2026-10-07 用户定规：交付格式固定为 `.pbit`。** 用户说的「清洗完的那个文件」就是 `.pbit` 模板，不是 PBIP 工程。
> 本文全部结论来自 Windows + Power BI Desktop 26.09（`2.158.1177.0 (26.09)+a10b99dd…`）实测。

## 0. 一句话结论

**能用的 PBIT 只有一个来源：Desktop 自己的「文件 → 导出 → Power BI 模板」。**
先把 PBIP 做对、真机验完数，再导出。**自造 PBIT 试过两次都撞墙，别再试（§2）。**

## 1. 真实 PBIT 的内部结构（解剖自 Desktop 亲自导出的包）

不要相信网上 2018 年的 PBIT 结构（那版有 `DataMashup`）。26.09 导出的是这样（实测 38 个部件）：

| 部件 | 编码 | 说明 |
| --- | --- | --- |
| `Version` | UTF-16LE | 8 字节版本号，26.09 写的是 `1.32` |
| `[Content_Types].xml` | UTF-8（带 BOM） | 很宽松：多个 `<Override>` 的 `ContentType` 是**空串**，Desktop 自己也这么写 |
| `UnappliedChanges` | UTF-16LE JSON | ⭐ **全部查询的 M 文本**都在这里（老版的 `DataMashup` 被它取代） |
| `DataModelSchema` | UTF-16LE JSON | ⭐ TMSL 模型：`{name(guid), compatibilityLevel: 1606, model:{…}}`，M 内联在 `partitions[].source.expression` |
| `DiagramLayout` | UTF-16LE JSON | 模型关系视图的节点位置（**不是 `DiagramState`**，很多老资料写错） |
| `Settings` | UTF-16LE JSON | `{"Version":4,"ReportSettings":{},"QueriesSettings":{…}}` |
| `Metadata` | UTF-16LE JSON | `{"Version":5,"AutoCreatedRelationships":[],"CreatedFrom":"Cloud","CreatedFromRelease":"2026.09"}` |
| `SecurityBindings` | 二进制 | 约 1.2 KB，凭据绑定 |
| `Report/definition/**` | UTF-8 无 BOM | ⭐ 就是 PBIP 里 `<名>.Report/definition/` 的**原样拷贝**（PBIR 增强格式）；**没有 `Report/Layout`** |

**注意：不存在 `DataMashup` 部件。**

### 1.1 `UnappliedChanges` 逐字段（实测）

```json
{
  "version": "1.0",
  "conceptualSchemaSettings": {},
  "queries": [
    {
      "name": "比赛数据",
      "lineageTag": "<guid>",
      "text": ["let", "    源 = 比赛宽表,", "…"],
      "isDirectQuery": false,
      "lastLoadedAsTableFormulaText": "{\"IncludesReferencedQueries\":false,\"RootFormulaText\":\"let\\n    源 = …\",\"ReferencedQueriesFormulaText\":{}}",
      "loadAsTableDisabled": false,
      "resultType": "Table",
      "isHidden": false
    },
    {
      "name": "数据文件夹路径",
      "lineageTag": "<guid>",
      "text": ["null meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]"],
      "loadAsTableDisabled": true,
      "resultType": "Text",
      "isHidden": false
    }
  ],
  "queryGroups": [],
  "culture": "zh-CN",
  "firewallEnabled": true
}
```

- 已加载的表：`isDirectQuery: false` + `loadAsTableDisabled: false` + 带 `lastLoadedAsTableFormulaText`
- 不加载的查询：只有 `loadAsTableDisabled: true`，**没有** `isDirectQuery` / `lastLoadedAsTableFormulaText`
- `resultType`：参数 = `Text`，自定义函数 = `Function`，中间查询 = `Table`
- `lastLoadedAsTableFormulaText` 是**字符串化的 JSON**，内层 `ReferencedQueriesFormulaText` 是 `{}`（空对象，不是 null）
- **参数在这一层被写成 `null meta […]`** —— 模板不固化参数值，所以用户打开时会弹框

### 1.2 `lineageTag` 三处必须对上（手搓时最容易漏的）

`DataModelSchema`（`table` / `column` / `measure` / `expression`） ↔ `UnappliedChanges.queries[].lineageTag` ↔ `DiagramLayout.diagrams[].nodes[].nodeLineageTag`

`pbi-tools convert … Raw` 产出的 `database.json` **完全没有这些 tag**（它的 TMDL 是极简的），要自己补。

## 2. ⛔ 手搓 PBIT：两条路都撞墙（别再试）

| 尝试 | 结果 |
| --- | --- |
| `pbi-tools compile <folder> out.pbit PBIT` | 打包步骤调 Desktop 的 `Microsoft.PowerBI.Packaging.PowerBIPackager.Save(…)`，26.09 签名已变 → `MissingMethodException`；pbi-tools 停在 2025-01，无解。另外 `compile` 期望的是 **PbixProj 目录**（要 `Version.txt` 等），不是 TMDL 的 `definition` 目录，直接喂会报 `The PBIX part at '…\Version.txt' could not be deserialized` |
| 手拼 OPC（v1：`DataMashup` + `DiagramState` + Version `1.25`） | Desktop **静默打开成空白新报表**，`currentFilePath` 为空 |
| 手拼 OPC（v2：按 §1 真结构全量重做，含 `UnappliedChanges` + `DiagramLayout` + `lineageTag` + 复用真包的小部件） | Desktop 弹「**无法打开模板 · 此文件已损坏，或是使用无法识别的 Power BI Desktop 版本**」 |

**结论**：容器层面能拼对（`pbi-tools extract` / Python `zipfile` 都能读），但 Desktop 26.09 的模板校验还有一层外部看不到的东西。投入产出比极差。

> **硬规则：不要自造 PBIT。** 见到"要 pbit"直接跳到 §3。

## 3. 官方导出路径（唯一可靠）

### 3.1 人工版：3 次点击

打开 PBIP → **文件 → 导出 → Power BI 模板** → 模板说明可留空 → 导出 → 选路径保存。

### 3.2 自动化版：实测能力边界（**已跑通全程**）

| 步骤 | 能否自动 | 手段 |
| --- | --- | --- |
| 打开 PBIP / 刷新 / DAX 验数 | ✅ | 见 `powerbi-mcp.md` |
| 点「文件」tab 进后台面板 | ✅ | `SendInput` 点击（**必须坐标标定**，见 §4） |
| 进「导出」面板 → 点「Power BI 模板」 | ✅ | 同上 |
| 「导出模板」对话框 → 确定 | ✅ | `TAB` + `ENTER` |
| 弹出「另存为」 | ✅ | |
| 填文件名 | ✅ | **点文件名框 + `Ctrl+V`**（`WM_SETTEXT` 也能成，但实测会阻塞 5m34s 才返回，别用） |
| 点「保存」按钮 | ✅ | `EnumChildWindows` 找到文本含 `保存` 的 `Button`，点其矩形中心 |

**实测成功的完整配方（照抄即可，2026-10-07 跑通，产出 39,897 字节模板）**：

```
① 启动 Desktop 打开 PBIP，等 100s 加载完，把窗口 SetWindowPos 固定成 1600x950（(0,0)）
② SendInput 点 (62,70)   → 打开「文件」后台面板
③ SendInput 点 (105,421) → 进「导出」面板
④ SendInput 点 (350,162) → 点「Power BI 模板」
⑤ 等 4s，找标题为「导出模板」的独立窗口 → SetForegroundWindow → TAB → ENTER
⑥ 等 5s，出现「另存为」窗口（1000x760，Desktop 会记住上次尺寸）
⑦ EnumChildWindows(另存为) 找 cls='Edit' 且宽>300 的控件 → 点其中心 → Ctrl+A → Ctrl+V 路径
⑧ 找 cls='Button' 且 title 含「保存」的控件（实测 rect (794,722)-(882,748)）→ 点矩形中心
⑨ 8s 后检查文件是否生成
```

> ⛔ 先删掉同名的旧 pbit，否则会弹「是否替换」多一步。
> ⛔ 打开模型后**不要再改窗口尺寸**，否则 §4.2 的坐标全部失效。

### 3.3 卡住过的地方（下次别在这儿耗）

- 给文件名 `Edit` 发 `SendMessage(WM_SETTEXT)` / `WM_COMMAND IDOK`：前者成功但**阻塞数分钟**，后者**完全无效**——必须点按钮。
- 「另存为」在默认尺寸下**把自己的按钮裁到客户区之外**；先 `SetWindowPos` 拉高（1000×760）再 `EnumChildWindows` 才看得到 `保存(&S)`。
- 模板加载后弹出的**参数输入框是 IE 嵌入控件**（子窗口是 `Shell Embedding` / `Internet Explorer_Server`），**收不到 `Ctrl+V`/`WM_SETTEXT`**；`KEYEVENTF_UNICODE` 逐字符注入也只能部分成功（会出现校验警告图标）。→ **别指望自动化把参数填完，这一步留给用户。**

## 4. Desktop UI 自动化：四条必须知道的规律

### 4.1 合成输入必须用 `SendInput`，不能用 `mouse_event`

`mouse_event`（旧 API）**进不了 Desktop 的 File 后台面板**——点了毫无反应。换 `SendInput`（绝对坐标 `x*65535/(屏幕宽-1)` + `MOUSEEVENTF_ABSOLUTE`）就能点。

现成脚本：`_tools/desktop_auto.py`（子命令 `list` / `shot` / `shot_hwnd` / `focus` / `click` / `**sclick**`(SendInput) / `move` / `key` / `**skey**` / `text`），内部已含 `INPUT`/`MOUSEINPUT`/`KEYBDINPUT` 结构体。

### 4.2 坐标标定：渲染位置 ≠ 命中位置（差 0.856 倍）

窗口被改成 1600×950 时，File 后台面板**看得见的位置和点得中的位置不是一个地方**：

```
点击y ≈ 0.856 × 渲染y − 27.7        # 0.856 = 950/1111 = 窗口高 / WebView 内部布局高
点击x ≈ 渲染x                        # x 方向实测不需要换算
```

- **别猜，现场标定**：先做三次探测（已知位置点一次，看反应对不对得上），把系数反解出来。
- ⛔ **打开模型之后不要再改窗口尺寸**：WebView 子窗口会保留旧几何（实测仍是 2048×1111），此后所有点击全乱。
- 标定结果（1600×950 窗口，可直接复用）：`文件` tab = **(62, 70)**；导出面板里 `导出` = **(105, 421)**；`Power BI 模板` = **(350, 162)**。

### 4.3 找控件别靠肉眼读截图

Read 工具渲染截图的缩放比是未知的，**肉眼估坐标必错**（这一条浪费了大量时间）。用两种程序化办法：

```python
# ① 暗像素扫描：找某区域里的文字行（返回每行的 y 带）
bands=[]; cur=None
for y in range(y0, y1):
    cnt = sum(1 for x in range(x0, x1) if px[x, y] < 140)
    if cnt > 3:
        cur = [y, y] if cur is None else [cur[0], y]
    else:
        if cur and cur[1]-cur[0] >= 6: bands.append(tuple(cur))
        cur = None
```

```python
# ② 控件级（最准）：EnumChildWindows 拿 Edit / Button 的 rect + 文本
#    例：找到 Button 文本 '保存(&S)' → rect (791,719)-(879,745) → 点矩形中心
```

### 4.4 两个配套的坑

- **「另存为」对话框在默认尺寸下把自己的按钮裁掉了**（按钮落在客户区之外）。先 `SetWindowPos` 拉高到约 1000×760，再 `EnumChildWindows` 才能看到 `保存(&S)`。
- **`python -c "…"` 里不要写含反斜杠的路径**（bash 会吃掉 `\\`）。所有 Windows 自动化/桥接脚本都写成 `.py` 文件再跑。

## 5. 导出后的验收

1. **大小参考**：竞彩篮球（5 表 / 28 度量值 / 3 页 24 视觉）≈ **39 KB**。PBIT 不含数据，别把"太小"当异常。
2. **部件自检**（Python `zipfile` 或 `pbi-tools extract`，最硬的离线证据）：
   ```
   部件数 38；顶层 9 类齐全：Version / [Content_Types].xml / UnappliedChanges /
   DataModelSchema / DiagramLayout / Settings / Metadata / SecurityBindings / Report/**
   Report 部件 30 个 = 3 页 page.json + 24 个 visual.json + pages.json + report.json + version.json
   UnappliedChanges.queries 覆盖全部查询（本例 15 个），已加载表 loads=True、其余 True→False
   DataModelSchema：表/关系/度量值数量与 PBIP 一致，compatibilityLevel 1606
   ```
3. **真机打开验收**（关键，判据和 PBIP 不同！）：
   - 正确现象：窗口标题变「**无标题 - Power BI Desktop**」，**并且弹出一个以模板名命名的对话框**（本例标题 `竞彩篮球-数据清洗模板`），里面列出模板里的参数（本例 `数据文件路径`）+ 一个「加载」按钮。
   - **只有 Desktop 成功解析了 `DataModelSchema` + `UnappliedChanges` + 报表部件，才可能读得出模板名和参数名**——这就是模板有效的铁证。
   - 报「**无法打开模板 · 此文件已损坏，或是使用无法识别的 Power BI Desktop 版本**」= 模板被拒（自造包就是这个下场）。
   - ⛔ **别拿 `currentFilePath` 当判据**：模板是「新建未保存文档」，Bridge `application.state.get/v1` 返回空字符串**属正常**（这点和打开 PBIP 时相反，早期把它当成"没打开"是误判）。
   - ⛔ 参数没填之前，AS 引擎里 `db.Model.Tables` 就是**空的**（模型要等参数确定才生成），这也属正常，不是模板坏了。
4. 用户可以自己把参数填完 → 点「加载」→ 模型与三页看板随即出现（这一步的参数框是 IE 控件，自动化填不进去，交给用户 1~2 次操作即可）。

## 6. ⭐ 跨版本兼容：对方打不开怎么办（2026-10-07 实战）

**这是交付 pbit 之后最常见的售后问题，务必提前预防。**

### 6.1 症状与根因

对方（朋友/同事）双击 pbit，报：

> **无法打开文档 · 此文件与当前版本的 Microsoft Power BI Desktop 不兼容。请安装最新版本，然后尝试重新打开该文档。**

**根因不是文件损坏，是文件太新。** Power BI 的硬规矩：**高版本 Desktop 产出的文件，低版本一定打不开。**

### 6.2 文件里刻着三个「版本太高」的标记（这样查）

解压 pbit（它就是 zip），看这几处：

| 部件 / 字段 | 26.09 实测值 | 说明 |
| --- | --- | --- |
| `Version` | `1.32`（UTF-16LE，8 字节） | 打包器版本号 |
| `DataModelSchema` → `compatibilityLevel` | **`1606`** | ⭐ 最关键。模型引擎的"语言版本" |
| `Metadata` → `CreatedFromRelease` | `2026.09` | 创建时的 Desktop 发行版 |
| `Settings` → `QueriesSettings.Version` | `2.158.928.0` | Desktop 构建号 |
| `Report/definition/version.json` → `version` | `2.0.0` | ⭐ 报表用的是**新版 PBIR 增强格式**（老版本读的是单个 `Report/Layout`） |

**关键洞察**：PBIP 工程里 `database.tmdl` 写的是 `compatibilityLevel: 1567`（低得多），
**是 Desktop 在导出模板时自动把它拉到 1606 的**。用户层面没有开关可以阻止这一步。

### 6.3 ⛔ 不要试图产出「向下兼容」的 pbit（做不到）

三个原因，别再试：

1. **兼容级别只能升不能降**——微软官方原文 `upgrading the compatibility level is irreversible`。
2. **报表格式换代了**——旧版是单个 `Report/Layout`（UTF-16LE），新版是 `Report/definition/**` 一整套目录（PBIR `2.0.0`）。把新版"翻译"回旧版 = 把整个报表重画一遍，那叫重做不叫导出。
3. **本机只有新版 Desktop，改完无法验证**——属于盲改；且手拼 pbit 已撞墙两次（§2）。

### 6.4 ✅ 正确处置：三条路，按推荐顺序

| 优先级 | 方案 | 做法 |
| --- | --- | --- |
| 🥇 | **让对方用他自己的电脑重建** | 交付时**附一份自包含提示词**（含清洗规则 + 星型模型 + 全部度量值 + 看板规格 + 验收标准），并把**完整 PBIP 工程**一起打包——PBIP 全是纯文本，对方的 AI/人能直接读，等于拿到精确规格书。用他本机 Desktop 生成 → 版本必然匹配 |
| 🥈 | **让对方升级 Desktop** | 官网 `https://www.microsoft.com/download/details.aspx?id=58494`（免费），或 Microsoft Store。微软官方口径就是「请安装最新版本」 |
| 🥉 | 应急偏方（不保证） | 报错弹窗点**右上角的 `X`**（**不是**「关闭」按钮），有时能进。仅在"模型能被解析、只是某个标记超纲"时管用，别当正经方案 |

### 6.5 交付时的预防动作（写进交付物）

1. **交付说明里写明「需要的最低版本」**（本例：Desktop 2026.09 / 构建号 2.158.928.0），别让对方猜。
2. **优先发压缩包**（`zip`/`7z`）而不是单个 pbit——避免 IM 传输环节截断，也能一次带齐「数据 + 工程 + 说明 + 提示词」。
3. **包里一定要放 PBIP 工程**——pbit 打不开时对方还有退路，不至于卡死。
4. **包里放一份「打不开怎么办」的诊断说明**，把 6.4 三条路写清楚。

### 6.6 「打不开」的四种现象对照（先用这张表分类）

| 对方看到的现象 | 根因 | 处理 |
| --- | --- | --- |
| 「此文件与当前版本的 Power BI Desktop 不兼容」 | **版本太新**（最常见） | §6.4 方案一 / 二 |
| 「无法打开模板 · 此文件已损坏」 | 传输损坏，或手工拼包 | 重新打包发送；确认没自造过 |
| 能打开但报「找不到数据文件」 | 模板里记的是交付方的本地路径 | 把参数指向对方自己那份原始数据 |
| 打开后空白 / 字段面板空 | 参数没填、没点「加载」 | 填参数 → 加载 → 刷新 |

## 7. 交付话术

> 双击 `竞彩篮球-数据清洗模板.pbit` → Power BI Desktop 会用模板新建一个报表 → 弹出参数框时把「数据文件路径」指到原始数据文件 → 确定 → 主页点「刷新」（约 2 万行，1~2 分钟）→ 三页看板就有数据了。
> ⚠️ **本模板需要 Power BI Desktop 2026.09 或更新版本**（低版本会报「不兼容」，那不是文件坏了——见 §6）。
> 想存成单文件再编辑：文件 → 另存为 → `.pbix`。
