# 项目报告

## 1. 目标与当前阶段

本项目在连接 SLM 和 CCD 的 Windows 实验电脑上提供 MCP 服务，让另一台局域网电脑通过本地 Codex / Claude 等 MCP 客户端调用实验操作。用户常用操作为 SLM 图片加载位置、附加光栅与一级衍射位置调整，以及 CCD 曝光等相机参数。

2026-10-13 用户确认首版范围、SLM2相对居中偏移 **(+10,+61)**，并批准设计与实施计划；服务实现、审查修复与83项软件测试已完成，代码已发布至用户指定仓库。2026-10-20最新维护重新绑定两SLM，同一MCP端点18工具可用，CCD8000µs/gain100/AE0且64×64软件ROI新帧实采通过。后文按阶段保留设计、实现和现场记录，当前状态以最新维护章节为准。

## 2. 已完成的调查与依据

### 2.1 SDK 文件

- HDSLM SDK：`D:/ExpSoftware/HDSLM_SDK`。
- 已有 Python 包装：`HDSLM_SDK/Samples/HDSLM_python_api_demo/hdslm_sdk.py`。
- CCD SDK：`D:/ExpSoftware/toupcamsdk.20260908`，含 `python/toupcam.py` 和 `win/x64/toupcam.dll`。

已有 SDK 可以直接提供图像数组显示、图像位置、相机曝光 / 增益、RAW 格式查询和持续采图接口。使用本机路径引用厂家组件，项目自身组织设备适配、控制协调、协议和结果管理。

### 2.2 已验证控制链来源

历史项目 `C:/Syncthing/Python/EccentricityHolography` 中的 `citl_hdslm_adapter.py`、`multiframe_slm_service.py` 和 `citl_toupcam.py` 提供参考：

- SLM SDK 调用在单一专用线程中执行，并持续处理 Win32 消息。
- SDK 枚举一次，后续操作使用已绑定的角色和窗口信息。
- 投屏前由软件生成精确的完整 panel，不依赖图片查看器缩放和隐式灰度转换。
- 相机保持单色 RAW 流，按照图案更新后的主机单调时间、曝光间隔和新帧丢弃策略选帧。
- 参数、数组 hash、帧记录和恢复结果分别保存。

这些源文件只读参考；新项目应独立实现必要部分，不导入旧项目的大型实验入口或复制研究工作流。

## 3. 当前参数与历史参数

| 参数 | 本项目处理 | 依据 |
|---|---|---|
| SLM2 相对居中偏移 | 当前 (+10,+61) | 用户当日更新 |
| 历史 (+10,+69) | 仅在历史来源说明保留 | 旧实验交接 |
| 振幅屏连接状态 | 允许缺席 | 用户当日说明 |
| 两屏尺寸 / 型号 | 1920×1200 / HDSLM80RPS 作为待核验提示 | 历史记录 |
| SDK index / 桌面坐标 | 今日探测后联合绑定，不固定旧值 | 热插拔可能变动 |
| CCD 格式 | 优先 YYYY RAW，以当前读回有效位深为准 | 历史 12 有效位 |
| 曝光 / 增益 / ROI | 连接时读回，按工具调用显式调整 | 历史值不是今日默认 |
| LUT / 波长 / 像元 | 显式配置才启用相位标定或物理换算 | 旧标定范围有限 |

对于 1920×1200 panel 上的 1000×1000 输入，居中左上角为 ((1920−1000)/2,(1200−1000)/2)=(460,100)，加当前偏移得到 (470,161)。这个规则只规定加载位置，不代表光学图像中心或 CCD ROI。

## 4. 计划采用的技术路线

### 4.1 MCP 与设备协调

采用 Python 与官方 MCP SDK，通过 Streamable HTTP 提供局域网 `/mcp` 端点。MCP 工具进入统一协调层；硬件修改串行执行，联合加载 / 采图保持完整操作边界。SLM 调用仍由专用消息线程执行，相机回调只获取并发布帧。

服务使用交互式桌面会话而非 Windows Session 0 服务，以满足投屏窗口需求。单实例锁避免项目启动多个 SDK owner。客户端断开后设备 owner 继续存活；不会通过重启或重试猜测命令是否执行。

