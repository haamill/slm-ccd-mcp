# SLM / CCD MCP

用于在局域网内通过 MCP（Model Context Protocol）远程控制实验电脑上的 SLM 与 CCD。  
项目支持模拟模式（无硬件）与硬件模式（Windows + 厂商 SDK）。

## 功能概览

- 基于 Streamable HTTP 的 MCP 服务（`/mcp`）
- SLM 图像上传、加载、偏移、光栅、恢复图
- CCD 参数读写与 RAW 采集（含预览与下载）
- 联合操作 `lab_load_and_capture`（一次请求内串行加载并采图）
- 操作去重（`operation_id`）与结果恢复（`operation_get`）
- 令牌认证 + Host/Origin 校验 + 受限文件访问

## 工作方式（简述）

1. 客户端通过 HTTP 调用 MCP 工具。  
2. 控制层统一串行执行设备修改与采集。  
3. SLM 与 CCD 数据写入 `runtime/`（不建议提交）。  
4. RAW 文件通过带认证的下载端点获取。

## 系统要求

- Python 3.12+
- 依赖：见 `pyproject.toml` 与 `requirements.lock.txt`
- 硬件模式额外要求：
  - Windows x64
  - 已安装 HDSLM / ToupCam SDK
  - 运行于交互式桌面会话（SLM 窗口需要消息泵）

## 安装

```bash
python -m venv .venv
. .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.lock.txt
pip install -e .
```

开发测试可额外安装：

```bash
pip install -e ".[dev]"
```

## 配置

- 模拟模式：`config/simulation.toml`
- 硬件示例：`config/hardware.example.toml`（复制为你自己的本地配置）
- 客户端模板：`client_examples/`

令牌通过环境变量提供（默认 `LAB_MCP_TOKEN`）：

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

PowerShell 也可使用启动脚本：

```powershell
.\scripts\start-lab-mcp.ps1 -ConfigPath config/local.toml
```

## 设备探测与绑定

硬件模式建议先探测：

```bash
python -m lab_mcp probe --config config/local.toml
```

结果写入 `runtime/probe.json`。  
当设备型号/序列号不唯一时，应结合显示位置、面板尺寸和角色约束完成绑定。

## MCP 客户端连接示例

- Codex：`client_examples/codex.config.toml`
- Claude Desktop（mcp-remote）：`client_examples/claude.desktop.json`

请将示例中的 URL、主机名与认证头替换为你自己的环境值。

## 工具列表（18）

- 状态与连接：`lab_status` `lab_connect` `lab_disconnect`
- 资产：`asset_list` `asset_upload_begin` `asset_upload_chunk` `asset_upload_finish`
- SLM：`slm_load_image` `slm_set_offset` `slm_set_grating` `slm_make_amplitude_grating` `slm_show_uniform` `slm_restore`
- CCD：`ccd_get_settings` `ccd_set_settings` `ccd_capture`
- 联合与恢复：`lab_load_and_capture` `operation_get`

## 项目结构

```text
slm-ccd-mcp/
├── src/lab_mcp/          # 核心实现（设备、控制、存储、MCP 服务、CLI）
├── tests/                # 测试
├── config/               # 配置示例
├── client_examples/      # 客户端配置模板
├── scripts/              # PowerShell 辅助脚本
├── docs/                 # 通用运行与验收文档
├── pyproject.toml
└── requirements.lock.txt
```

## 测试与验证

```bash
pytest -q
```

也可运行 CLI 冒烟：

```bash
python -m lab_mcp smoke --url http://127.0.0.1:8765/mcp
```

> 硬件冒烟需要显式提供 `--allow-hardware --image --exposure-us`。

## 硬件集成注意事项

- SLM 调用与窗口消息泵由同一 owner 线程管理。
- HDSLM 枚举在 owner 生命周期内受约束，显示拓扑变化后应重新探测绑定。
- 仅允许配置白名单目录（`input_roots`）中的输入文件。
- 服务不对光学效果做自动保证，实际效果需实验侧独立验证。

## 安全与限制

- 必须携带有效访问凭证
- 启用 Host/Origin 校验，避免跨源滥用。
- 不提供任意 shell 执行或任意路径文件访问。
- `runtime/` 可能包含采集结果与运行记录，默认应视为本地运行数据。

## 贡献与许可证

- 欢迎通过 Issue / Pull Request 反馈问题与改进建议。
- 当前仓库未包含 `LICENSE` 文件；在复用前请先确认授权方式。
