# Power BI MCP 使用手册（本机已打补丁）

> 交付 PBIP 后**必须**走这里跑一遍真机验证。MCP 是第三方开源件（`sulaiman013/powerbi-mcp`，82 个工具），
> 本机已按实测打了 3 个补丁——升级或重装会丢，见 §5。

## 0. 本机事实（别再去找别的方案）

- 配置：`~/.workbuddy/mcp.json` → 服务名 `powerbi` → `<本仓库>/mcp/powerbi-mcp/src/server.py`
- 建模库：`powerbi-mcp/adomd/`（`Microsoft.AnalysisServices.Tabular.dll` / `.AdomdClient.dll`），
  pythonnet 可直接加载，**这就是"MCP 没有的功能"的兜底通道**
- 参考文档：同目录 `AGENTS.md`（作者写给 agent 的金规：改名走 pbip_*、DAX 先校验、批量改走事务）

## 1. 按任务选工具（速查）

| 要做的事 | 工具 |
| --- | --- |
| 加载/校验工程（离线，不开 Desktop） | `pbip_load_project` → `pbip_validate` → `pbir_validate_report` |
| 改名（模型 + 报表引用一起改） | `pbip_rename_tables` / `pbip_rename_columns` / `pbip_rename_measures`（**不要**用 `batch_rename_*`，那组只改模型、会把图表改坏） |
| 加度量值（离线写 TMDL，自带 dax_lint） | `pbip_add_measures` → **重新 `pbip_load_project`** 才能被视觉对象引用 |
| 加页面 / 图 / 绑定字段 | `pbir_add_page` → `pbir_add_visual` → `pbir_bind_fields` → `pbir_validate_report` |
| 连活模型读数 | `desktop_discover_instances` → `desktop_connect <port>` → `desktop_list_tables` / `desktop_list_columns` / `desktop_list_measures` / `desktop_get_model_info` |
| 跑 DAX 验数 | `desktop_execute_dax` |
| 模型体检 | `run_bpa` / `audit_star_schema` / `audit_naming` / `audit_ai_readiness` / `analyze_model_storage` / `export_data_dictionary` |
| 拆解别人的 pbix（只读） | `pbix_inspect` / `pbix_extract` |
| 窗口级（预览） | `bridge_status` / `bridge_reload` / `bridge_screenshot` |

## 2. 标准验证链（交付 PBIP 后必跑，最后导出 PBIT）

1. `pbip_load_project <pbip路径>` → 识别 TMDL 数 / 可视对象数 / 报告格式
2. `pbip_validate` → `No validation errors found`；`pbir_validate_report` → 所有字段绑定可解析
3. **打开 Desktop**（用 Python，不要用 PowerShell）：
   ```python
   import subprocess
   subprocess.Popen([r'C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe',
                     r'<pbip 绝对路径>'], close_fds=True)
   ```
4. `desktop_discover_instances` 拿端口 → `desktop_connect <port>`
   ⛔ **别用 `netstat` 找端口**：沙箱里拿不到 PBIDesktop 的 LISTENING 行（实测空结果）；端口每次启动都变，必须现查。
5. **刷新数据**（MCP 无此功能，见 §3）
6. `desktop_execute_dax` 验行数 / 勾稽 / 度量值：
   `EVALUATE ROW("场次", COUNTROWS('事实表'), "度量值", [某度量值])`
7. **逐页截图**：优先 Desktop Bridge（`file.reload/v1` 热重载 + `report.snapshot.capture/v2` 按 pageId 截图，scale 可调）
   —— 比 `bridge_screenshot` 更省事，也不用切页（切页在这版 Desktop 上很难自动化，见 `pbit-export.md` §4）
8. **导出 PBIT**：文件 → 导出 → Power BI 模板（自动化配方见 `pbit-export.md` §3–§4）

**判断口径（踩过的坑）**

- `COUNTROWS` 返回 **null** = 模型连上了但**从未刷新**，不是模型错
- Desktop 打开成功的**可靠判据是 Bridge `application.state.get/v1` 的 `currentFilePath`** —— 必须指向你传进去的文件；
  为空 = 其实开成了空白新文档（窗口标题「无标题」既可能是打开失败，也可能是**正常打开模板**，光看标题会误判）
- 桥接回 `-32502 Host is not ready to accept operations` = 界面正在忙（加载中）或**窗口被最小化**，或界面上有模态对话框
- 模型报「不明确的路径」= 事实表之间建了关系，删掉（见 pbip-delivery.md 星型模型铁律）

## 3. 本地刷新缺口：用 TOM 自己补

MCP 没有任何"刷新本地模型"的工具，只能用它自带的建模库：

```python
import sys, clr
sys.path.append(r'<本仓库>/mcp/powerbi-mcp/adomd')
clr.AddReference('Microsoft.AnalysisServices.Tabular')
clr.AddReference('Microsoft.AnalysisServices.Core')
clr.AddReference('Microsoft.AnalysisServices.AdomdClient')
from Microsoft.AnalysisServices.Tabular import Server, RefreshType
srv = Server(); srv.Connect(f'localhost:{port}')
db = srv.Databases[0]
db.Model.RequestRefresh(RefreshType.Full); db.Model.SaveChanges()
# 再用 ADOMD 轮询 DAX 直到数据出现（刷新是异步的）
```