### 4.2 图像与光栅

输入解码、码值检查、光栅合成和 panel 放置在硬件提交之前完成。保留 uint8 / uint16 语义；不自动改变尺寸、方向、位深或亮度。SLM2 的附加相位载波默认关闭，避免对已有载频的图再次叠加。

没有 LUT 时，显式码域光栅只提供名义相位控制；有 LUT 时，需要将已知基图码解释为 LUT 相位，加入载波，再执行圆周最近相位查表。振幅屏单独使用振幅光栅生成接口，不采用相位图的取模相加方法。物理一级位置只能通过新的 CCD 实拍核验。

### 4.3 CCD 与结果

CCD 工具使用微秒曝光及 SDK 增益单位，设置后读回。RAW 保留原生行顺序和有效位深；软件 ROI 只裁取保存区域，不改变传感器坐标定义。采图记录更新边界、主机及设备帧身份、被丢弃帧和实际设置。

完整 RAW 以 NPY 保存，预览以 PNG 返回，参数和运行结果以 JSON 保存。全幅 5312×4592 uint16 单帧约 48.8 MB，因此 MCP 返回缩略图及受认证下载引用，避免把全幅数组塞进语言模型上下文。

### 4.4 网络与操作记录

局域网端口启用 Bearer 令牌认证、明确的 Host / Origin 校验和受限文件接口。操作日志使用请求 ID、输入 hash、执行阶段和结果区分成功、失败与执行状态不确定；相同 ID / 参数的重发读取既有结果，不重复投屏或采图。

## 5. 风险与验证方式

- **屏幕映射变化**：启动前枚举并重新绑定角色；不依赖旧 SDK index。
- **枚举破坏投屏**：列表 / 状态工具仅查询缓存；重新探测仅在设备 owner 关闭后执行。
- **窗口被覆盖**：检查同进程窗口、矩形、最小化和遮挡，光学效果再由 CCD 核验。
- **旧帧残留**：等待稳定和额外曝光间隔，并丢弃新完成帧；保存身份记录，不声称精确硬件同步。
- **厂家软件占用相机**：报告设备忙；联调时由用户处理占用软件，不自动关闭其进程。
- **原生 DLL 异常或断连**：停止相关命令、保留已得数据和执行阶段；人工检查后显式重启，避免重复执行状态不明的动作。
- **缺少完整 LUT / 光路标定**：显示码和名义载频与真实相位 / 一级位置分别描述。

计划验证顺序为纯数组和假设备测试、真实 MCP 客户端协议测试、当前 SLM2 与 CCD 的小范围联调、另一台电脑局域网端到端验收；SLM1 待接入后单独验收。

## 6. 本轮完成项与下一步

已建立核心文档及 [书面设计](docs/superpowers/specs/2026-10-13-slm-ccd-mcp-design.md)。设计阶段文档校验退出码 0：5 份 Markdown、5 个本地链接、0 缺失链接、0 占位项，当前偏移一致，放置算式独立复算通过；并完成范围 / 一致性 / 歧义自审。设计已获用户同意，下一步审阅实施计划和选择执行方式。本轮仅开展文件 / 接口调查和规划，没有运行设备 SDK 或改变实验参数。

## 7. 设计批准后的实施计划

用户已批准书面设计，现形成 [实施计划](docs/superpowers/plans/2026-10-13-slm-ccd-mcp-implementation.md)，包含 8 个任务：配置与环境、图像 / 光栅、资产 / 采集存储、HDSLM owner、ToupCam RAW、协调与模拟设备、MCP / 认证下载、CLI / 客户端与验收。

本机只读环境检查确认 Python 3.12.3 x64；未安装产品依赖。官方 PyPI 元数据确认 MCP 2.3.0，当前官方文档使用 MCPServer；计划明确采用 2.3.0，并在安装阶段保存实际依赖解析版本。

