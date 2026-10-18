# 安装、启动与客户端连接

## 当前本机配置

2026-10-18维护更新：两SLM已重新探测绑定并恢复connected（SLM1 x4992、SLM2 x3072），CCD按许可短暂重连后为streaming、8000µs/gain100/AE0。恢复的是当前日志最后成功图案：SLM1 8bit小图offset0,0；SLM2显式8bit小图offset10,61、原附加fx=-0.5。下方10月14日首组为历史配置描述，不能据此重新覆盖当前实验图案。

项目：`D:/ExpSoftware/slm-ccd-mcp`。2026-10-14两块HDSLM80RPS / UPL0080 / 1920×1200完成今日枚举和窗口核验。第一轮历史位置映射被用户反馈可能反向，已对调试绑SLM1(4992,0)、SLM2(3072,0)，实体角色仍等待观察确认。当前保留用户文档FIRST_SIX第1组：SLM1 WORKING_STRAIGHT GRAY8、SLM2 DECODE_Qp0 RGB10，满屏offset0、无额外透镜/载波；用户通过ToupView找像，MCP未连接CCD。CCD此前已实拍IUA24500KMA单色YYYY RAW、12bit、5312×4592。SLM2通用小图相对居中默认偏移 **(+10,+61)**，不加到本次满panel图。

WLAN地址：`10.195.186.75`。本机私有绑定配置在 `config/local.toml`，令牌在 `config/local.token`；二者不受Git跟踪。正式网关已启动且保留两SLM当前显示，MCP CCD为disconnected；先结束ToupView对相机的占用，再显式调用ccd连接工具可移交给MCP。IP或插拔变化后重新核验配置。跨电脑真实连接仍需要在另一台电脑验收。

## 安装

PowerShell中：

```powershell
Set-Location -LiteralPath 'D:\ExpSoftware\slm-ccd-mcp'
& 'D:\Program Files\Python312\python.exe' -m venv .venv
& '.venv\Scripts\python.exe' -m pip install -r requirements.lock.txt
& '.venv\Scripts\python.exe' -m pip install -e .
```

本机已经建立venv。SDK直接使用配置的本机目录；无需安装厂家GUI作为MCP依赖，也不把DLL复制进仓库。

## 令牌与启动

首次生成私有令牌（已有文件时命令拒绝覆盖）：

```powershell
& '.venv\Scripts\python.exe' -m lab_mcp init-token --output config/local.token
```

真实设备服务：

```powershell
& '.\scripts\start-lab-mcp.ps1' -ConfigPath config/local.toml
```

启动网关不会立即打开SLM或CCD。远端明确调用 `lab_connect` 才连接设备。保持服务进程与Windows桌面会话运行；SLM窗口需要该进程持续处理消息。Ctrl+C正常结束会尝试恢复注册图案、相机原设置并关闭本进程投屏窗口；不能保证窗口关闭后面板继续显示本进程图案。

本机模拟服务：

```powershell
& '.\scripts\start-lab-mcp.ps1' -ConfigPath config/simulation.toml -Mode simulate
```

## 探测与绑定

停止本项目owner后运行：

```powershell
& '.venv\Scripts\python.exe' -m lab_mcp probe --config config/hardware.example.toml
```

结果保存在 `runtime/probe.json`。探测只枚举，不打开投屏或CCD。不要把Windows标签0/1当SDK index；SN可能重复，需要同时设置serial、desktop_xy与panel_wh。接入SLM1时关闭owner，重新探测并明确两个角色；不要沿用旧屏幕编号。

ToupView可能占用相机，MagicHolo可能与SDK窗口重叠。MCP会报告占用 / 遮挡，不自动关闭其他应用。SDK状态与图像hash是软件证据，光学有效性仍须CCD实拍核验。

## 另一台电脑：Codex

