# 配套 MCP 服务端：Power BI MCP

本目录是 `powerbi-crawler-data-prep` 技能配套的 **Power BI MCP 服务端**源码。

上游项目：[sulaiman013/powerbi-mcp](https://github.com/sulaiman013/powerbi-mcp)（开源）。
本副本在其基础上打了 **3 处本机实测出来的补丁**，用于打通「本地 Power BI Desktop 真机验证」这条链路
（Desktop Bridge 命名管道热重载、PBIP 连接器增强、桥接截图），是技能里 `references/powerbi-mcp.md`、`references/pbit-export.md` 所述能力的实现体。

## 目录结构

```
mcp/powerbi-mcp/
├── src/                  # 服务端源码（25 个文件）
│   ├── server.py                     # MCP 入口（82 个工具）
│   ├── desktop_bridge.py             # ⭐ Desktop Bridge 客户端（本机补丁）
│   ├── powerbi_pbip_connector.py     # ⭐ PBIP/TMDL/PBIR 读写（本机补丁，最大的一个）
│   ├── powerbi_tom_connector.py      # TOM 连活模型（刷新/度量值/关系）
│   ├── powerbi_xmla_connector.py     # XMLA 连接
│   ├── powerbi_rest_connector.py     # Power BI REST API
│   ├── dax_lint.py / dax_generator.py
│   ├── model_analysis.py / star_schema.py / bpa_authoring.py
│   ├── tmdl_authoring.py / pbir_authoring.py
│   ├── security/                     # 权限策略 / 审计日志 / PII 检测
│   └── ...
├── config/policies.yaml  # 安全策略
├── docs/                 # ARCHITECTURE / TESTING / TOOLS 三份文档
├── tests/                # 25 个测试文件
├── requirements-core.txt # 纯跨平台依赖（不需要 .NET）
├── requirements.txt      # 含 pythonnet / pyadomd（Windows 全功能）
└── pyproject.toml
```

## 接入方式

在 `~/.workbuddy/mcp.json`（或 Claude / CodeBuddy 的 MCP 配置）的 `mcpServers` 里加入：

```json
{
  "mcpServers": {
    "powerbi": {
      "command": "<你的 python 解释器路径>",
      "args": [
        "<本仓库路径>/mcp/powerbi-mcp/src/server.py"
      ],
      "env": {
        "PYTHONPATH": "<本仓库路径>/mcp/powerbi-mcp/src",
        "ADOMD_DLL_PATH": "<你放置 ADOMD/TOM DLL 的目录>",
        "TOM_DLL_PATH": "<你放置 ADOMD/TOM DLL 的目录>"
      }
    }
  }
}
```

把路径替换成你自己机器上的实际位置，然后重启会话即可加载。

## 依赖说明

**Python 侧**（必需）：

```bash
pip install -r requirements.txt
```

- 只用「离线分析」能力（PBIP/TMDL/PBIR 编辑、最佳实践审计、模型分析、DAX 校验）→ 装 `requirements-core.txt` 即可，**不需要 .NET**
- 要用「连活的 Power BI Desktop」能力（刷新、DAX 实测、桥接截图）→ 装 `requirements.txt`，需要 `pythonnet` + `pyadomd`

**ADOMD / TOM 的 .NET 程序集（不随本仓库分发）**：

`ADOMD_DLL_PATH` / `TOM_DLL_PATH` 指向的目录里需要放下面几个 DLL。
它们体积约 97 MB 且属于**微软的版权物**，因此不放进本仓库，请自行从 NuGet 获取：

- [`Microsoft.AnalysisServices.AdomdClient`](https://www.nuget.org/packages/Microsoft.AnalysisServices.AdomdClient)
- [`Microsoft.AnalysisServices.Tabular`](https://www.nuget.org/packages/Microsoft.AnalysisServices.Tabular)
- `Microsoft.AnalysisServices.Core`、`Microsoft.AnalysisServices`（随上面两个包一并提供）

把 NuGet 包（本质是 zip）解压，取其中的 `lib/` 下对应框架的 DLL 放到同一目录即可。

**环境变量**：见同目录 `.env.example`（Azure 云凭据是可选项，纯本地 Desktop 用法不需要）。

## 注意

- 本目录源码已做过密钥体检：**不含任何真实凭据**，测试文件里的邮箱均为示例假数据
- 日志、缓存、数据库文件不入库，首次运行会自动创建