计划锁定跨模块模型、函数签名、测试断言与验收边界，并覆盖重复请求、执行状态不确定、相同SN映射、非法文件 / 大图头、partial RAW等容易影响实验的条件。推荐本会话直接执行以保持设备协议及状态接口一致；也支持用户选择逐任务子代理实施及审查。当前等待用户审阅计划和选择执行方式，设备联调所需的角色 / 加载图 / 曝光确认留在代码与模拟验收完成之后。

计划阶段文档校验退出0：6份Markdown、8个本地链接、0缺失链接，代码围栏成对，8任务 / 42实施步骤均为未执行状态；Git内容检查通过。以上是计划文档验证，不是业务测试或设备成绩。

## 8. 实施进展

Task1已完成：独立venv、固定MCP2.3.0、强类型配置和公共模型。实际观察红灯（包不存在）后实现，13项测试通过；禁止bool当曝光整数、拒绝NaN / Infinity，当前offset10,61，普通导入没有厂家DLL副作用。后续模块仍在实现。

Task2已完成：灰度/明确RGB10读取、原生panel拼板、码域与LUT相位光栅、独立振幅光栅及RAW固定范围预览。全套24测试通过。LUT用排序后的相位邻点搜索，避免整图×1024分配；原始图不因预览和光栅计算改变。

Task3已完成：限额与hash验证的分块上传、allowlist最终路径、不可变资产、分帧RAW/固定预览/partial manifest及SQLite请求日志。32通过/1权限跳过；这不证明真实硬件已操作。

Task4已完成：HDSLM专用线程、一生期一次SDK枚举、同SN矩形角色绑定、Win32窗口遮挡/拓扑检查，API提交不自动重试。41通过/1权限跳过，验证使用fake SDK。

Task5已完成：ToupCam持续YYYY RAW流、范围检查和设置读回、三帧容量队列、新帧丢弃/时间记录、ROI及异常释放恢复。50通过/1权限跳过。调查确认本机monotonic_ns读数约16ms粒度，不声称亚毫秒硬件同步；时序单测用独立指定帧时间。

Task6已完成：统一操作锁、state_version、SQLite请求去重、不可重放的uncertain状态、联合预检/顺序/逐帧保存、OS单实例锁和模拟设备。59通过/1权限跳过；模拟相机提供确定非对称测试图，明确simulation，不作为光学模型或实验数据。

Task7已完成：18个MCP工具、3类资源、Bearer与Host/Origin双重校验、认证流式下载及PNG内容块。66通过/1权限跳过，官方Client验证完整模拟调用链和legacy握手，网络取消后恢复请求不会重复采图。

Task8软件部分完成：CLI/启动/防火墙脚本、Codex与Claude Desktop模板、私有本机绑定与令牌、运行及验收文档。71通过/1权限跳过，compileall和pip check通过；独立TCP回环smoke验证18工具、(470,161)与RAW下载SHA一致。临时服务已结束；并未以回环成功代替另一台电脑验收。

今日只读SDK探测已确认HDSLM80RPS/UPL0080在桌面(3072,0)，CCD IUA24500KMA单色；没有打开设备。WLAN为10.195.186.75，本机硬件配置已按唯一已接相位屏绑定，SLM1禁用。ToupView/MagicHolo仍存在，已请求用户指定现场图/曝光和GUI释放方式；现场联调尚未完成。完整实现正进入独立代码审查。

## 9. 独立审查后的最终实现

第8节按时间记录历史状态；本节是审查修复及现场暗帧后的最新结论。独立审查在c93d311..6319b79范围发现6项Important和2项原Minor，按实际工作流影响将默认SLM1位深及巨大有限phi0静默错误升为Important。8项均进入一次修复轮，12条回归先观察失败再通过，全套83通过/2个Windows文件symlink权限跳过，目录junction测试实跑通过。详情见[审查归档](docs/archive/2026-10-13-native/review.md)。

### 9.1 存储边界

AssetStore/CaptureStore在初始化时固定canonical根路径。所有下载记录目录、manifest/asset metadata和最终文件都先resolve，再检查是否仍在固定root内，之后才能读取内容。这样记录目录本身被junction替换时不能把外部manifest先读取后当合法记录返回；上传及published资产同样校验。公开API只接受canonical UUID及登记file_id，不能以路径遍历枚举任意文件。该检查拒绝静态symlink/junction越界，不宣称对本机拥有文件系统写权限的并发恶意替换提供OS级目录句柄隔离。

