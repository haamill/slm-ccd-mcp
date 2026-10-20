# 操作日志

时间按 Asia/Shanghai 记录。每次运行前检查本文件，记录范围和预期，运行后补充实际结果。历史实验项目和 SDK 目录只作为来源。

## 2026-10-13 — 项目前期调查（补记来源）

### 运行前范围

用户要求在 `D:/ExpSoftware` 建立局域网 SLM / CCD MCP。新项目创建前先按照 Superpowers 头脑风暴检查 SDK 和历史控制链，确认客户端类型及首版范围。

### 结果

- 本机 SDK 目录包含 HDSLM_SDK、HDSLM80RGamma_x64、MagicHolo_10bit、toupcamsdk.20260908。
- 阅读旧项目核心说明、当前光路交接、SLM 单 / 双屏适配器、持续 RAW 相机代码及 SDK 头文件 / Python 包装。
- 历史代码确认枚举会关闭 HDSLM 投屏窗口；应启动时枚举一次，并用独立线程持续处理窗口消息。
- 历史两块 SLM 使用相同名称 / SN，需按角色和桌面区域联合绑定。
- 历史 CCD 型号 IUA24500KMA，全幅 5312×4592，单色 YYYY / 12 有效位；这些不是今日重新枚举的结果。
- 查阅官方 MCP Streamable HTTP 与 Python SDK 文档。
- 用户确认另一台电脑使用 Codex / Claude 等 MCP 客户端。
- 只读进程检查见 ToupView / MagicHolo 进程；进程存在不证明当前设备占用情况，联调时须重新核验。
- 本阶段未调用设备 SDK。

## 2026-10-13 — 会话方案确认与书面设计（运行前）

### 用户确认

用户同意首版方案，并更新当前 SLM2 相对居中偏移为 **(+10,+61)**。

### 检查与范围

- 目标 `D:/ExpSoftware/slm-ccd-mcp` 尚不存在。
- `D:/ExpSoftware` 无上级 Git 仓库；Git 身份已配置，可建立独立本地仓库。
- 根目录未发现适用的本地 AGENTS.md；采用会话中用户提供的全局项目约束。
- 会话方案确认允许形成书面设计；业务代码 / 产品依赖阶段等待书面设计及实施计划审阅。
- 本次建立核心文档和设计文档，使用 (+10,+61) 作为当前默认；旧 (+10,+69) 只保留追溯。
- 预期检查 Markdown 本地链接、偏移一致性、方案内部一致性和 Git 工作区状态。

### 设计整理结果

- 写入 AGENTS.md、README.md、LOG.md、REPORT.md 和书面设计。
- 明确全局串行控制、SLM 专用线程、CCD RAW 新帧策略、认证、文件边界与验收步骤。
- 明确相位码域叠加 / LUT 相位域叠加与振幅光栅的区别，避免错误地把振幅图按相位取模相加。
- 明确 1000×1000 小图的当前左上角为 (470,161)，全幅 panel 不重复套偏移。
- 接下来进行文档自审和本地 Git 保存；验证结论在运行后追加。

### 文档检查结果

- 新鲜校验命令退出码 0：5 份 Markdown、5 个本地链接、0 缺失链接、0 TODO / TBD / FIXME 占位。
- 5 份文档都包含当前 (+10,+61)，所有 (+10,+69) 均明确为旧 / 历史值。
- 独立重算 1000×1000 小图在 1920×1200 panel 上的放置为 (470,161)。
- 自审检查占位、内部一致性、范围和歧义；将相位 / 振幅、码域 / LUT、panel / 小图、缓存状态 / 物理读回分开，确认验收顺序与功能范围一致。
- 添加 .gitignore，排除凭据、本机配置、运行数据、用户输入、Python 生成物及厂家二进制。
- 下一步初始化独立本地 Git 仓库、检查 staged diff 并保存文档，打开书面设计供用户审阅。

### Git 保存前检查

- 独立仓库初始化成功，分支 main；未配置远端或推送。
- 首次 staged diff 检查退出码 0，范围仅 6 个文档 / 忽略规则文件、524 行新增。
- Git 提示本机自动换行设置会在后续检出时转为 CRLF，未报告内容错误。
- 本次提交保存设计和调查记录；提交后核验工作区状态，并在 Codex 编辑面板打开书面设计。

### 保存后结果

- 本地文档提交成功，6 个文件受 Git 跟踪；提交后 `git status --porcelain=v1` 输出为空。
- 书面设计 SHA256：`09261028A66C8587DA3E074E56ED1F63DAB052D9E1E6E0FC9A0204E4727832A5`。
- `open_in_codex` 返回 queued，仅表示已请求打开，不能宣称当前面板已显示。
- 本日志补记纳入最终文档提交。当前等待用户审阅书面设计，然后进入实施计划阶段。

## 2026-10-13 — 设计批准与实施计划

### 准备检查