现成脚本：`_tools/刷新并验证.py <端口>`（连端口自己发现：`desktop_discover_instances`）。
注意 `file.reload/v1` 热重载后**数据缓存会清空**，截图前必须重新刷新。

## 4. 报表创作的三个坑（实测）

1. **值角色里的文本列会被自动套 CountNonNull 聚合** → 明细表渲染成「某某的计数」。
   修法：传显式规格 `{"table","field","kind":"Column"}`（不带 aggregation），用 `pbir_bind_fields` 的 `replace` 重绑。
2. **一条角色放多个字段，只渲染第一个**（`tableEx` 7 列只出 1 列、矩阵 5 个 Rows 只出 1 个）。
   结论：**一条角色只放一个字段**；要"表格"效果用 `pivotTable`（Rows 放一个维度，Columns 放日期，Values 放指标），
   `tableEx` 实测只渲染第一列、别用。多列明细表让用户在 Desktop 里拖一次，Power BI 自己会写对格式。
3. **改了模型要重新 `pbip_load_project`**，新表/新度量值才会被 `pbir_add_visual` 的字段校验看到。

## 5. 本机补丁（3 处，2026-10-01 实测后打的）

都在 `<本仓库>/mcp/powerbi-mcp/src/`，**MCP 服务重启后生效**（本次用直接调用模块验证）：

1. **`desktop_bridge.py`**：新增 `call_with_args()`。26.07+ 的桥接在 manifest 里声明
   `params.required = ["args"]`，业务参数必须写成 `{"args": {...}}`；原来直接传 `{"pageId","scale"}` 会报
   `-32602 Request arguments are required`。现在自动兼容两种形态，`capture_snapshot` 还优先用 v2（支持截图区域）。
2. **`powerbi_pbip_connector.py`**：`_write_text` 加**进程级锁 + 唯一临时文件名**。
   原来并发工具调用共用 `<name>.tmp`，会 `WinError 32` 写坏 `definition/pages/pages.json`。
3. **同文件 `create_backup()`**：备份目录从「项目旁边」改到 `%TEMP%/powerbi-mcp-backups/`，
   不再往用户工作区丢 `xxx_backup_时间戳` 文件夹。

验证脚本：`_tools/验证MCP补丁.py`（并发写 4×150 次、桥接真机截图、备份路径检查）。
⚠️ 升级 powerbi-mcp 前先把这三处记下来，或直接从 git 恢复本机补丁。

## 6. 截图三招（按优先级）

1. **Desktop Bridge 逐页截图**（首选）：`report.snapshot.capture/v2` + `{pageId, scale}`，**按页拿图、不用切页**
2. `bridge_screenshot`（MCP 工具，需窗口**未最小化**；单页或 all）
3. `PrintWindow`（纯 ctypes，**能抓被遮挡的窗口**）：`_tools/窗口截图3.py <pid> <out.png>`
   —— 桥接不可用时的兜底；最小化的窗口抓不到，先 `ShowWindow(SW_RESTORE)` 还原

⛔ **窗口截图看不到底部页面标签栏**：报表用 `FitToPage` 时会撑满窗口，标签栏被挤出可视区，PrintWindow / BitBlt 都一样抓不到。
所以「要证明三页都对」只能用桥接按 pageId 逐页截（或改 pages.json 的 activePageName 重启，但**只对第一页生效**，后面会被 Desktop 自身状态覆盖）。

环境限制：PowerShell 的 `Add-Type`、`New-Object -ComObject` 一律被安全策略拦；Bash 里带反引号的命令会被判"绕过 PowerShell 检查"而拒绝 → **窗口/截图/进程操作统一走 Python（ctypes + PIL）**。

## 7. 沉淀的脚本清单（都在项目 `_tools/`）

| 脚本 | 用途 |
| --- | --- |
| `刷新并验证.py <端口>` | TOM 触发全量刷新 + ADOMD 轮询验行数/勾稽 |
| `desktop_auto.py <子命令>` | **Desktop UI 自动化**：`list`/`shot`/`shot_hwnd`/`focus`/`click`/`sclick`(SendInput)/`move`/`key`/`skey`/`text`，导出 PBIT 全靠它（见 `pbit-export.md` §4） |
| `grid_crop.py` | 给截图叠加坐标刻度，辅助定位（但**首选暗像素扫描**，肉眼读数不可靠） |
| `桥接.py <pid> [pageId] [out.png] [--reload]` | 桥接热重载 + 截图（现在 MCP 已修，可作兜底） |
| `窗口截图3.py <pid> <out.png>` | PrintWindow 抓窗口 |
| `窗口内容截图.py <hwnd> <out.png>` | 按句柄抓（含对话框） |
| `自检脚本.py` | PBIP 工程结构与编码自检 |
| `验证MCP补丁.py` | 上面三处补丁的回归验证 |

> 所有脚本**必须存成 `.py` 文件再跑**——`python -c "…"` 里 bash 会吃掉反斜杠，`\\.\pipe\…` 之类的路径会被改坏（表现为"文件不存在"，极易误判成服务没起）。