将 [客户端配置](../client_examples/codex.config.toml) 合并到另一台电脑的Codex配置中。令牌通过 `LAB_MCP_TOKEN` 环境变量提供，须让Codex进程继承该变量；在桌面应用已启动后改终端变量不会改变已有进程环境。

本机已核验CLI语法，对另一台电脑可使用：

```powershell
codex mcp add slm_ccd_lab --url http://10.195.186.75:8765/mcp --bearer-token-env-var LAB_MCP_TOKEN
```

配置中将tool_timeout_sec设为180，以覆盖默认120秒采图上限。相关参数依据 [OpenAI官方MCP文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。本项目没有替用户修改任何已有Codex配置。

## 另一台电脑：Claude Desktop / Claude Code

Claude Desktop使用 [stdio桥接模板](../client_examples/claude.desktop.json)，需要客户端电脑可用的Node / npx。模板固定 `mcp-remote@0.14.3`；在Claude进程环境设置 `LAB_MCP_AUTH_HEADER`，其内容为 `Bearer ` 加本机令牌，再重新启动Claude。

模板参数 `Authorization:${LAB_MCP_AUTH_HEADER}` 避免Windows npx参数中空格拆分；`--allow-http` 用于此局域网HTTP端点。这些行为依据 [桥接工具维护者文档](https://github.com/punkpeye/mcp-remote)。也可使用该工具的header-file方式保存客户端私有认证头。

Claude Code支持原生HTTP MCP配置，按 [Anthropic官方文档](https://code.claude.com/docs/en/mcp) 为同一端点设置Authorization请求头。客户端具体版本、桥接包启动和网络可达性需要另一台电脑验证；本机未安装或修改它的客户端。

## 网络与防火墙

实验服务只绑定配置的私网接口。MCP与RAW下载都需要令牌。若另一台电脑无法连接，先检查IP、同网可达性和端口，再检查Windows网络profile / 防火墙。当前ZJUWLAN为Public；以下脚本仅配置Private规则，因此不能直接保证这个校园网络可连接。若保持Public，需由用户/管理员按客户端IP配置同等受限Public规则；本轮没有修改网络分类或开放防火墙。

管理员PowerShell可以显式为客户端IP添加受限Private规则：

```powershell
& '.\scripts\setup-lan-firewall.ps1' -LocalIp 10.195.186.75 -RemoteAddress '<客户端IP>'
```

脚本不会自动执行，也不修改网络profile或开放公网。校园WLAN可能启用客户端隔离；服务代码不能绕过网络设备的隔离策略。

## 调用顺序

1. `lab_status` 查看mode、角色连接、图案与state_version。
2. `lab_connect` 连接指定角色；SLM1缺席可只传slm2、ccd。
3. 上传NPY / PNG / BMP，或使用配置allowlist中的本机路径；`slm_load_image` 对8/10bit与panel/centered明确声明。
4. `slm_set_offset` 设置小图相对居中位置；`slm_set_grating` 设置绝对载波cycle/pixel，加载新图默认附加载波为0。
5. `ccd_get_settings` / `ccd_set_settings` 读回或设置微秒曝光、SDK增益和AE。
6. `ccd_capture` 或 `lab_load_and_capture` 获取新RAW、inline预览和认证下载引用。
7. 对修改请求提供UUID operation_id；丢失响应后用 `operation_get` 查询或以同ID重发，不猜测重做。

SLM1只支持加载8bit振幅图和生成独立振幅光栅，不对已有振幅全息图猜测相位取模叠加。

## 数据与关闭

RAW位于 `runtime/captures/<capture_id>/raw_NNN.npy`，预览为preview.png，manifest记录配置、帧身份、丢帧和hash。SQLite保存规范化命令/参数、各阶段开始/完成和结果；既有旧记录缺失字段保留为空，不能推测补全。失败保留partial，预览不改变RAW。持久化失败返回uncertain及operation_id，同进程查询也可取回内存结果，重启保留running/intent为uncertain，不自动重放。`lab_disconnect`释放设备；它不会结束MCP网关。