- 用户同意书面设计，进入 writing-plans 阶段；当前尚未选择执行方式。
- 已只读检查项目指令、日志、设计和 Git；进入本轮前工作区干净，最新文档提交 13c5771。
- 本机 `D:/Program Files/Python312/python.exe` 为 Python 3.12.3 / x64；全局有 numpy、Pillow、httpx、starlette、uvicorn，未发现 mcp / pytest。此为只读环境检查，未安装依赖。
- HDSLM 和 ToupCam 的指定 x64 DLL / Python 包装文件存在。

### 本轮运行前范围

- 仅编写可审阅实施计划，确定文件职责、跨模块接口、测试与硬件联调边界。
- 必要时只读核验官方 SDK 版本 / 文档；不执行设备 SDK，不搭建业务代码或安装产品依赖。
- 保持当前 (+10,+61)，默认小图放置 (470,161)。
- 计划完成后检查规范覆盖、签名一致性、文档链接和 staged diff，再保存本地 Git 并交给用户审阅。

### 计划整理与自审结果

- PyPI 官方元数据返回 MCP 2.3.0 / Python≥3.10；官方当前文档为2.x稳定路线，使用MCPServer和 `from mcp import Client`。计划采用本机已核验3.12 x64及固定2.3.0。
- 已形成8任务实施计划，定义公共类型、跨模块接口、测试断言、运行命令、提交点与现场 / 远端验收范围。
- 自审覆盖设计13节、类型和方法一致性、五项Review Focus、步骤粒度与比例；补充LUT读取接口、存储构造签名、实际show时间字段、restore来源语义和Client正确导入方式。
- 当前计划302行 / 34,340字节，对照设计226行 / 18,737字节；没有逐行写完业务实现。
- 更新核心文档和设计状态：书面设计已批准，实施计划待审阅和执行方式选择。
- 下一步执行文档链接 / 占位 / 任务步骤检查并提交本地Git；本轮未安装依赖或操作硬件。

### 文档验证结果

- 校验命令退出0：6份Markdown、8个本地链接、0缺失链接；代码围栏成对。
- 实施计划含8个任务、42个未执行实施步骤，当前偏移一致；计划中的测试代码只作为实施说明，没有运行这些业务测试。
- `git diff --check` 通过；拟提交范围仅核心文档、设计批准状态和新增实施计划。
- 接下来保存本地Git，并请求在Codex打开计划供用户审阅；用户确认计划和推荐的本会话直接执行方式后开始实现。

### 保存后结果

- 计划文档本地提交成功；提交后Git工作区为空，范围为6个文档文件。
- 打开计划请求返回 queued，未据此宣称当前面板已显示；用户可直接通过计划文件链接审阅。
- 本日志补记随最终文档提交保存。当前等待计划审阅及执行方式选择；已批准的设计和 (+10,+61) 保持有效。

## 2026-10-13 — 实施启动（运行前）

- 用户要求开始，实施计划与推荐Native方式生效；顺序完成8任务，不在任务之间重复请求确认。
- 检查Git：当前main、干净工作区、普通独立仓库，无已附加worktree；本项目仍仅文档。
- 使用executing-plans、test-driven-development及using-git-worktrees流程；在用户指定项目目录的专用开发分支实现并维持可恢复进度记录。
- Ruling: 新项目无其他开发内容，用户已指定最终项目目录；使用原目录的独立开发分支，不额外创建worktree，避免交付散落 — 若以后并行开发再增加工作树。
- 本轮先创建计划workspace / ledger，运行Task1红灯，建立venv并安装锁定依赖；不调用设备SDK。

### Task1结果 / Task2运行前

- 初次pytest因lab_mcp不存在失败，符合计划红灯；venv依赖安装成功，未使用全局环境写入。
- 实现强类型配置与公共模型，editable安装成功；全套13测试通过，依赖版本锁定。
- 当前状态为实现中；接下来验证图片位深、RGB10、精确拼板、光栅 / LUT和预览，仍不调用SDK。

### Task2结果 / Task3运行前

- 观察imaging模块缺失红灯后实现；全套24测试通过，包含精确(470,161)拼板、native10/RGB10、LUT圆周最近码、伪造大文件头及固定预览映射。
- Task3准备测试上传边界、最终路径、重复请求、重启不确定状态、partial保存和磁盘空间预检。

### Task3结果 / Task4运行前

- 存储模块缺失红灯后实现资产上传、逐帧NPY/预览/manifest和SQLite intent/去重；全套32通过、1因Windows symlink权限跳过。
- Task4使用严格SDK fake验证同线程、一次枚举、角色绑定、窗口失效及无重试；实际厂商DLL仍未调用。

### Task4结果 / Task5运行前

- 全套41通过/1权限跳过；SLM fake验证所有API/消息泵同线程，缓存查询不重枚举，窗口失效和拓扑变化停止提交。
- Task5将用ToupCam fake和真实时间队列验证手动曝光/AE读回、新帧阈值/丢帧、断连和恢复关闭。

- Task5第一次全量验证：49通过/1权限跳过/1时序用例失败。systematic-debugging实测本机monotonic_ns约16ms粒度，2ms测试生产时间未越过阈值；改为独立可控帧时间戳，未放松生产阈值。

### Task5结果 / Task6运行前

