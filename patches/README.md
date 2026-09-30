# patches/ — 配套 Power BI MCP 的 3 处本地补丁

`mcp/` 目录里的源码**已经打过这 3 个补丁**。这个目录是给两种情况用的：

1. 你 `git clone` 的是[上游原始版本](https://github.com/sulaiman013/powerbi-mcp)，想快速套上同样的修复；
2. 上游以后更新了，你想把这几处修复**重新打一遍**。

## 用法

```bash
# 只看需要改什么，不动文件
python apply_patches.py --mcp-dir <你的 powerbi-mcp 目录> --check

# 真正打补丁（幂等，已经打过的会跳过）
python apply_patches.py --mcp-dir <你的 powerbi-mcp 目录>
```

脚本按「精确文本匹配 → 替换」工作，每个补丁都带一个**标记字符串**：
文件里已经出现标记就跳过（所以可以反复执行）；匹配不到就报警告（说明上游改了这段，需要人工介入）。
打完补丁记得**重启 MCP 服务**——它是常驻进程，改完源码不会自动重载。

## 三处补丁分别修什么

### 1. 桥接参数契约（`src/desktop_bridge.py`）

- **现象**：`bridge_screenshot` / `bridge_reload` 报 `Bridge error -32602: Request arguments are required.`
- **原因**：Desktop **26.07+** 的 Desktop Bridge 在 manifest 里声明 `params.required = ["args"]`，
  业务参数必须包一层：`{"args": {"pageId": "...", "scale": 1.5}}`；原代码传的是平铺的 `{"pageId", "scale"}`。
- **修法**：新增 `call_with_args()`，先试 `{"args": {...}}`，遇到 `-32602` 再退回平铺形态（兼容新旧版本）；
  `capture_snapshot` 优先调 `report.snapshot.capture/v2`（支持区域截图），失败退回 v1。

### 2. 并发写文件损坏（`src/powerbi_pbip_connector.py` → `_write_text`）

- **现象**：两个 `pbir_add_page` 同时调用时，报
  `[WinError 32] 另一个程序正在使用此文件 … pages.json.tmp -> pages.json`，`Report/definition/pages/pages.json` 可能被写坏。
- **原因**：原子写用的是固定临时名 `<文件名>.tmp`，并发调用会撞车。
- **修法**：进程级 `threading.RLock()` 串行化写入 + 临时文件名带上 `pid` 和线程 id。

### 3. 备份目录乱丢（`src/powerbi_pbip_connector.py` → `create_backup`）

- **现象**：每轮编辑都会在**项目文件夹旁边**生成 `xxx_backup_20261001_010928/`，用户工作区越来越乱。
- **修法**：备份改写到系统临时目录 `%TEMP%/powerbi-mcp-backups/`（仍然可恢复，只是不占用户目录）。

## 回归验证

```bash
python ../tools/verify_mcp_patches.py       # 4 线程 × 150 次并发写 + 桥接真机截图 + 备份路径断言
```