### 9.2 SLM owner与完整拓扑

HDSLM owner启动时一次枚举SDK，同时固定完整Win32显示拓扑：每块active monitor的物理像素矩形、Windows显示设备名及monitor interface ID。连接前和周期健康检查比较完整快照，新增/删除其他屏或同矩形身份替换也会锁存requires-rebind。停止owner、重新probe和确认角色后再连接，避免复用缓存SDK index。此过程不在已打开窗口时调用SDK枚举。

关闭每个角色独立尝试，只有close成功才删除opened记录；失败汇总到LabError.details.roles，后续角色仍尝试。全量关闭即使出错也结束线程并在finally再次清理，仍失败的窗口保持跟踪并要求重启进程。窗口健康含PID/handle、原生矩形、存活/挂起、最小化及前方遮挡；这些是软件状态，没有液晶面板图像的物理回读。

### 9.3 CCD预检与操作记录

CameraAdapter新增统一readiness方法，要求原生camera已打开、pull流已启动、status为streaming且FreshFrameQueue没有锁存错误。联合命令在曝光修改或投屏前先检查，正式capture入口再次检查以覆盖预检后的断连。回调错误仍唤醒采集并保留partial RAW。

SQLite增加规范化params JSON和steps JSON，兼容旧数据库列迁移；旧数据缺少参数时保留null，不伪造历史。每个阶段先写started，成功后写completed，参数包括命令/资产ID/曝光/偏移等，结果关联capture和panel/input hash。数据库connection显式close。请求ID仍按规范化参数hash拒绝不同参数复用，不保存令牌或上传base64。

若硬件已执行而SQLite finish/fail持续失败，MCP仍返回uncertain、operation_id、已提交阶段和journal_failure；内存缓存返回相同结果并拒绝重复硬件动作。进程重启后的原intent/running标为uncertain，同ID不重放。数据库及内存均不能提供已丢失物理帧的恢复，也不能保证磁盘故障时最终结果持久化成功。

### 9.4 位深与相位

省略LoadRequest/slm_show_uniform位深时由当前角色配置决定：SLM1默认8、SLM2默认10；显式的8/10与输入dtype仍严格校验。空间载波频率受±0.5cycle/pixel限制，phi0以弧度输入，先按2π约简，再与空间相位合成和整数量化，避免巨大有限常数溢出int64。附加光栅与位置调整仍从保留的原始图重算，restore snapshot不会随后续调整被覆盖。

## 10. 实际CCD暗帧与LAN监听证据

用户允许关闭ToupView与MagicHolo，并说明未开激光。两个已核验路径/PID均通过CloseMainWindow正常退出，没有强制结束其他进程。首次probe仅一块SLM；关闭GUI后的新probe出现两个相同HDSLM80RPS/UPL0080、1920×1200接口，桌面(3072,0)与(4992,0)，与Win32快照一致。物理SLM2对应正在确认；未把旧SN/index当作两屏身份，也未向SLM提交。

正式hardware网关已仅绑定WLAN10.195.186.75:8765。测试客户端通过标准Streamable HTTP MCP及私有Bearer令牌连接同机LAN地址；只连接ccd，读取原AE1、曝光2000µs、增益100。以同一曝光2000µs固定AE0，实际范围读回30..15000000µs，增益100..5000。CCD原生型号IUA24500KMA、RAW FourCC YYYY、有效位深12、5312×4592。

默认settle0.3秒、额外曝光间隔、丢弃3张新完成帧之后保存一张全幅uint16 NPY：capture_id=5a26259e-d2c4-4d76-b9aa-cf60021901ee，hostcounter5/SDKseq8。SDK只提供seq/timestamp标志，未伪造EXPOTIME字段；曝光设置保存在metadata.settings。主机有16ms时钟粒度，时序明确为保守软件同步，不声称精确曝光起点。写盘期间有5张队列丢帧，manifest如实记录，保存计数1。