- 修正测试时间来源后，全套50通过/1权限跳过；RAW流、曝光读回、新帧阈值、断连唤醒、ROI及逐项恢复关闭已实现。
- Task6准备接通模拟设备、操作串行锁、版本控制、原图重新合成、联合事务和请求去重。

- Task6初验57通过/1跳过/2失败：恢复登记标记随重算沿用导致baseline覆盖，error浅拷贝与partial manifest形成循环引用。已按失败测试定位，消耗登记标记并深拷贝独立错误记录，不修改预期行为。

### Task6结果 / Task7运行前

- 全套59通过/1权限跳过，联合预检、顺序、ID去重、版本、恢复基图、partial失败和响应性通过。
- Task7已只读核验安装的MCP2.3.0真实接口；将构建认证ASGI和真实SDK client调用链，不用自造协议。

- Task7首次集成测试发现bare dict注解不生成structuredContent；通过安装SDK源码和in-process Client定位，改用明确dict[str,Any]输出schema。pytest async fixture跨任务退出AnyIO cancel scope，改由单一后台任务持有完整lifespan；生产ASGI生命周期不改。

### Task7结果 / Task8运行前

- 全套66通过/1权限跳过：真实MCP Client完成上传/投屏参数/曝光/采图/inline PNG/认证RAW下载hash核对，legacy握手通过。
- 客户端取消后操作在线程内完成；重复operation_id不重新采图。未认证和错误Host/Origin被拒绝。
- Task8准备CLI、启动与客户端模板、真实回环网络smoke及设备只读探测。投屏/曝光现场联调保留用户指定图像与曝光步骤。

### Task8初验 / 设备探测与网络运行前

- CLI和模拟smoke实现后，全套71通过/1权限跳过。将运行compileall、pip check和今日SDK只读枚举。
- 本机WLAN IPv4读回10.195.186.75，另有Meta虚拟网卡；客户端模板使用WLAN地址，跨日需重新核验。
- Codex官方文档与本机CLI确认URL/Bearer环境变量；Claude Desktop模板使用mcp-remote0.14.3及无空格header占位，凭据由客户端环境提供。
- 接下来生成本项目私有token并测试独立TCP模拟服务；真实硬件smoke要求显式图像和曝光，不使用模拟测试图直接试投硬件。

- 今日probe成功：HDSLM80RPS/UPL0080在(3072,0)、1920×1200，另一个显示为普通主屏；CCD IUA24500KMA单色。未打开设备，保存runtime/probe.json。
- compileall、pip check、CLI help通过。已生成私有token，未输出值；本机硬件绑定配置仅登记枚举结果。
- 自动审核拒绝复合后台启动命令（blocked by policy，无具体说明），未执行该命令。改为项目启动脚本在工具会话中运行回环模拟服务，端口8766；没有Start-Process后台进程或真实设备动作。
- 用户现场图、曝光和是否可关闭厂家GUI的澄清已异步提出；继续完成独立网络验证和代码审查。

### 独立TCP验证结果

- 8766回环端口的独立服务进程与真实MCP Client完成smoke：18工具、placement(470,161)、RAW下载hash一致。
- 结果在runtime/simulation-verification/network-smoke.json；capture ID为4a8ead98-79c0-44cc-85de-fd7174e2998f，simulation明确标记。
- 临时模拟服务经工具会话Ctrl+C结束，退出码1，无硬件连接；接下来确认端口释放。
- Task8软件交付已具备；现场投屏/CCD打开及另一台设备连接仍待确认/验收。将先对全部实现做独立代码审查，期间不操作厂家GUI。

- 临时8766监听已释放；本机私有配置和token经git check-ignore确认不受跟踪。正式8765网关尚未启动。
- 实施计划Task1..7及Task8软件步骤1..4标记完成，现场/跨电脑/收尾步骤保持未完成。
- 最新文档本地链接核验通过。已按Native流程派唯一独立审查代理审阅c93d311..6319b79，不让审查代理操作SDK或凭据。

### 审查修复运行前
- 独立审查已完成，6项Important及2项Minor。按实际功能影响将SLM1默认位深和巨大有限相位的静默错误升为Important，8项进入唯一修复轮。
- 先建立路径junction、关闭故障、拓扑/身份变化、持久化失败、CCD readiness、参数追溯和默认位深/相位的回归测试；不触碰真实硬件。
- 用户授权关闭厂家程序，并说明激光未开；现场仅验收控制/暗帧链路，保留当前曝光，采用明确标记的新测试图。

### 审查修复结果 / 现场运行前
- 12个回归失败先复现，修复后12通过/1文件symlink权限跳过；全套83通过/2同类权限跳过，真实junction测试通过。
- Win32完整拓扑和monitor interface ID读回3屏，SLM坐标3072与4992均存在；须重新SDK probe明确当前绑定。
- 用户已允许关闭ToupView和MagicHolo；将仅对已确认PID22892/13304及路径发出正常关闭，5秒未退出才结束这两个进程。

