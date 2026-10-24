# SLM / CCD MCP

[English](README.en.md)

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-6A5ACD)](https://modelcontextprotocol.io/)
[![GitHub Issues](https://img.shields.io/github/issues/haamill/slm-ccd-mcp)](https://github.com/haamill/slm-ccd-mcp/issues)

用于在局域网内通过 [MCP（Model Context Protocol）](https://modelcontextprotocol.io/) 远程控制实验电脑上的 SLM 与 CCD。项目支持模拟模式（无硬件）与硬件模式（Windows + 厂商 SDK）。

## 功能

- 基于 Streamable HTTP 的 MCP 服务（[`/mcp`](https://github.com/haamill/slm-ccd-mcp)）
- SLM 图像上传、加载、偏移、光栅与恢复图
- CCD 参数读写与 RAW 采集，支持预览与下载
- 联合操作 `lab_load_and_capture`：一次请求内串行加载并采图
- 操作去重（`operation_id`）与结果恢复（`operation_get`）
- 令牌认证、Host/Origin 校验与受限文件访问

## 系统要求

- [Python 3.12+](https://www.python.org/downloads/)
- 依赖见 [`pyproject.toml`](pyproject.toml) 与 [`requirements.lock.txt`](requirements.lock.txt)
- 硬件模式还需要：
  - Windows x64
  - 已安装 HDSLM / ToupCam SDK
  - 交互式桌面会话（SLM 窗口需要消息泵）

## 安装

```bash
python -m venv .venv
. .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.lock.txt
pip install -e .
```

开发测试可额外安装：

```bash
pip install -e ".[dev]"
```

## 配置

- 模拟模式：[`config/simulation.toml`](config/simulation.toml)
- 硬件示例：[`config/hardware.example.toml`](config/hardware.example.toml)
- 客户端模板：[`client_examples/`](client_examples/)

通过环境变量提供令牌（默认变量名为 `LAB_MCP_TOKEN`）：

```bash
python -m lab_mcp init-token --output config/local.token
```

然后将 token 注入服务与客户端进程环境。

## 启动

### 模拟模式

```bash
python -m lab_mcp serve --config config/simulation.toml --mode simulate
```

### 硬件模式

```bash
python -m lab_mcp serve --config config/local.toml --mode hardware
```

也可以使用 [`scripts/start-lab-mcp.ps1`](scripts/start-lab-mcp.ps1)：

```powershell
.\\scripts\\start-lab-mcp.ps1 -ConfigPath config/local.toml
```

## 设备探测与绑定

硬件模式建议先运行：

```bash
python -m lab_mcp probe --config config/local.toml
```

结果写入 [`runtime/probe.json`](runtime/probe.json)。当设备型号或序列号不唯一时，应结合显示位置、面板尺寸和角色约束完成绑定。

## MCP 客户端

- [Codex 配置示例](client_examples/codex.config.toml)
- [Claude Desktop 配置示例](client_examples/claude.desktop.json)

请将示例中的 URL、主机名与认证头替换为你自己的环境值。

## 工具列表

- 状态与连接：`lab_status`、`lab_connect`、`lab_disconnect`
- 资产：`asset_list`、`asset_upload_begin`、`asset_upload_chunk`、`asset_upload_finish`
- SLM：`slm_load_image`、`slm_set_offset`、`slm_set_grating`、`slm_make_amplitude_grating`、`slm_show_uniform`、`slm_restore`
- CCD：`ccd_get_settings`、`ccd_set_settings`、`ccd_capture`
- 联合与恢复：`lab_load_and_capture`、`operation_get`

## 测试

```bash
pytest -q
```

CLI 冒烟测试：

```bash
python -m lab_mcp smoke --url http://127.0.0.1:8765/mcp
```

> 硬件冒烟测试需要显式提供 `--allow-hardware --image --exposure-us`。

## 项目结构

```text
slm-ccd-mcp/
├── src/lab_mcp/          # 核心实现
├── tests/                # 测试
├── config/               # 配置示例
├── client_examples/      # 客户端配置模板
├── scripts/              # PowerShell 辅助脚本
├── docs/                 # 运行与验收文档
├── pyproject.toml
└── requirements.lock.txt
```

## 安全与限制

- 必须携带有效访问凭证。
- 启用 Host/Origin 校验，避免跨源滥用。
- 不提供任意 shell 执行或任意路径文件访问。
- `runtime/` 可能包含采集结果与运行记录，默认应视为本地运行数据。
- 服务不对光学效果做自动保证，实际效果需实验侧独立验证。

## 贡献与许可证

欢迎通过 [Issue](https://github.com/haamill/slm-ccd-mcp/issues) 或 [Pull Request](https://github.com/haamill/slm-ccd-mcp/pulls) 反馈问题与改进建议。

当前仓库未包含 `LICENSE` 文件；在复用前请先确认授权方式。
