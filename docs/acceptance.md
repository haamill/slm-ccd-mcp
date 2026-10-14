# 验收与证据边界

当前 SLM2 默认偏移 **(+10,+61)**，1000×1000小图放置(470,161)。

## 已验证的代码路径

- 83项测试通过，2项Windows文件symlink权限跳过（独立审查修复后）；目录junction攻击测试已在Windows实际通过。
- 真实MCP Python Client连接模拟ASGI，完成上传、精确投屏参数、CCD设置、采图、PNG和认证RAW下载hash核对。
- SDK fake验证SLM一次枚举 / 同线程、同SN绑定、相机范围 / 读回 / 恢复及新帧选择。
- 并发同ID只执行一次，网络取消后仍可取结果，状态查询不被采图锁阻塞。
- compileall与pip check通过。

这些是软件与模拟证据，不是实验光学成绩。

## 独立TCP模拟验证

先启动模拟服务，并让验证进程读取相同私有令牌：

```powershell
$env:LAB_MCP_TOKEN = (Get-Content -LiteralPath config/local.token -Raw).Trim()
& '.venv\Scripts\python.exe' -m lab_mcp smoke --url http://127.0.0.1:8765/mcp
```

smoke通过标准网络MCP上传1000×1000 native10图、加载(+10,+61)、设置相位载波、读回6000µs曝光、采图、下载并核对SHA256；只在simulate模式默认允许运行。实际本机临时验收可能使用8766以避免占用正式端口，结果单独记LOG。

## 现场设备验收

用户允许关闭ToupView / MagicHolo，两者正常退出。当前probe出现两个同SN的SLM，保存runtime/probe.json，初始probe归档runtime/probe-initial.json；已请求物理SLM2对应关系，未向SLM提交。

真实CCD已通过正式hardware网关的TCP MCP采到一张全幅暗帧：5312×4592、uint16容器、12有效位。保持2000µs曝光（测试期间AE关闭），丢弃3张新帧后保存，RAW认证下载SHA256相同。断开时原AE/曝光/增益及RAW选项恢复，全部读回通过。证据runtime/hardware-dark-verification.json及runtime/captures/5a26259e-d2c4-4d76-b9aa-cf60021901ee/；帧均值16.065/4095，激光未开，不能证明光栅/衍射行为。

2026-10-14新现场步骤：按用户D:/lab/zty/2文档第1组，SLM1 WORKING_STRAIGHT8bit与SLM2 DECODE_Qp0原RGB10文件经MCP上传、解码、完整panel加载成功，offset0，不加额外载波/透镜。两屏选定x3072/x4992，与原始code hash一致，窗口alive/unobscured且未挂起。当前保留该组，ToupView运行，CCD由用户手动定位，尚未收到光学亮点反馈。证据runtime/document_pair_20261014；没有自动执行六组采图。

随后用户反馈角色可能反向：已停止原owner、重新枚举并对调试绑SLM1 x4992/SLM2 x3072，同一组码值和0offset再次提交成功，窗口健康/hash相同，当前保留的是对调组。证据runtime/document_pair_swapped_20261014；实体角色与光学定位点仍等待用户观察确认，不能把两次软件提交成功当作物理角色证明。

硬件smoke需要全部显式参数：

```powershell
& '.venv\Scripts\python.exe' -m lab_mcp smoke --url http://10.195.186.75:8765/mcp --allow-hardware --image '<用户确认的图.npy>' --exposure-us 6000
```

曝光6000仅为命令示例，不是已批准的现场值。硬件模式不叠模拟测试载波，当前图作为显式恢复图登记。若只验证CCD或保留当前图案，应通过MCP工具分别连接 / 采图，避免运行全流程smoke。

记录当前绑定、窗口健康 / 遮挡、输入和panel hash、曝光/增益/AE实际读回、有效RAW位深、保存帧与丢帧身份、预览和下载hash。SLM1未插入时不声称双屏验证。

## 另一台电脑验收

1. 使用同一token和实际WLAN IP配置Codex / Claude。
2. 成功执行lab_status并看到hardware/simulate及角色状态。
3. 用户明确调用现场参数或图案，再采图，看到新的inline预览。
4. 经认证下载RAW，SHA256与manifest一致。

同一电脑使用私网IP连接成功，只证明本机网关监听和协议可用；不能代替另一台电脑穿过WLAN / 防火墙的实测。当前跨电脑连接及SLM1接入的验收状态在LOG / REPORT更新。
