# tools/ — 可复用脚本

全部是纯 Python（Windows 上跑过），中文名和英文名是**同一份脚本**，按自己顺手的挑一个用。

## 1. `刷新并验证.py` / `refresh_and_verify.py`

MCP 没有"刷新本地模型"的工具，这个脚本用 Power BI MCP 自带的 TOM 组件补上：

```bash
python 刷新并验证.py <端口>
```

- 端口从 MCP 的 `desktop_discover_instances` 拿（每个 Desktop 实例一个）
- 做三件事：`Model.RequestRefresh(RefreshType.Full)` + `SaveChanges()` → ADOMD 轮询到数据出现 →
  打印前 5 行样例 + 「四节加总 vs 全场比分」勾稽校验
- 依赖：`pythonnet` + `adomd/` 下的微软 DLL，路径可用环境变量 `POWERBI_MCP_DIR` 覆盖

## 2. `桥接.py` / `bridge_client.py`

直接调 Desktop Bridge（MCP 自带的客户端），做热重载 + 截图：

```bash
python 桥接.py <pid> [pageId] [输出.png] [--reload]
```

- 参数现在会自动包成 `{"args": {...}}`（打过补丁后 MCP 的 `bridge_screenshot` 也能直接用，此脚本作为兜底）
- 注意：`--reload` 热重载后**数据缓存会清空**，截图前要重新刷新

## 3. `窗口截图3.py` / `window_capture.py`

```bash
python 窗口截图3.py <pid> <输出.png>
```

- 用 ctypes 调 `PrintWindow` 抓窗口内容，**被其它窗口挡住也能抓到**
- 最小化的窗口抓不到（先还原）；桥接截图超时（30s）时用这个兜底

## 4. `技能自检.py` / `skill_lint.py`

```bash
python 技能自检.py <技能目录>
```

检查：BOM / 换行符 / 代码块配对 / frontmatter 必填项 / references 交叉引用是否有效 / 已知陈旧内容。

## 5. `verify_mcp_patches.py` / `验证MCP补丁.py`

```bash
python verify_mcp_patches.py
```

三处补丁的回归验证：并发写 4 线程 × 150 次不报错、桥接真机截图成功、备份路径指向系统临时目录。
（需要本机已装 powerbi-mcp + 有正在运行的 Power BI Desktop 才能验完整流程）