- ToupView与MagicHolo均正常关闭，不需强制结束。首次probe误用了不存在的--output参数，CLI拒绝且未触碰设备；按CLI既有输出路径重试，历史probe另存probe-initial.json。

- 新probe已枚举两个同SN/型号SLM，位置3072和4992；已异步请求物理SLM2对应，仅CCD联调可以继续。正式8765网关将绑定已核验WLAN地址启动，令牌不回显，不自动开放防火墙。

### CCD真实暗帧运行前
- 正式hardware服务在8765启动；本次通过官方MCP Client调用只连接CCD，读回当前曝光并以同值手动设置，采1张全幅RAW、3张丢弃、0.3s稳定，流式下载核SHA，finally断开并恢复原设置。激光关闭，未向任何SLM投屏。

### CCD真实暗帧结果
- 正式LAN IP上的官方MCP Client采图成功，capture_id=5a26259e-d2c4-4d76-b9aa-cf60021901ee；5312×4592、YYYY RAW12有效位，曝光2000µs、增益100。
- 测试期同值手动曝光、AE0；断开恢复原AE1、曝光2000、增益100和原RAW/BITDEPTH/RGB选项，无错误。
- 丢弃3新帧后保存hostcounter5 / SDKseq8；SHA下载一致，预览1024×885，min1/max1007/mean16.065，激光关闭。
- 当前8765仅绑定10.195.186.75，服务PID7712；防火墙未改，跨电脑未知。Win32/SDK均列两SLM，投屏仍待用户物理角色确认。

### 最终运行前检查
- 最终源码再次全套83通过/2文件symlink权限跳过，已实拍CCD、已恢复释放；SLM物理对应仍无回复，不能继续依赖旧3072绑定。
- 为使当前网关可直接审阅且避免错误SLM角色，将暂禁用SLM2并保留候选配置，正常重启网关加载最终修复；仍提供CCD远程控制。收到角色确认后再重绑并投屏。

### 当前阶段收尾
- 正式网关已正常重启加载最终源码；暂禁用两个SLM避免角色歧义，CCD可独立连接。标准MCP查询返回hardware、18工具、SLM1/2 unavailable、CCD disconnected。
- 本轮代码审查和暗帧结果已归档；现场SLM身份待回复、跨电脑尚无访问条件，Task8现场步骤不标完成。分支保留feat/slm-ccd-mcp，不合并或推送。

### 交付检查运行前
- 将核验核心Markdown链接、Git diff和凭据排除，并提交唯一审查修复及CCD验收阶段。没有远端仓库操作；本计划现场联调未结束，保留正在使用的ledger工作区，已把重要记录复制到docs/archive。

- 交付文档检查：10份Markdown、11个本地链接、无缺失；私有token未出现在Git文件；config/local.toml、local.token和运行证据被ignore。diff发现ledger末尾多余空行，已修正后再检查。

### 2026-10-14 GitHub初次上传运行前

- 用户指定并授权上传至 https://github.com/haamill/slm-ccd-mcp。
- 本地feat/slm-ccd-mcp工作区干净，最新实现d096120；尚未配置remote，目标git ls-remote没有任何已存在ref。
- 上传前重新运行全套测试、文档链接检查；检查完整Git历史中令牌及排除目录/厂家二进制是否曾受跟踪。计划以完整项目建立远端main，保留开发分支与历史。

### GitHub上传前检查结果
- 新全套83通过/2个Windows文件symlink权限跳过。完整历史198个对象/123个blob，私有token与排除路径均未出现。文档10份/11个本地链接无缺失，私有配置、token、RAW记录和venv被ignore。
- 目标仓库可访问且无refs；准备配置origin并将本地main仅作祖先检查后的快进，再推送完整项目，开发分支保持现有工作目录。

- 首次HTTPS推送被GitHub以Invalid username or token拒绝，远端没有写入。已验证现有SSH认证对应haamill账号（GitHub正常返回已认证、不提供shell）；使用同一仓库的SSH地址继续推送。

### GitHub初次上传结果

- SSH推送成功建立远端main，初次发布提交701763d；远端HEAD为refs/heads/main，git ls-remote核对main与本地主分支完整SHA一致。
- origin已配置为用户指定仓库的SSH地址，本地main跟踪origin/main；当前feat/slm-ccd-mcp保留，工作目录D:/ExpSoftware/slm-ccd-mcp。
- 源码、测试、四份核心文档、设计/计划、依赖及审查归档已上传。最后提交历史检查208个对象/129个blob，无本项目token或排除路径。
- 将本条成功记录提交并快进推送到main后再核对最终远端SHA。SLM物理角色确认和另一台电脑连通仍为现场待验收，上传不改变此前设备验收结论。

### 2026-10-14 文档首组加载运行前

