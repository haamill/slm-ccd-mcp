# SLM / CCD MCP

在连接实验设备的Windows电脑上运行MCP服务，让另一台局域网电脑的Codex / Claude客户端控制SLM图案、位置和光栅，以及CCD曝光与RAW采集。

项目仓库：[haamill/slm-ccd-mcp](https://github.com/haamill/slm-ccd-mcp)。本机工作目录为 `D:/ExpSoftware/slm-ccd-mcp`。

## 当前状态

**2026-10-18恢复实测：MCP在线，端点`http://10.195.186.75:8765/mcp`不变；两路SLM已重新探测绑定为connected，窗口健康，requires_rebind清除。CCD按用户后续许可短暂重连后恢复streaming，8000µs/增益100/AE关闭均与维护前读回相同。未额外采图。下文10月14日加载为历史实验记录。**

本次保留的是SQLite最后成功操作的图案，而非10月14日初始文档屏：SLM1为8bit小图、offset(0,0)；SLM2为显式8bit小图、offset(+10,+61)，并恢复原有附加载波fx=-0.5、fy=0。两屏最终数组hash与维护前最后成功提交相同。完整证据在`runtime/slm_rebind_20261018/recovery.json`。

**2026-10-14：服务代码与审查修复已完成，83项测试通过、2项Windows文件symlink权限跳过；真实CCD暗帧通过。按用户文档的第一组已完成双SLM满屏加载并保留显示，用户正在用CCD手动定位。**

- 官方MCP2.3.0，18个工具、3类资源、Bearer认证与Host/Origin校验。
- 支持图片分块上传、8bit/native10、精确拼板、相位载波/LUT、独立振幅光栅。
- CCD支持曝光/增益/AE读回、RAW新帧、软件ROI、inline预览与认证下载。
- 控制串行、联合加载采图、state_version、请求去重和partial结果保存。
- 真CCD采集5312×4592、12bit RAW，曝光2000µs读回、认证下载SHA256及原设置恢复通过；激光关闭，预览接近黑色。
- 第1组WORKING_STRAIGHT + DECODE_Qp0已实际SDK提交。用户指出历史角色映射可能反向后已对调重新加载，8/10bit、panel位置/窗口健康及输入hash一致；实体对应和光学亮点待用户手动观察确认。另一台电脑连通待验收。

## 设备与当前绑定

| 角色 | 当前信息 |
|---|---|
| SLM1 | 当前试绑桌面(4992,0)，HDSLM80RPS / UPL0080，1920×1200，WORKING_STRAIGHT GRAY8 |
| SLM2 | 当前试绑桌面(3072,0)，HDSLM80RPS / UPL0080，1920×1200，DECODE_Qp0 RGB10，无虚拟透镜 |
| SLM2偏移 | **(+10,+61)**，相对居中；1000×1000小图左上角(470,161) |
| CCD | IUA24500KMA，单色YYYY RAW，12有效位，5312×4592；已实拍暗帧 |
| 局域网地址 | WLAN 10.195.186.75；正式端点已监听 http://10.195.186.75:8765/mcp |

本次文档图案均为完整面板，加载 **offset0**、无额外软件光栅/透镜；上表(+10,+61)仍为小图相对居中的通用默认值，不重复加到本次满屏图。MCP未连接CCD，由用户手动找定位亮点。首次/对调证据分别在`runtime/document_pair_20261014/`和`runtime/document_pair_swapped_20261014/`，不进入Git；相同SN不能证明实体模式，当前试绑等待观察确认。

SDK直接引用 `D:/ExpSoftware/HDSLM_SDK` 和 `D:/ExpSoftware/toupcamsdk.20260908`，不修改或复制厂家DLL。旧偏移(+10,+69)仅作历史追溯。IP和插拔变化后须重新核验绑定。

## 安装

```powershell
Set-Location -LiteralPath 'D:\ExpSoftware\slm-ccd-mcp'
& 'D:\Program Files\Python312\python.exe' -m venv .venv
& '.venv\Scripts\python.exe' -m pip install -r requirements.lock.txt
& '.venv\Scripts\python.exe' -m pip install -e .
```

本机venv已安装。详见[运行说明](docs/operations.md)。

## 启动

首次生成令牌（本机已有，命令不覆盖已有文件）：

```powershell
& '.venv\Scripts\python.exe' -m lab_mcp init-token --output config/local.token
```

真实网关使用本机私有配置：

```powershell
& '.\scripts\start-lab-mcp.ps1' -ConfigPath config/local.toml
```

启动网关不会立即连接硬件；远端调用lab_connect才打开设备。Windows需保持交互式桌面会话，服务进程持续处理投屏窗口消息。ToupView/MagicHolo占用或遮挡时先由用户处理，服务不自动关闭其他程序。

模拟服务：

```powershell
& '.\scripts\start-lab-mcp.ps1' -ConfigPath config/simulation.toml -Mode simulate
```

停止本项目owner后探测：

```powershell
& '.venv\Scripts\python.exe' -m lab_mcp probe --config config/hardware.example.toml
```

## 另一台电脑连接

- [Codex配置模板](client_examples/codex.config.toml)：使用HTTP URL和LAB_MCP_TOKEN环境变量。
- [Claude Desktop模板](client_examples/claude.desktop.json)：使用固定版本mcp-remote桥接，LAB_MCP_AUTH_HEADER由客户端进程环境提供。
- [运行说明](docs/operations.md)包含具体配置、私网防火墙脚本和调用顺序。
- [验收步骤](docs/acceptance.md)区分模拟、本机TCP、现场硬件和跨电脑证据。

本机令牌在config/local.token，不进入Git；将相同令牌安全配置到客户端。网络profile、防火墙及校园WLAN客户端隔离需在另一台电脑实际核验。

## 常用工具

| 目的 | 工具 |
|---|---|
| 状态/连接 | lab_status、lab_connect、lab_disconnect |
| 图片 | asset_upload_begin/chunk/finish、asset_list、slm_load_image |
| 位置/载波 | slm_set_offset、slm_set_grating |
| 振幅光栅/均匀码/恢复 | slm_make_amplitude_grating、slm_show_uniform、slm_restore |
| 相机 | ccd_get_settings、ccd_set_settings、ccd_capture |
| 联合操作/结果恢复 | lab_load_and_capture、operation_get |

SLM图片保持原尺寸/码值；full panel不重复偏移，附加光栅每次从原图重算。相位码域与LUT合成分开，振幅图不按相位取模相加。RAW保存不受预览亮度映射影响。

## 数据与目录

```text
slm-ccd-mcp/
├── AGENTS.md / README.md / LOG.md / REPORT.md
├── pyproject.toml / requirements.lock.txt
├── src/lab_mcp/       # 图像、存储、设备、协调、MCP、CLI
├── tests/            # 纯数组、SDK fake、事务、真实MCP Client
├── config/           # 可提交示例 + 不提交的本机绑定/令牌
├── client_examples/  # 另一台电脑的客户端模板
├── scripts/          # 启动及显式Private防火墙配置
├── docs/             # 设计、计划、运行和验收
└── runtime/          # 不提交：探测、操作SQLite、assets、RAW/PNG/manifest
```

运行失败保留partial证据，不自动删除RAW。输入、凭据和本机配置由.gitignore排除。SDK hash与窗口状态是软件证据，真实光学效果仍须开激光后实拍核验。
