# 关于 `adomd/` 目录（本仓库未附带）

Power BI MCP 需要两份**微软的客户端库**才能连本地模型引擎：

- `Microsoft.AnalysisServices.AdomdClient.dll`（ADOMD.NET，跑 DAX 查询用）
- `Microsoft.AnalysisServices.Tabular.dll` + `Core` / `Json` / `SPClient.Interfaces` / `AnalysisServices.dll`
  （TOM，建模对象模型，用来触发刷新、读表结构）

## 为什么没有随仓库分发

1. **版权**：这些 DLL 版权归 Microsoft，从 NuGet 包解出来的整包结构（约 97 MB）不适合直接进公开仓库；
2. **体积**：占仓库 97 MB，克隆体验很差。

## 怎么获取

任选一种，然后在仓库根目录建 `adomd/` 放进这些 DLL：

**方式一：从已安装的 Power BI Desktop 取（最省事）**

```
C:\Program Files\Microsoft Power BI Desktop\bin\
```
把其中的 `Microsoft.AnalysisServices.AdomdClient.dll`、`Microsoft.AnalysisServices.Tabular.dll`、
`Microsoft.AnalysisServices.Core.dll`、`Microsoft.AnalysisServices.Tabular.Json.dll` 复制到 `adomd/`。

**方式二：从 NuGet 取（版本可控）**

```
Microsoft.AnalysisServices.AdomdClient
Microsoft.AnalysisServices.Tabular
```
（`.nupkg` 改后缀解压，从 `lib/net*/` 里取对应 framework 的 DLL）

## 配好之后

MCP 配置里指向它即可：

```jsonc
"env": {
  "ADOMD_DLL_PATH": "<仓库路径>/adomd",
  "TOM_DLL_PATH": "<仓库路径>/adomd"
}
```

脚本 `tools/刷新并验证.py` 也读同一个目录（可用环境变量 `POWERBI_MCP_DIR` 覆盖）。