- 用户现已连接两个SLM和CCD，要求按D:/lab/zty/2文档先加载一组，CCD由用户自己定位；本次只操作两SLM，不连接或调参CCD，不执行文档六次采集。
- README/FIRST_SIX指向第1组WORKING_STRAIGHT + DECODE_Qp0，满panel1920×1200、SLM1 GRAY8/SLM2 RGB10、offset0、无额外软件透镜/光栅。本机目录缺少直条纹文件，已在同源Ecc2/runs/throughput_matching_20261014/load/slm1找到；先核对README和已有decoder/source文件SHA一致再采用原图。
- 映射依据为原实验记录SLM1 x3072、SLM2 x4992；须与今日SDK/Win32矩形、尺寸和SN共同匹配，不沿用旧SDK index。厂家MagicHolo当前在运行，按既有允许关闭授权正常关闭；ToupView保持运行供用户定位。
- 资料搜索误把历史outputs JSON纳入全文扫描，输出过大，已停止宽搜索，后续只定点读取相关小文档/文件。一次shell拼写错误未执行Python或SDK，不影响设备。

- 首组预检通过：README及现有decoder/旧U源与同源包逐文件SHA一致；直条纹GRAY8为1200×1920/0..242，decoder正确RGB10解码为1200×1920/0..1023。panel输入hash与原始数组完全一致。
- MagicHolo已正常退出，今日probe与Win32均读回主屏及SLM x3072/x4992、1920×1200、UPL0080；按历史角色联合匹配配置启用两SLM。现在启动独占MCP owner，仅上传、连接两SLM、SLM2→SLM1提交并保留窗口，CCD不由MCP连接。

### 文档首组加载结果

- 标准MCP Client通过正式LAN端点上传原BMP并验证asset，成功连接两SLM；SLM2→SLM1提交均succeeded，窗口均alive/unobscured且未挂起，CCD状态disconnected。
- SLM1(3072,0)原生8bit，数组SHA eb4875addefc6161a7d519ffd5933ec270ec6305f40ee7c87d8bdcf87d20273a；SLM2(4992,0)RGB10/native10，数组SHA 0f1b9a4aa0f16c6a2440dfd849acec27a758d809f50f96a0baadc83005f4194a。提交hash与预检原始码逐个相等，两个placement/offset均(0,0)，无额外载波/透镜。
- source README、decoder及已有旧U源与同一Ecc2原包逐字节相同；缺失直条纹采用该同源包原BMP，没有生成替代图或改写用户资料。
- 输入快照/preflight.json/probe_previous.json/probe_current.json/load_result.json保存在runtime/document_pair_20261014。服务继续运行并保持两屏，不断开SLM，不自动采集或改变CCD，由用户手动找像。此次只验证加载控制链，不声称已观察到光学亮点。

- 运行后确认ToupView PID21152仍在，正式8765监听及两SLM窗口状态已核对。更新核心文档、运行/验收说明；仅文档变化，直接SDK/MCP加载核验作为本轮验证，不为该可逆操作新增或重跑软件测试。
- 继续同步到用户先前授权的同一GitHub仓库；先检查文档链接、凭据排除及diff，再提交记录并快进main推送，保持投屏owner运行。

### 用户反馈可能两SLM角色反向 / 对调前
- 用户反馈可能弄反；上一组仅以历史位置映射，不能单凭相同型号/SN确认今日实体连接。
- 将在保留第一轮证据后正常关闭owner，配置SLM1振幅角色到x4992、SLM2相位角色到x3072，重新probe再加载同一WORKING_STRAIGHT+DECODE_Qp0组；所有图码、位深、满panel/offset0不变，CCD不操作。此为对调验证，实体对应等待用户观察确认。

### 对调加载结果

- 原服务进程经Ctrl+C退出；SDK在退出时输出两条不可读编码的原生提示，无法据此证明旧restore成功，不把退出恢复记为通过。随后新独占probe/owner成功。
- 对调配置SLM1 x4992/index2/8bit、SLM2 x3072/index1/10bit；两次slm_load_image成功，同原图array hash，offset0且无额外载波/透镜；最终窗口alive/unobscured/未挂起，CCD仍disconnected。
- 首次运行证据及其配置快照保留，第二次写runtime/document_pair_swapped_20261014/load_result.json及新配置/probe。当前保持对调屏，物理角色由用户观察确认；已修正文档，不再把历史矩形映射当确定实体身份。

### SLM2纵向光栅运行前
- 用户明确追加SLM2纵向条纹以横向分离一级。该指令优先于实验README的额外光栅关闭，本轮只改SLM2，保留SLM1/CCD/无透镜/满屏offset0。
- 同源生成器确认DECODE_Qp0已内含x周期5px载波及y行补偿；追加fx应计入已有0.2cycle/px，不能把光栅条纹方向误当fy。已异步询问追加周期，默认按文档offaxis320方案fx+0.12、fy0（额外8.333px，名义总3.125px）。先检查原包LUT的方向和语义，避免非线性10bit码直接当线性相位。

- 用户询问“那是不是不用加了”，依据原图已含P5说明当前先不追加；前述fx+0.12只是未执行备选，没有调用slm_set_grating或重新投屏。下一步仅lab_status读回核验原hash/附加fx=fy=0及窗口状态，不操作CCD。

- 上轮只读核对已完成：SLM2原始数组hash仍为0f1b9a4a…05f4194a，附加fx/fy/phi0均0，CCD disconnected；grating_review.json保留。未追加光栅。