RAW认证流式下载SHA256与manifest一致；预览固定0..4095映射至1024×885，min1/max1007/mean16.065/near_full_fraction0。画面接近黑色，验证SDK/数据流而非一级衍射/标定位深响应。证据在runtime/hardware-dark-verification.json及runtime/captures/5a26259e-d2c4-4d76-b9aa-cf60021901ee/。RAW和原始运行证据按项目规则不提交Git。

finally断开CCD时Stop、RAW/BITDEPTH/RGB选项、曝光/增益/原AE、Close全部成功，实际设置与原快照读回一致；SDK设备已释放，MCP网关继续监听。没有修改Windows防火墙/网络profile。当前ZJUWLAN为Public，现有Private脚本不直接覆盖此网络；另一台电脑的路由、防火墙/校园隔离、Codex/Claude真实调用仍需远端验收。

收尾时物理SLM2对应仍待回复，因此本机配置暂将两个SLM均disabled，保留候选信息以便明确绑定后启用。网关正常重启加载最终源码；客户端可独立lab_connect(['ccd'])使用CCD，不能在确认前通过默认连接误投SLM。SLM代码与模拟验收已完成，现场SLM投屏、光栅响应及跨电脑连通仍未完成，不把任务8现场步骤标为通过。

## 11. GitHub初次发布

