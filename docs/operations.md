# 运行与连接指南

本文档给出通用运行流程，不包含任何特定实验环境参数。

## 1) 安装

```bash
python -m venv .venv
. .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.lock.txt
pip install -e .
```

## 2) 生成访问令牌

```bash
python -m lab_mcp init-token --output config/local.token
```

将 token 注入服务端与客户端进程环境（默认环境变量名：`LAB_MCP_TOKEN`）。

## 3) 启动服务

### 模拟模式

```bash
python -m lab_mcp serve --config config/simulation.toml --mode simulate
```

### 硬件模式

```bash
python -m lab_mcp serve --config config/local.toml --mode hardware
```

Windows 也可用辅助脚本：

```powershell
.\scripts\start-lab-mcp.ps1 -ConfigPath config/local.toml
```

## 4) 硬件探测与绑定

```bash
python -m lab_mcp probe --config config/local.toml
```

- 输出写入 `runtime/probe.json`
- 探测用于绑定核对，不会自动完成角色映射
- 当设备 SN/型号重复时，需结合桌面位置与分辨率确认角色

## 5) MCP 客户端配置

- Codex 示例：`client_examples/codex.config.toml`
- Claude Desktop 示例：`client_examples/claude.desktop.json`

请替换示例中的 URL 与认证相关占位符。

## 6) 推荐调用顺序

1. `lab_status`：读取当前状态
2. `lab_connect`：连接所需角色
3. `asset_upload_*` + `slm_load_image`：上传并加载图案
4. `slm_set_offset` / `slm_set_grating`：调整位置与载波
5. `ccd_get_settings` / `ccd_set_settings`：设置并读回相机参数
6. `ccd_capture` 或 `lab_load_and_capture`：采集并获取下载引用
7. `operation_get`：用于恢复可能丢失的操作响应

## 7) 网络与安全

- 服务与下载端点都需要有效访问凭证
- 启用 Host/Origin 校验
- 输入文件受 `input_roots` 白名单约束
- 如需防火墙规则，可使用：

```powershell
.\scripts\setup-lan-firewall.ps1 -LocalIp <SERVER_IP> -RemoteAddress <CLIENT_IP>
```

## 8) 运行数据

- 采集结果默认在 `runtime/captures/<capture_id>/`
- 运行过程中会写入操作与元数据记录
- 建议将 `runtime/` 视为本地运行数据，不纳入版本控制