### 2026-10-16 当前连接检查运行前

- 用户询问当前服务是否可连接以及连接方式。本轮只查监听、认证、MCP握手/工具列表/lab_status，不连接或更改SLM/CCD。
- 当前WLAN仍10.195.186.75，8765监听PID20384，ZJUWLAN仍Public。检查本机CLI确认--url/--bearer-token-env-var语法，并核验官方Codex MCP配置说明。
- 将从本机私有token文件内部读取令牌，仅向已有实验服务发送认证，输出摘要不显示令牌。远端电脑未直接访问，不能以本机检查宣称跨电脑已连通。

### 2026-10-18 当前服务状态检查运行前
- 用户询问当前MCP是否正常。本轮仅验证8765监听、认证拒绝/成功握手、工具列表和缓存lab_status，不枚举SDK、不重启owner、不投屏、不连接CCD。
- WLAN仍为10.195.186.75，8765由原服务PID20384监听；已有未提交LOG记录保留。新检查另存今日报告，不覆盖10月16日证据。

### 2026-10-18 当前服务状态检查结果

- 只读检查成功：未认证HTTP401，认证MCP握手、18工具列表、lab_status均正常，地址http://10.195.186.75:8765/mcp，mode=hardware。
- 两SLM仍status=error、requires_rebind=true；CCD当前status=streaming（区别于10月16日disconnected）。本轮未采新帧或改CCD设置，不把缓存streaming状态称为新采图验收。
- 今日结果runtime/connectivity_20261018.json，未输出令牌，未做硬件修改/owner重启。另一台电脑路由/防火墙连通尚未直接验证。

### 2026-10-18 SLM重新探测绑定运行前

- 用户明确授权重新探测/绑定两SLM并修复报错，要求CCD保持当前状态。先读MCP缓存状态及当前Win32完整拓扑，保存CCD设置快照；不重启包含相机流的主进程，不调用CCD connect/disconnect/settings/capture。
- 使用systematic-debugging核对根因与恢复接口：requires-rebind为拓扑变化锁存。现有lab_disconnect指定两SLM仅关闭窗口、不结束SLM owner；全量disconnect会关闭CCD，不能用它冒充SLM-only恢复。先确认实际显示接口是否齐全，再选择不影响CCD的最小恢复路径。

- 诊断：两个Win32接口UID261/UID277都存在，物理矩形与原来一致；旧owner锁存requires_rebind。CCD缓存为streaming/8000µs/增益100/AE0。
- 用户明确选择允许短暂重启CCD并恢复同一个MCP服务。采用现有MCP全量lab_disconnect→重新probe/绑定→lab_connect路径；可不结束HTTP网关进程，但设备owner/CCD流短暂重启。先保存实际CCD设置和SQLite中最近成功SLM输入及参数，随后恢复核验。

### 恢复前图案重建核验
- SQLite存在其它客户端后续成功操作，不能恢复为10月14日初始文档屏。按成功操作顺序重建最新输入、偏移和附加光栅，离线hash必须与日志最后成功提交一致后才修改硬件。
- 最新SLM1为asset44a6bbfd…/8bit/centered0,0，最新SLM2为assete493f655…/8bit/centered10,61及原有fx=-0.5；该载波是既有成功操作，不是本次新增加。
- 恢复脚本将先读取CCD真实设置，带expected_version做全量释放；先恢复CCD streaming/曝光/增益/AE，再单独枚举HDSLM并连接两屏，重放最新图案参数。整个HTTP网关进程和地址保持不变。

### 2026-10-18 SLM恢复结果

- 通过原MCP端点的lab_disconnect全部设备，SLM owner线程完整结束；CCD短暂释放后优先重连，恢复8000µs/增益100/AE0。未结束HTTP网关进程，未修改相机原始ROI/有效位深或做额外采图。
- 确认无本进程SLM窗口后独立HDSLM probe，匹配SLM1 x4992/index2和SLM2 x3072/index1；主服务新owner再次初始化枚举并绑定成功。
- 两屏重载当前实际图案及既有载波，最终SLM1 SHA26ca5916…5b5dc4，SLM2 SHAb0a78e82…b026fb，与最后成功实验操作完全一致。窗口alive/unobscured、未挂起，status=connected且requires_rebind不存在。
- CCD实时设置读回与维护前相同，camera_id/5312×4592/12bit保持，状态streaming。维护经过expected_version串行校验。runtime/slm_rebind_20261018保存before、成功SLM历史、fresh probe/bindings、全部操作ID及前后CCD读回；没有输出令牌。
- 接下来仅再次只读查询服务/设备状态并做文档检查，保留之前故障报告，不重复采图或重启。

- 恢复后再次只读健康检查通过：同PID20384/同端点，认证握手和18工具正常，SLM1/2均connected且无requires_rebind/错误字段，CCD streaming。原故障报告保留，after_health.json另存。文档10份/11本地链接无缺失，git diff检查通过。
- 本轮未改业务源码，采用实际MCP/SDK重连及数组/设置读回验证，不重复无关软件测试。同步维护记录至原授权仓库。