2026-10-14用户建立并指定 [haamill/slm-ccd-mcp](https://github.com/haamill/slm-ccd-mcp) 为项目仓库，授权将现有实现上传。发布范围为源码、测试、依赖版本、示例配置、核心文档、设计/计划与审查归档，并保留开发提交历史。

本机私有配置/令牌、实验图像与RAW/PNG/操作数据库、venv及厂家DLL/SDK不进入仓库。发布前同时检查当前跟踪文件和完整Git对象历史，避免仅凭gitignore遗漏曾提交文件。新空仓库以main承载完整项目；本机开发分支保留。硬件SLM角色和跨电脑验收的待确认状态继续在README中明确记录。

HTTPS推送认证失败后，标准SSH握手已确认本机现有密钥认证为haamill；origin改用git@github.com:haamill/slm-ccd-mcp.git，继续向同一用户指定仓库发布，不读取或复制密钥内容。

初次SSH上传已成功建立main（701763d），远端HEAD/main与本地完整提交SHA一致。仓库包含全部软件实现及历史；本机main跟踪origin/main，开发分支feat/slm-ccd-mcp仍保留。发布前新全套测试83通过/2个权限跳过，10份Markdown/11个本地链接核验通过；完整历史208对象/129blob未发现本项目私有token或排除目录/厂家二进制。成功记录随文档提交同步发布。

## 12. 用户文档第1组双SLM加载

2026-10-14用户已接两SLM与CCD，要求根据D:/lab/zty/2的README/FIRST_SIX先加载一组，并自行用CCD定位。选取文档第1行WORKING_STRAIGHT + DECODE_Qp0作为单亮点定位控制；没有执行六帧扫描、切下一decoder、加入字母MAIN或自动CCD采集。文档为实验参数依据，其中原作者其他授权边界不替代本聊天用户的本次设备操作指令。

本地展平目录缺少SLM1_WORKING_STRAIGHT_FULL1920x1200_GRAY8.bmp；从C:/Syncthing/Python/Ecc2/runs/throughput_matching_20261014/load/slm1只读取得。展平README、DECODE_Qp0与旧U源均与该原包同名文件SHA一致，故使用同源原图，不猜测生成新直光栅。SLM1 BMP文件SHA c4f06f1f81ea65319c84a05c2184eb34dcd896c581d2a404666e906b612cd635；SLM2 BMP文件SHA 88d631999f7c8356b5ec05bae08760d88429e8be0cce8230fda7770e7dc28862。

当前三个显示接口与昨日完整Win32身份一致，SLM1按历史记录匹配桌面3072,0（monitor UID261）、SLM2匹配4992,0（UID277）；今日SDK分别index1/2、同SN UPL0080、同尺寸1920×1200。MagicHolo按既有用户许可正常关闭，MCP为唯一投屏owner；不按旧厂家标签号替代今日SDK索引。

先离线解码及compose_panel预检，再通过真实LAN MCP分块上传原BMP、asset完整SHA验证和格式检查，连接两SLM，顺序SLM2→SLM1加载。SLM1码uint8/0..242，SLM2明确厂家RGB10位布局解码为uint16/0..1023；均完整panel1200×1920，offset(0,0)，不添加虚拟透镜/额外光栅，也不重复加通用小图偏移10,61。panel输入/显示数组hash与原图相等：SLM1 eb4875addefc6161a7d519ffd5933ec270ec6305f40ee7c87d8bdcf87d20273a，SLM2 0f1b9a4aa0f16c6a2440dfd849acec27a758d809f50f96a0baadc83005f4194a。

两次SLM SDK提交成功，最终窗口alive、unobscured且not hung。当前一组注册为明确restore snapshot并保持显示，持续owner消息泵。MCP CCD为disconnected，曝光/增益/ROI未改，由用户手动找文档的定位亮点。SDK/数组/窗口证据不证明真实光学点已出现；需要用户定位反馈。现场原证据、输入NPY快照和操作ID保留runtime/document_pair_20261014，按忽略规则不上传Git。

### 12.1 用户指出角色可能反向后的对调

用户反馈“你可能弄反了”。第一轮使用历史位置而未得到当天实体对应确认，历史记录不足以证明当前振幅/相位设备身份。相同SN和稳定Win32接口只能区分输出口，接线或实体模式不能从这些字段判断；第一轮软件成功不支持确定角色的结论。

按该反馈做可逆对调试载，先保留第一轮证据及其本机配置快照，再停止owner、重新probe、将SLM1振幅试绑到(4992,0)/当前SDK index2，将SLM2相位试绑到(3072,0)/index1。原服务退出时有两条编码不可读的SDK提示，旧restore过程未获可靠读回，不记为通过；旧进程结束后新probe/owner和两屏提交成功。新运行原图、GRAY8/RGB10、full-panel/offset0及数组hash完全不变，CCD仍由用户操作。两窗口健康检查通过，当前保持的是对调版本。

第二轮证据独立保存runtime/document_pair_swapped_20261014，引用第一轮结果而不覆盖；角色仍标注试绑，等待用户观察确认，不声明已经修正光学成像或证明实体角色。当前只换对应输出，不叠加光栅、不改变曝光，也不自动执行后续六帧。

## 13. 2026-10-18服务状态只读复核

WLAN仍10.195.186.75，原服务PID20384在8765监听；以项目私有令牌在内部认证，官方MCP Client握手、列18工具和lab_status调用正常，未认证请求返回401。两SLM缓存状态error/requires_rebind，仍须关闭owner后重新probe/明确绑定，不能沿用历史SDK index继续投屏。CCD当前为streaming，本次没有采新帧或调整设置，不据此宣称新采图验证完成；也没有重启服务影响正在进行的相机流。

证据runtime/connectivity_20261018.json与10月16日报告独立保留；仅证明本机LAN地址上的协议/认证和缓存设备状态，未替代另一台电脑的路由/防火墙实测。本轮无设备修改。

## 14. 2026-10-18重新探测绑定及CCD设置恢复

用户要求恢复两路SLM且先保留CCD。诊断确认当前两个输出口UID261/277及矩形均齐全，旧owner锁存了此前的拓扑变化；只关闭指定SLM窗口不会结束owner线程，全量disconnect才会结束owner，同时释放CCD。用户随后明确授权CCD短暂重连并恢复同一个MCP服务，因此通过现有控制接口完成维护，没有修改程序、清除安全检查或终止网关进程。

先记录当前CCD真实读回和缓存流身份，并只读重建SQLite成功SLM操作序列。日志显示其他客户端已有后续实验加载，故不能套用10月14日首组。离线逐步还原最近图像/位置/载波，预检数组hash与最后成功提交一致后，带expected_version调用全量lab_disconnect，优先lab_connect(['ccd'])及恢复8000µs、gain100、AE0。HDSLM重新探测仅在两屏窗口都释放后进行，不枚举相机；匹配同SN+矩形+尺寸，SLM1(4992,0)/index2，SLM2(3072,0)/index1。随后主服务新SLM owner初始化，requires-rebind锁存解除。

恢复SLM1 asset44a6bbfd…的8bit居中图，offset0,0，最终SHA26ca5916cf02d5c2f0df34ef001f2e5fd77a9e8596e83a66700803d46a5b5dc4。恢复SLM2 assete493f655…显式8bit相位图、offset10,61，以及原有fx=-0.5/fy0/code模式载波，最终SHAb0a78e822e02ff1d0b02b211de47ab9f6367d5b67f7d51c4f581a4c918b026fb。该载波来自之前成功实验命令，本次没有新选择载频。最终两SLM均connected，窗口存活/无遮挡/不挂起；数组与最后实验状态相同，不据此声称光学效果验证。

CCD新流恢复streaming，同一camera_id、5312×4592、12有效位；实时读回AE0/8000µs/gain100及其他比较字段与维护前一致。确有授权的短暂断流，不将其描述为连续无中断；本次没有额外采图。完整本机证据runtime/slm_rebind_20261018/recovery.json保存前后设置、operation_id、探测和hash，不提交运行数据。服务端点仍为http://10.195.186.75:8765/mcp，设备恢复不代表另一台电脑的网络已验收。

## 15. 2026-10-18再次健康检查、按当前实验状态恢复及新帧验证

用户再次要求检查MCP并恢复异常。认证、握手及18工具列表正常，但两SLM旧owner再次锁存requires_rebind；当前显示接口及桌面矩形齐全。故障检查报告独立保存为runtime/health_check_20261018_49253927/health.json。本轮CCD正在streaming，实时曝光已由后续实验改为16000µs、gain100、AE0，不能使用上一轮8000µs快照恢复。

实时图案也已由后续联合实验替代：SLM1为500×500、8bit、居中offset0,0；SLM2为800×800、8bit、居中offset10,61，两路当前附加光栅均0。旧恢复辅助脚本只遍历独立SLM加载/偏移/光栅操作，会遗漏lab_load_and_capture中的loads；在硬件操作前发现这一差异，改用本轮状态中的input_sha256、displayed_array_sha256、位深、位置与光栅，反向匹配SQLite成功独立或联合加载请求及原资产。离线compose_panel结果须与实时display hash完全一致才允许进入恢复流程，不采用旧图或旧fx=-0.5，也不重新设置显式restore基线。

沿用用户已批准的短暂CCD重连方案，所有修改以expected_version串行守卫：全量lab_disconnect释放旧SLM owner，优先重连CCD并恢复本轮实时参数；仅在无本进程投屏窗口时单独探测HDSLM；按矩形、尺寸、SN匹配SLM1 x4992/index2与SLM2 x3072/index1，再由主服务新owner连接并重载原图。未修改生产源码、绕过拓扑保护、终止网关进程或改变网络配置。

最终SLM1显示SHA为7d0e767bd7988566787980a6f17e8f3339be92f907d91173a1f70b732f50bfe2，SLM2为066d90f1446975c2751627f764672a6ed03277b53ea2d06e402e9ade02923a51，与本轮维护前相同。两窗口connected、存活、无遮挡、不挂起且无requires_rebind；CCD身份、5312×4592、12有效位及曝光/增益/AE读回均与本轮快照相同。完整操作、资产匹配、probe及设置证据保留在runtime/health_check_20261018_49253927/recovery，不覆盖之前维护记录。

再用标准MCP Client独立执行最终健康检查：无令牌返回401，认证握手及18工具正常；两SLM周期窗口健康时间有效。从现有CCD RAW流实采一张64×64软件ROI新帧，capture_id=ab672ed5-9ab4-4f3b-84b2-763cdfe4de53，前后曝光16000µs、增益100、AE0保持一致，最终CCD streaming，检查脚本退出0且healthy=true。报告位于runtime/health_check_20261018_4837df2c/health.json。该软件ROI不改变CCD原始全幅配置；本轮验证控制/显示窗口/新帧链路，不等同于光学成像效果或另一台电脑网络已验收。

## 16. 2026-10-19再次恢复

用户要求再次恢复MCP。初检发现同一网关PID20384、端点及18工具正常，两SLM均因历史显示拓扑变化锁存error/requires_rebind；当前三个Win32显示接口、身份及矩形齐全。CCD实际streaming、64000µs/gain100/AE0。两张图案尺寸、偏移及位深虽与上次相同，内容hash已被后续实验更新，因此重新保存state_version482快照，并从lab_load_and_capture加载记录匹配SLM1 asset197c4029…与SLM2 assetf3ae9565…，离线还原display hash逐一相同才执行设备维护。初检及快照证据独立保存，不覆盖10月18日记录。

沿用已有授权，以原MCP工具全量断开设备、优先恢复CCD本轮实时设置、在无SLM窗口时重新probe，再启动新SLM owner并加载本轮原图。维护脚本额外在修改前比较实时state_version及两路last元数据与重建快照，避免其他客户端在规划后改图而被旧计划覆盖；后续每步仍使用expected_version。网关进程与网络设置未改，CCD经历已许可的短暂重连；业务源码未改。

恢复SLM1(4992,0)/index2与SLM2(3072,0)/index1均connected且窗口健康，display SHA分别为6f6ef85a98119206b8549401ec335283e3e9c87f37189f3a505361da9471bd9d与1cbdffee27ec77deb01930ff7a30418eefa98768301c3ad90a4de7653560a679，与本轮维护前相同。两图分别500×500和800×800/8bit，offset0,0及10,61、附加光栅0。CCD身份、全幅尺寸、有效位深和实时曝光64000µs/增益100/AE0均保持。

最终独立检查healthy=true：无令牌401、认证18工具、两SLM窗口健康且无requires_rebind，CCD streaming并实际取得一张64×64软件ROI新帧，capture_id=a944bfba-f251-4b05-8291-d3791e133583，采图前后设置相同。完整恢复证据runtime/maintenance_20261019_769b242a/recovery/recovery.json，最终报告runtime/health_check_20261019_7f82068c/health.json。恢复验证控制与新帧链路；尚无证据确定引起历史拓扑变化的外部事件，不宣称已消除所有复发原因，也不将本机MCP成功等同于跨电脑或光学成像验收。

## 17. 2026-10-20重新绑定

用户要求重新绑定。实时state_version501：SLM1 connected，SLM2保留“Projection window closed, moved or hung”错误，当前窗口健康且无requires_rebind字段。源码显示周期窗口检查失败会锁存error，后续健康检查成功只更新window，不自动解除error；本次不能直接归因为此前拓扑变化。三个显示接口及矩形齐全，触发历史窗口异常的外部事件尚未确定。

离线匹配本轮实时原图：SLM1 asset197c4029…/500×500/8bit/居中offset0,0，SLM2已更新为asset9c11eaa7…/800×800/8bit/居中offset10,61，两路附加光栅0。以expected_version及维护前图案元数据守卫，按既有授权全量释放设备owner，优先恢复CCD本轮实际8000µs/gain100/AE0，在无投屏窗口时probe，然后重新绑定SLM1 x4992/index2、SLM2 x3072/index1并重载原图。网关PID20384与端点未变，CCD有已许可的短暂重连；没有修改业务源码或绕过安全检查。

两屏最终connected且窗口健康，display SHA分别6f6ef85a98119206b8549401ec335283e3e9c87f37189f3a505361da9471bd9d与2ba0c359a311cbb763520a937fec70955d5b8c09d2e982105a3d5de09fae6f0c，与维护前相同；CCD原身份、尺寸、位深及实时设置保持，streaming。独立最终检查healthy=true、认证/18工具通过，64×64软件ROI新帧capture_id=5d252a9c-a599-466d-86bd-2d6b5dfd0807，采图前后设置相同。恢复证据runtime/maintenance_20261020_009aacd4/recovery/recovery.json，最终检查runtime/health_check_20261020_b0b1fe40/health.json；软件与新帧链路通过不等同于跨电脑网络或光学成像验收。
