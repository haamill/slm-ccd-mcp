# SLM / CCD MCP 项目指令

## 目标与用户确认

- 2026-10-18当前状态：用户授权重新探测绑定SLM，并随后明确允许CCD短暂重连、恢复同一个MCP服务。已通过全量设备disconnect、先恢复CCD、SLM新probe/connect恢复两屏；HTTP网关/PID/端点不变。SLM1(4992,0)/index2、SLM2(3072,0)/index1均connected且窗口健康。CCD streaming、8000µs、gain100、AE0，读回与维护前一致。
- 当前图案按SQLite最后成功操作重建并核hash，不是10月14日初始包：SLM1 asset44a6bbfd…/8bit/centered offset0,0，SLM2 assete493f655…/8bit/centered offset10,61及此前既有fx=-0.5。下方10月14日首组/未加光栅说明为历史阶段，不可当当前屏。证据runtime/slm_rebind_20261018/recovery.json。
- 项目位于 `D:/ExpSoftware/slm-ccd-mcp`，在连接实验设备的 Windows 电脑上运行。
- 另一台局域网电脑通过 Codex / Claude 等本地 MCP 客户端操作实验。
- 首版覆盖 SLM 图片加载、加载位置、光栅，以及 CCD 曝光、增益、采图与单步联合操作。
- 用户于 2026-10-13 同意首版范围，并明确当前 **SLM2 相对居中偏移为 (+10,+61) 像素**。旧记录 (+10,+69) 仅用于历史追溯。
- 用户最初说明振幅型 SLM1 未插入；后续当前 probe 出现两个同 SN SLM，实际角色须按当日确认绑定。不能把某角色缺席作为其他设备服务的整体启动失败。
- 2026-10-13暗帧阶段，用户允许关闭ToupView/MagicHolo，两者正常关闭，激光未开启；该历史暗帧不作光学效果验证。2026-10-14首组加载仅关闭MagicHolo，ToupView保持运行由用户操作。
- 2026-10-14用户要求按D:/lab/zty/2文档加载一组并由其手动用CCD找像。当前保留FIRST_SIX第1组：SLM1 WORKING_STRAIGHT GRAY8、SLM2 DECODE_Qp0 RGB10，完整1920×1200、placement=panel/offset0，不加软件透镜或光栅。MCP只连接两SLM，CCD保持disconnected；不继续文档的六帧扫描或更换下一组，等用户反馈。
- 第一轮按历史位置SLM1(3072,0)/SLM2(4992,0)加载，用户反馈可能反向；当前已对调试绑SLM1振幅(4992,0)、SLM2相位(3072,0)，同组/同码/满屏offset0，等用户观察确认实体对应。两者同型号/SN，Win32接口和矩形只能标识输出口，不能证明器件振幅/相位角色；不得把旧记录或本次试绑写成用户已确认。两窗口均alive/unobscured、不挂起，服务必须持续消息泵以保留显示。

## 开发流程

- 开发前检查本文件、README.md、LOG.md、REPORT.md 及最新设计 / 计划。
- 新项目先使用 Superpowers 头脑风暴梳理目标、约束、方案和风险，再进入搭建 / 实现。
- 用户已批准书面设计和实施计划，并于2026-10-13要求“开始”；按推荐的本会话直接实现方式执行，最后进行独立代码审查。
- 按对应阶段完成设计、计划和用户审阅；用户后续明确指令优先，不自行增加审批要求。
- 不使用其他项目的既有环境路径作为本机已验证路径；解释器、依赖及 DLL 位数需实际核验。
- 代码编辑优先使用 apply_patch；验证使用有意义的模拟设备测试、协议测试及分阶段设备联调。

## 核心文档与记录

- 持续维护 AGENTS.md、README.md、LOG.md、REPORT.md。
- README.md 包含定位、安装 / 运行、目录结构、当前状态、进展和重要说明；未实现命令不可写成可运行。
- 每次运行前检查 LOG.md，并先记录本次范围和预期；运行后补充结果、失败和下一步。
- REPORT.md 详细说明实现的功能、原理、技术路线、验证证据及尚未验证范围。
- 新文件出现替代版本时，删除确认无参考价值的临时工作；有参考意义的版本归档并保留来源和发展脉络。
- 不删除 / 改写历史实验数据、SDK 文件和其他项目资料。

## 设备与图像约束

- HDSLM 枚举只能在尚未打开本进程投屏窗口的设备启动阶段执行；状态查询读取缓存，不重新枚举。
- 所有 HDSLM 调用和窗口消息泵由同一专用线程拥有；应用在 Windows 交互式桌面会话运行。
- 两块历史设备的名称 / SN 相同，不能只按序列号或旧 SDK index 绑定；使用角色、桌面区域、尺寸及枚举信息联合核验。
- 完整 Win32 拓扑包含 monitor interface ID。变化后锁存 requires-rebind，关闭 owner 后重新探测和确认；不能在旧 SDK index 上继续提交。
- SLM1 默认 uint8 / 0..255；SLM2 默认 uint16 容器 / 0..1023。显式的 8bit 相位输入保留原码，不隐式拉伸到 10bit。
- 图片不自动缩放、插值、镜像、裁剪或逐图归一化；RGB10 打包文件必须显式声明后解码。
- 相对居中偏移、整张面板图的位置、图像内的光栅相位是不同参数，不能重复叠加。
- 相位载波的码域叠加只能声明为码域处理；有 LUT 时须在相位域合成后重新查表，不能把非线性 LUT 码直接相加当正确相位。
- 振幅图不能沿用相位取模相加；首版只生成独立振幅光栅和加载已生成振幅图。
- 不写入硬件 Gamma / LUT、触发寄存器；不调用旧代码已发现返回值异常的 SoftGamma setter/getter。
- SDK 调用成功、窗口存活和数组 hash 不等于液晶面板物理读回或光学效果达标。

## CCD、并发与网络约束

- 曝光使用微秒，增益使用 SDK analog gain percent；查询设备范围后校验并读回。
- RAW 保存保留有效位深、SDK 行顺序、帧身份、曝光设置和时间信息；预览映射单独记录。
- 图案更新 / 曝光更新后，使用等待和新帧丢弃策略，不返回残留旧帧当新状态的采图。
- 控制命令串行；联合加载采图不可被其他调参命令插入。客户端断开不触发重新执行硬件命令。
- 服务仅暴露受限的设备工具及文件接口，不提供任意 shell、Python 执行或任意文件读写。
- 读取上传资产或 capture manifest 前验证其最终路径处于启动时固定根目录；不能仅与可被 junction 替换的记录目录比较。
- 操作日志保存命令、参数及步骤；持久化故障仍返回 operation_id 和 uncertain，原 intent 及内存结果用于禁止重放。
- 局域网服务启用令牌认证、Host / Origin 校验；凭据、运行数据及本机配置不提交 Git。

## 资料入口

- GitHub：`https://github.com/haamill/slm-ccd-mcp`，用户于2026-10-14授权初次上传现有项目。
- 设计：`docs/superpowers/specs/2026-10-13-slm-ccd-mcp-design.md`。
- 计划：`docs/superpowers/plans/2026-10-13-slm-ccd-mcp-implementation.md`。
- 历史实验：`C:/Syncthing/Python/EccentricityHolography`，仅作为来源。
- SDK：`D:/ExpSoftware/HDSLM_SDK`、`D:/ExpSoftware/toupcamsdk.20260908`。