- 维护文档提交1c15f7f已同步GitHub main。普通SSH22被当前网络关闭，改用ssh.github.com:443并校验既有github.com主机密钥后推送成功；未改变全局SSH/代理配置。设备状态不受Git同步影响。

### 2026-10-18 再次检查及按需恢复运行前

- 用户要求检查MCP，若异常恢复正常；保留当前图案与CCD设置，必要时沿用已批准的短暂重连方式，不重复询问。
- 8765仍由PID20384监听、WLAN10.195.186.75。先验证认证/握手/18工具、两SLM周期窗口健康和CCD实时设置；两屏健康时从现有CCD流取1帧64×64软件ROI验证新帧，曝光/增益/AE/图案不改。用expected_version避免插入其他客户端调参，新证据单独目录保存。
- 若发现故障，先刷新当前参数与成功操作记录再修复，不使用上次恢复前的旧快照覆盖新实验。

- 本轮当前屏已改变为SLM1 500×500、SLM2 800×800（均8bit、当前附加载波0）。原恢复脚本仅重建独立slm_load_image历史，不能覆盖后来lab_load_and_capture的加载；在任何硬件操作前已发现并改用当前缓存input/display hash匹配联合命令中的原asset请求。
- 新恢复计划先与两路当前display hash逐个相等，再执行重连；CCD以实时16000µs/gain100/AE0恢复。所有快照与重建计划位于本轮独立recovery目录，上次证据保留。

### 2026-10-18 再次恢复与新帧验证结果

- 初检runtime/health_check_20261018_49253927/health.json确认协议认证正常、18工具可用，但两SLM再次error/requires_rebind；CCD仍streaming、16000µs/gain100/AE0。保留故障证据，未在初检时采图。
- 根据本轮实时input/display hash匹配SQLite成功lab_load_and_capture中的原资产，重建500×500的SLM1与800×800的SLM2，均8bit，偏移分别0,0和10,61，附加光栅均0。所有离线display hash相同后，带expected_version执行全量释放、优先恢复CCD、无SLM窗口时probe、新owner连接两屏及恢复图案。
- 恢复后SLM1 SHA7d0e767bd7988566787980a6f17e8f3339be92f907d91173a1f70b732f50bfe2，SLM2 SHA066d90f1446975c2751627f764672a6ed03277b53ea2d06e402e9ade02923a51，均与本轮维护前相同；两屏connected、窗口健康、无requires_rebind。CCD camera_id/全幅尺寸/有效位深和实时16000µs/gain100/AE0与维护前一致，streaming。完整恢复证据runtime/health_check_20261018_49253927/recovery/recovery.json。
- 最终检查前已在本轮运行范围中记录64×64软件ROI新帧实采；运行runtime/check_mcp_current_20261018.py退出0，healthy=true、18工具、两SLM connected，CCD streaming、ccd_frame_and_settings_ok=true。capture_id=ab672ed5-9ab4-4f3b-84b2-763cdfe4de53，采图前后曝光/增益/AE未变。证据runtime/health_check_20261018_4837df2c/health.json。
- 未改业务源码或运行中网关，PID20384与端点不变；CCD有已授权短暂断流。没有对光学效果或另一台电脑网络作超出证据的结论。更新四份核心文档及运行说明，接下来检查本地链接、凭据排除和Git差异，再同步既有授权仓库。
- 本轮文档检查通过：10份Markdown、11个本地链接无缺失，跟踪文件中无私有令牌，git diff --check通过。仅维护记录变化，以本轮实际MCP/SDK恢复、hash/设置读回和新帧实采为验证，不重跑无关软件测试。准备提交并通过既有GitHub SSH443路径同步，保持全局配置不变。
- 恢复与验证记录已提交b8d4db2，GitHub main由1c15f7f快进至b8d4db2并推送成功；运行数据、私有配置和令牌未上传。本条同步结果随收尾日志提交。

### 2026-10-19 恢复运行前

- 用户再次要求恢复MCP；先检查监听/认证/设备缓存状态与CCD实时读回，保留本轮图案和设置。沿用已明确授权的短暂CCD重连方式，不套用10月18日旧图、旧曝光。
- 已检查项目指令、前次恢复与健康检查脚本；沿用systematic-debugging定位异常。HDSLM探测仅允许在本进程SLM窗口释放后进行，网关可响应时保持进程和端点。
- 本轮快照/重建/操作与最终新帧报告使用独立20261019目录；恢复前校验实时图案hash及state_version未被其他客户端改变。恢复后将验证18工具、两路SLM窗口健康和CCD一张64×64软件ROI新帧，曝光/增益/AE保持本轮原值。
- 初检runtime/health_check_20261019_dabd790b/health.json：接口认证与18工具正常，SLM1/2 error/requires_rebind；CCD streaming、实际64000µs/gain100/AE0。当前Win32三个显示接口及矩形齐全，异常与此前拓扑变化锁存一致，尚无证据定位触发该历史变化的外部事件。
- 最新SLM1/2仍为500×500及800×800/8bit、offset0,0及10,61、附加光栅0，但内容hash已变，不能复用昨日图片。runtime/maintenance_20261019_769b242a/recovery已保存state_version482实时快照，并从联合操作匹配当前资产、离线hash相同。现在按原MCP接口全量释放设备、优先恢复CCD64000µs，再probe/rebind及重载原图；HTTP网关PID20384保持。

### 2026-10-19 恢复及最终验证结果

- recover.py退出0，status=recovered。同一网关PID20384/端点不变，两SLM新owner成功连接：SLM1 x4992/index2，SLM2 x3072/index1；两窗口connected/无遮挡、requires_rebind清除。
- SLM1 display SHA6f6ef85a98119206b8549401ec335283e3e9c87f37189f3a505361da9471bd9d，SLM2 SHA1cbdffee27ec77deb01930ff7a30418eefa98768301c3ad90a4de7653560a679，均与本轮维护前相同；CCD恢复64000µs/gain100/AE0、原身份/尺寸/位深和streaming，ccd_settings_equal=true。恢复证据runtime/maintenance_20261019_769b242a/recovery/recovery.json。
- 按运行前范围独立执行check_health.py，退出0、healthy=true、18工具、SLM1/2 connected、CCD streaming；取得64×64软件ROI新帧a944bfba-f251-4b05-8291-d3791e133583，采图前后CCD设置不变。最终报告runtime/health_check_20261019_7f82068c/health.json，故障报告保留。
- 更新四份核心文档与运行说明。未改业务源码，以实际MCP/SDK/图案hash/设置及新帧验证完成本次恢复。接下来核验Markdown链接、凭据排除与Git差异，同步维护记录至原授权仓库。历史拓扑变化的外部触发原因尚不确定，未绕过保护或声称永久解决复发。
- 文档核验通过：10份Markdown、11个本地链接无缺失，跟踪文件中不含私有令牌，git diff --check通过。运行证据和私有配置保持忽略；仅提交维护文档，使用此前验证的GitHub SSH443路径同步，不修改全局SSH/代理配置。

### 2026-10-20 重新绑定运行前

- 用户要求重新绑定两SLM，保留当前实验图案、偏移、光栅及CCD实时参数；沿用此前明确允许的短暂CCD重连方案，不使用昨日快照覆盖后续实验。
- 已检查核心文档、当前Git状态与上次已验证维护脚本。先读取实时MCP状态和Win32拓扑，离线匹配原资产及display hash；若需要结束SLM owner，按原接口全量释放、优先恢复CCD，再在无SLM窗口时probe/rebind。维护前校验state_version及图案元数据，后续逐步expected_version守卫。
- 新建20261020独立证据目录，旧证据保留；最终检查认证/18工具、两SLM窗口健康及CCD一张64×64软件ROI新帧，曝光/增益/AE保持本轮原值。网关可响应时不结束HTTP进程。
- 初检state_version501：SLM1 connected，SLM2 error='Projection window closed, moved or hung'；当前窗口检查alive/unobscured且无挂起、当前三个Win32显示接口齐全，无requires_rebind字段。源码核验显示周期健康检查曾失败会保留error状态，后续窗口健康不会自动清除；此次不直接沿用昨日拓扑故障诊断。
- 当前CCD缓存streaming/8000µs/gain100/AE0；维护脚本将再次实时读回。SLM2图案已变化，离线匹配最新联合加载原资产并校验display SHA2ba0c359…ae6f0c，SLM1保持6f6ef85a…71bd9d。证据runtime/maintenance_20261020_009aacd4/recovery/before.json及matched_current_patterns.json；现在按用户重新绑定要求释放owner、重新probe及加载两路原图。

### 2026-10-20 重新绑定结果

- recover.py退出0、status=recovered；新probe绑定SLM1 x4992/index2、SLM2 x3072/index1，两屏connected/无遮挡。display SHA分别6f6ef85a…71bd9d及2ba0c359…ae6f0c，与本轮维护前相同，图案/偏移/光栅保留。
- CCD实时读回8000µs/gain100/AE0，重连后身份/尺寸/位深及设置相同，streaming；HTTP网关PID20384及端点不变。完整证据runtime/maintenance_20261020_009aacd4/recovery/recovery.json。
- 独立执行check_health.py退出0、healthy=true、18工具、两SLM窗口健康；实际取得64×64软件ROI新帧5d252a9c-a599-466d-86bd-2d6b5dfd0807，CCD采图前后设置一致。报告runtime/health_check_20261020_b0b1fe40/health.json。
- 更新核心文档与运行说明，未改业务源码，采用本轮原生MCP/SDK/hash/设置与新帧证据验证。下一步核验文档链接、凭据排除及Git差异，再同步维护记录；不重复无关软件测试，不声称已确定历史窗口异常触发事件。
- 文档核验通过：10份Markdown、11个本地链接无缺失，跟踪文件中不含私有令牌，git diff --check通过。仅提交维护文档至原授权仓库；运行证据/私有配置保持忽略，SSH443使用既有主机密钥验证且不修改全局配置。
