# SLM / CCD MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在本机 Windows 上建立可供另一台局域网电脑的 Codex / Claude 客户端使用的 SLM / CCD MCP，覆盖图案、偏移、光栅、曝光和新帧采图。

**Architecture:** 一个服务进程内，MCP / HTTP 网关调用串行协调层，HDSLM 专用线程处理 SDK 与窗口消息，相机回调向有界队列发布 RAW。图像处理、文件存储和操作日志与设备适配分开；模拟模式使用同样的工具及数据路径。

**Tech Stack:** Windows x64、Python 3.12、本项目 `.venv`、官方 `mcp==2.3.0`（`mcp.server.MCPServer`）、NumPy、Pillow、Pydantic、Starlette、Uvicorn、SQLite、pytest。MCP 版本已于 2026-10-13 从 PyPI 元数据核验；依赖实际解析结果在安装时锁定。

**Spec:** [已批准设计](../specs/2026-10-13-slm-ccd-mcp-design.md)。本计划以用户当前偏移 (+10,+61) 为准。

## Global Constraints

- 项目位于 `D:/ExpSoftware/slm-ccd-mcp`；历史项目及 `D:/ExpSoftware` 的 SDK 原文件只读引用。
- 首版单进程、单 ASGI worker，在已登录 Windows 交互式桌面会话运行；硬件模式显式启用。
- HDSLM 在无本进程投屏窗口时枚举一次；所有 SDK 调用及消息泵在同一 owner 线程。
- SLM1 缺席不阻止 SLM2 / CCD；相同 SN 用角色、桌面矩形、尺寸联合绑定。
- SLM1 默认 8bit / uint8；SLM2 默认 native10 / uint16 / 0..1023；显式 8bit 相位输入保持原码。
- 小图相对居中偏移：SLM2 **(+10,+61)**，SLM1 (0,0)；1920×1200 中的 1000×1000 小图放置 **(470,161)**。
- 不隐式缩放、裁切、镜像或归一化；完整 panel 不重复偏移；光栅绝对重算。
- 相位码域 / LUT 相位域处理分别标记；振幅屏不做相位取模相加。
- 不写硬件 Gamma / LUT / 触发寄存器，不调用已知异常 SoftGamma setter/getter。
- 曝光为整数微秒，增益为 SDK analog gain percent；设置后读回，保留 RAW 行顺序及有效位深。
- 默认稳定等待 0.3 s + 一个实际曝光间隔，丢弃 3 张新完成帧，保存 1..16 张；默认最大超时 120 s。
- 预览长边 ≤1024，以固定有效位深范围映射；RAW 与预览分开。
- 每块上传解码后 ≤1 MiB，总长度默认 ≤32 MiB；路径最终目标需在 allowlist 根内。
- 网络 `/mcp` 默认端口 8765；MCP 和下载均校验 Bearer、Host / Origin；不输出凭据。
- 运行数据、用户输入、本机绑定与凭据不提交 Git；维护四个核心文档及运行前后日志。

## Review Focus

- JSON 的 `true` 不得被当成曝光 / 尺寸整数；NaN / Infinity 不得进入光栅或时序计算（任务 1、2、5）。
- 小图 / panel 切换、重复 set_grating 和恢复必须基于原始输入，不累计偏移 / 光栅（任务 2、6）。
- 同 SN、缺席角色及热插拔后错误匹配必须拒绝，不投到普通桌面（任务 4、6）。
- 重复请求、网络断开或保存失败不得重复硬件命令；返回已提交步骤和不确定状态（任务 3、6、7）。
- 极大伪造图片头、Windows junction / symlink、未完成上传与非法下载 ID 必须在分配 / 访问前拒绝（任务 2、3、7）。

---

## 文件职责与实施顺序

下列为预计创建的文件，当前尚无业务代码。文件名和跨任务接口按本计划固定，内部实现可按已批准设计选择。

| 任务 | 文件 / 职责 |
|---|---|
| 1 | `pyproject.toml`、`requirements.lock.txt`、`src/lab_mcp/models.py`、`config.py`、`errors.py`：环境、强类型输入、配置、统一错误 |
| 2 | `imaging/io.py`、`panel.py`、`grating.py`、`preview.py`：安全解码、拼板、光栅 / LUT、预览 |
| 3 | `storage/assets.py`、`captures.py`、`journal.py`：不可变输入、分帧结果、SQLite 去重 / 执行阶段 |
| 4 | `devices/slm.py`、`hdslm.py`、`windows.py`、`vendor.py`：单线程 SLM owner、设备选择、窗口检查、延迟加载 |
| 5 | `devices/camera.py`、`toupcam.py`、`frame_queue.py`：RAW 相机、配置读回、新帧选择 |
| 6 | `devices/simulated.py`、`controller.py`、`instance_lock.py`：同接口假设备、协调 / 状态版本、单实例 |
| 7 | `server/tools.py`、`app.py`、`security.py`：MCP 工具 / 资源、ASGI 认证与下载 |
| 8 | `cli.py`、`__main__.py`、`scripts/*.ps1`、`client_examples/`、`docs/operations.md`、`docs/acceptance.md`：入口、客户端连接与验收 |

创建 Python 包时补齐这些目录的 `__init__.py`；导入不加载厂家 DLL。每个任务完成后更新核心文档，运行前后写 LOG，进行本任务测试和检查后提交。首次执行前使用 using-git-worktrees 检查当前 Git / worktree 状态；最终用户可运行的交付目录仍为 `D:/ExpSoftware/slm-ccd-mcp`，不要把最终成果遗留在未合并的工作树。

## 公共数据与接口约定（由任务 1 创建）

- `SLMRole = Literal['slm1','slm2']`；`Role = Literal['slm1','slm2','ccd']`。
- `LabConfig`：`mode`、`host`、`port=8765`、`public_base_url`、`allowed_hosts`、`allowed_origins`、`token_env='LAB_MCP_TOKEN'`、`runtime_dir`、`input_roots`、`slm_sdk_dir`、`camera_sdk_root`、`slms:dict[SLMRole,SLMConfig]`、`camera:CameraConfig`、`capture_timeout_max_s=120`。
- `SLMConfig`：`enabled`、`serial`、`name_contains`、`desktop_xy`、`panel_wh`、`bit_depth`、`offset_xy`、`background`、`restore_source`。硬件绑定字段可未配置，但使用对应角色前必须通过探测 / 绑定。
- `CameraConfig`：可选 `camera_id`、`expected_model='IUA24500KMA'`；连接不把历史曝光当默认。
- `GratingSpec`：`fx=0.0`、`fy=0.0`、`phi0=0.0`、`mode:Literal['code','lut']='code'`、`lut_source:str|None`。
- `LoadRequest`：`role`、`source`（`asset:<id>` 或 allowlist 本机路径）、`bit_depth:Literal[8,10]`、`placement:Literal['centered','panel']`、可选 `offset_xy` / `background`、`packed_rgb=False`、`as_restore=False`。
- `CameraPatch`：可选 `exposure_us` / `gain_percent` / `auto_exposure:bool`。显式曝光且未指定 AE 时按 AE=false 处理；曝光与 AE=true 同时指定时拒绝矛盾输入。
- `CaptureRequest`：`frames=1`、`roi_xywh=None`、`settle_s=0.3`、`discard_frames=3`、`timeout_s=120`、`preview_bounds=None`；所有数值有限，整数拒绝 bool。
- `JointRequest`：`loads:list[LoadRequest]`（0..2，角色不重复）、`camera_patch:CameraPatch|None`、`capture:CaptureRequest`。
- `PreparedPanel`（dataclass）：`codes:np.ndarray`、`metadata:dict[str,Any]`。
- `FrameRecord`（dataclass）：`raw:np.ndarray`、`metadata:dict[str,Any]`，至少有 `host_monotonic_ns`、`host_frame_counter`、`origin_xy`；可选相机 seq / timestamp / exposure 只保存有效值。
- `LabError(code:str,message:str,*,stage:str='validate',hardware_submitted:bool=False,details:dict|None=None)`；`to_dict()->dict` 可序列化且不含凭据。
- 对外 JSON 均包含相关 operation / capture ID；数组只在进程内传递，RAW 通过文件下载。

### Task 1: 可安装项目、强类型配置与无设备导入

**Files:** 创建 `pyproject.toml`、`src/lab_mcp/{__init__,models,config,errors}.py`、`config/{simulation,hardware.example}.toml`、`.env.example`、`tests/test_config.py`、`tests/test_imports.py`；安装后生成 `requirements.lock.txt`；更新核心文档。

**Interfaces:**
- Produces: 上述全部公共模型；`load_config(path:Path,*,mode:str|None=None)->LabConfig`；`LabError.to_dict()`。
- 基线 Python ≥3.12；运行依赖 `mcp==2.3.0`、`numpy>=1.26,<3`、`Pillow>=10,<13`、`pydantic>=2.12,<3`、`starlette>=0.48,<1`、`uvicorn>=0.31,<1`。测试使用 `pytest>=8,<10`、`pytest-asyncio>=0.24,<2`、官方 SDK 的客户端依赖 `httpx2`。

- [ ] **Step 1 — 写配置失败测试。** `test_slm2_default_alignment` 断言 `offset_xy==(10,61)`；`test_strict_numbers` 对曝光 true、fx=NaN、settle_s=Inf 断言 ValidationError；`test_hardware_requires_explicit_binding` 保留未绑定状态，不能自动选择旧 index。

  ```python
  def test_slm2_default_alignment():
      assert load_config(Path('config/simulation.toml')).slms['slm2'].offset_xy == (10, 61)

  def test_strict_exposure_integer():
      with pytest.raises(ValidationError):
          CameraPatch(exposure_us=True)
  ```
- [ ] **Step 2 — 执行前建独立环境并验证红灯。** `& 'D:/Program Files/Python312/python.exe' -m venv .venv`；仅在 `.venv` 安装测试 / 基线依赖。`& .venv/Scripts/python.exe -m pytest tests/test_config.py -q`，预期因 `lab_mcp` / 模型未实现失败。每条命令前后记 LOG。
- [ ] **Step 3 — 实现配置和公共模型。** TOML 用 `tomllib`；Pydantic strict 整数、有限浮点及交叉条件；示例不含凭据、旧屏幕 index 或真实绑定猜测；sim 模式设 SLM1 缺席 / SLM2 1920×1200 / offset10,61。pyproject 配置 src 布局与 `lab-mcp` 入口（入口文件到任务 8 完成）。
- [ ] **Step 4 — 安装并验证。** `& .venv/Scripts/python.exe -m pip install -e '.[dev]'`；`& .venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_imports.py -q`。导入测试拦截 WinDLL / os.add_dll_directory，断言导入不调用它们；应全部 PASS。`pip freeze --exclude-editable` 保存依赖精确版本至 lock 文件，避免把本机editable绝对路径写入锁文件。
- [ ] **Step 5 — 更新文档并提交。** 实际确认安装命令后才写入 README；`git diff --check` 后提交 `build: add typed configuration and isolated Python environment`。

### Task 2: 图像解码、精确放置与光栅

**Files:** 创建 `src/lab_mcp/imaging/{__init__,io,panel,grating,preview}.py`、`tests/test_image_io.py`、`tests/test_panel.py`、`tests/test_grating.py`、`tests/test_preview.py`。

**Interfaces:**
- Consumes: `LoadRequest`、`SLMConfig`、`GratingSpec`、`PreparedPanel`。
- Produces: `read_codes(path:Path,*,packed_rgb:bool=False,max_file_bytes:int=33554432)->np.ndarray`；`read_phase_lut(path:Path,*,expected_codes:int|None=None)->np.ndarray`（一维有限实数、长度256/1024）；`compose_panel(codes:np.ndarray,config:SLMConfig,request:LoadRequest)->PreparedPanel`；`add_phase_grating(codes:np.ndarray,spec:GratingSpec,*,lut:np.ndarray|None=None)->np.ndarray`；`make_amplitude_grating(width:int,height:int,*,fx:float,fy:float,style:str,low:int,high:int,duty:float=0.5)->np.ndarray`；`make_preview(raw:np.ndarray,effective_bits:int,*,bounds:tuple[int,int]|None=None,max_side:int=1024)->tuple[bytes,dict]`。
- panel metadata 固定键：`input_shape`、`panel_wh`、`placement_xy`、`offset_xy`、`bit_depth`、`input_sha256`、`displayed_array_sha256`；光栅参数 / 模式由协调层添加。

- [ ] **Step 1 — 写独立预期值测试。** `test_current_1000_alignment` 断言 panel[161:1161,470:1470] 与输入逐码相等；`test_panel_has_no_second_offset` 全 panel 原样；`test_native10_and_rgb_rejection` 拒绝1024码及普通RGB，显式 RGB10 回读码一致；`test_code_carrier_quarter_cycle` 用 fx=.25 的手算4点斜坡；`test_circular_lut_wrap_and_tie` 以接近0/2π及等距 LUT 样例断言最近圆周相位 / 小码平局。

  ```python
  def test_current_1000_alignment():
      cfg = load_config(Path('config/simulation.toml')).slms['slm2']
      codes = np.full((1000, 1000), 17, dtype=np.uint16)
      req = LoadRequest(role='slm2', source='example.npy', bit_depth=10, placement='centered')
      result = compose_panel(codes, cfg, req)
      assert result.metadata['placement_xy'] == [470, 161]
      np.testing.assert_array_equal(result.codes[161:1161, 470:1470], codes)
      assert result.codes[160, 470] == 0
  ```
- [ ] **Step 2 — 验证红灯。** `& .venv/Scripts/python.exe -m pytest tests/test_image_io.py tests/test_panel.py tests/test_grating.py tests/test_preview.py -q`，预期相应模块 / 接口未实现失败。
- [ ] **Step 3 — 实现解码与变换。** NPY 禁止 pickle，以只读 mmap 和有界 header 检查 dtype / 形状 / 文件实际长度后复制；PNG / BMP 在解码前限制尺寸 / 像素数，默认 H/W≤8192、总像素≤8,388,608，异常头拒绝。光栅从基图重算；LUT 查表分块计算，避免整图×1024 分配；preview 用固定范围映射后缩略，保留映射元数据。
- [ ] **Step 4 — 加并验证边界测试。** `test_forged_npy_shape_rejected_before_allocation`、`test_huge_image_header_rejected`、`test_out_of_bounds_keeps_input`、`test_grating_repeat_identical`、`test_amplitude_binary_duty`、`test_preview_keeps_raw_unchanged`；运行本任务全部测试，预期 PASS，无位深拉伸 / 翻转。
- [ ] **Step 5 — 记录并提交。** 更新光栅实际舍入规则（NumPy rint、半整数取偶数），保留码域 / LUT 模式标记；提交 `feat: add exact SLM image composition and grating generation`。

### Task 3: 资产、采集文件与可追溯操作记录

**Files:** 创建 `src/lab_mcp/storage/{__init__,assets,captures,journal}.py`、`tests/test_assets.py`、`tests/test_captures.py`、`tests/test_journal.py`。

**Interfaces:**
- Consumes: `LabConfig`、`FrameRecord`、`read_codes`、`make_preview`。
- Produces: `AssetStore(runtime_dir:Path,input_roots:list[Path])`：`begin(filename:str,total_bytes:int,sha256:str)->dict`、`chunk(upload_id:str,offset:int,data:bytes)->dict`、`finish(upload_id:str,*,packed_rgb:bool=False,kind:str='codes')->dict`、`resolve(source:str)->Path`、`list()->list[dict]`、`register_codes(codes:np.ndarray,label:str)->dict`。
- `kind='phase_lut'` 的 NPY 为长度256/1024的一维有限浮点数组，只供 LUT 使用；不将它当图投屏。
- `CaptureStore(runtime_dir:Path)`：`prepare(request:CaptureRequest,sensor_wh:tuple[int,int],effective_bits:int)->CaptureWriter`；writer 提供 `write_frame(frame:FrameRecord)->None`、`finish(metadata:dict)->dict`、`fail(error:dict)->dict`；`registered_file(capture_id:str,file_id:str)->Path`。
- `OperationJournal(path:Path)`：`begin(operation_id:str,params:dict)->dict`、`stage(operation_id:str,name:str,*,hardware_submitted:bool)->None`、`finish(operation_id:str,result:dict)->None`、`fail(operation_id:str,error:dict)->None`、`get(operation_id:str)->dict`。记录状态使用intent / running / succeeded / failed / uncertain；已明确失败与无法确认是否执行分开。启动恢复将旧未完成 intent / running 标为 uncertain。

- [ ] **Step 1 — 写存储失败测试。** `test_upload_limits_and_sha` 测1 MiB块、32 MiB总上限、错hash、finish前不可 resolve；`test_path_escape_and_symlink` 测根外目标 / Windows链接；`test_duplicate_operation_payload` 测相同 ID 返回记录、不同 payload 冲突；`test_restart_preserves_uncertain` 测仅intent后的新实例不得执行操作。

  ```python
  def test_restart_preserves_uncertain(tmp_path):
      operation_id = str(uuid.uuid4())
      OperationJournal(tmp_path / 'ops.sqlite').begin(operation_id, {'op': 'slm_load_image'})
      resumed = OperationJournal(tmp_path / 'ops.sqlite')
      assert resumed.get(operation_id)['status'] == 'uncertain'
  ```
- [ ] **Step 2 — 验证红灯。** `& .venv/Scripts/python.exe -m pytest tests/test_assets.py tests/test_captures.py tests/test_journal.py -q`，预期 storage 接口缺失失败。
- [ ] **Step 3 — 实现存储。** 资产用不可变UUID名与单独元数据，最终路径 resolve / 根比较使用规范化路径与最终链接目标；上传连续块，重复同offset同内容允许，冲突拒绝。RAW逐帧写NPY，原子发布JSON，单帧即时落盘不堆16张全幅内存；磁盘空间估计含RAW+预览+余量，写失败保留partial。SQLite记录intent先于硬件；JSONL仅记录紧凑非敏感事件。
- [ ] **Step 4 — 验证恢复与下载登记。** `test_partial_capture_survives_write_failure` 保存首张后模拟写失败，断言首帧NPY仍可读、manifest标partial；`test_raw_and_preview_separate` 原码hash一致；`test_disk_full_precheck` 不创建伪成功结果；`test_unregistered_download_rejected` 拒绝根内但未登记文件。运行本任务测试，预期 PASS。
- [ ] **Step 5 — 记录并提交。** 临时物清理只指向本项目上传区；有价值partial不删除；提交 `feat: persist assets captures and idempotent operation records`。

### Task 4: 单线程 HDSLM owner 与窗口状态

**Files:** 创建 `src/lab_mcp/devices/{__init__,slm,hdslm,windows,vendor}.py`、`tests/test_slm_owner.py`、`tests/test_display_binding.py`、`tests/test_window_visibility.py`。

**Interfaces:**
- Consumes: `SLMConfig`、`PreparedPanel`、`LabError`。
- Produces: `SLMAdapter` Protocol：`connect(roles:list[SLMRole])->dict`、`show(role:SLMRole,panel:PreparedPanel)->dict`、`status()->dict`、`disconnect(roles:list[SLMRole]|None=None)->dict`。
- `HDSLMOwner(configs:dict[SLMRole,SLMConfig],sdk_dir:Path,*,sdk_factory:Callable|None=None)` 实现该协议；`probe_displays(sdk_dir:Path)->list[dict]` 在独占探测进程内枚举后退出，不打开窗口；`select_roles(configs:dict,displays:list[dict])->dict` 为纯函数。
- show 返回 `submitted_monotonic_ns`（SDK show和随后pump完成之后采样）、panel metadata及窗口状态；缓存查询不声称物理framebuffer读回。
- `load_vendor_module(name:str,path:Path)->ModuleType` 只在显式硬件连接 / 探测时调用；`inspect_projection_window(hwnd:int,expected_rect:tuple[int,int,int,int])->dict` 返回保守窗口检查。

- [ ] **Step 1 — 写SDK fake测试。** `test_enum_once_same_thread` 记录所有sdk调用的线程ID，重复status后枚举次数仍1；`test_missing_slm1_slm2_works` 缺席SLM1不阻止show SLM2；`test_same_serial_rect_binding` 两同SN按矩形区分，重复匹配 / 同index / 普通桌面均拒绝。

  ```python
  # SDK fake 应提供调用记录；本用例需要的测试fixtures在本任务测试文件内定义。
  def test_enum_once_same_thread(owner, fake_sdk):
      owner.connect(['slm2'])
      owner.status()
      owner.status()
      assert fake_sdk.enum_calls == 1
      assert len(set(fake_sdk.call_thread_ids)) == 1
  ```
- [ ] **Step 2 — 验证红灯。** `& .venv/Scripts/python.exe -m pytest tests/test_slm_owner.py tests/test_display_binding.py tests/test_window_visibility.py -q`，预期接口不存在失败。
- [ ] **Step 3 — 实现owner与延迟加载。** SDK import / enum / open / show / close / pump同线程执行，用队列+Future；启动设置owner线程DPI上下文、offset0和附加相位false；循环持续pump。缓存身份，窗口检查按本进程PID+精确矩形选HWND，不选首个同尺寸窗口；只检查遮挡，不自动关闭其他程序。
- [ ] **Step 4 — 验证异常。** `test_show_error_is_not_retried`、`test_window_closed_stops_role`、`test_topology_change_requires_rebind`、`test_no_soft_gamma_or_trigger_calls`、`test_shutdown_closes_every_opened_role`。查询桌面拓扑只用Win32非SDK枚举；变化使绑定失效。fake测试 PASS 不计为真实投屏结果。
- [ ] **Step 5 — 记录并提交。** 提交 `feat: add single-owner HDSLM control and explicit role binding`。

### Task 5: ToupCam RAW 流、设置读回与新帧选择

**Files:** 创建 `src/lab_mcp/devices/{camera,toupcam,frame_queue}.py`、`tests/test_camera_settings.py`、`tests/test_camera_frames.py`、`tests/test_camera_shutdown.py`。

**Interfaces:**
- Consumes: `CameraConfig`、`CameraPatch`、`CaptureRequest`、`FrameRecord`、`LabError`。
- Produces: `CameraAdapter` Protocol：`connect()->dict`、`settings()->dict`、`validate_patch(patch:CameraPatch)->None`、`apply_settings(patch:CameraPatch)->dict`、`capture(request:CaptureRequest,boundary_ns:int,on_frame:Callable[[FrameRecord],None])->dict`、`status()->dict`、`disconnect()->dict`。
- `ToupCamAdapter(config:CameraConfig,sdk_root:Path,*,sdk_factory:Callable|None=None)` 实现协议。`FreshFrameQueue(max_pending:int=3)`：`publish(frame:FrameRecord)->None`、`publish_error(error:Exception)->None`、`collect(request:CaptureRequest,boundary_ns:int,exposure_us:int,on_frame:Callable)->dict`。

- [ ] **Step 1 — 写相机fake失败测试。** `test_manual_exposure_disables_ae_and_reads_back` 设置6000µs / gain100返回SDK读回；`test_readback_mismatch_is_error`；`test_freshness_threshold_and_three_discards` 将边界前 / 阈值前 / 合格新帧混入，断言仅阈值后丢3帧之后的身份被保存；`test_roi_preserves_sensor_coordinates` 无翻转。

  ```python
  # camera fixture以本任务fake SDK构建，明确记录SDK设置与get读回。
  def test_manual_exposure_disables_ae_and_reads_back(camera):
      camera.connect()
      result = camera.apply_settings(CameraPatch(exposure_us=6000, gain_percent=100))
      assert result['auto_exposure'] == 0
      assert result['exposure_us'] == 6000
      assert result['gain_percent'] == 100
  ```
- [ ] **Step 2 — 验证红灯。** `& .venv/Scripts/python.exe -m pytest tests/test_camera_settings.py tests/test_camera_frames.py tests/test_camera_shutdown.py -q`，预期接口缺失失败。
- [ ] **Step 3 — 实现持续相机。** 延迟加载toupcam+x64 DLL；绑定ID，保存原设置；读取范围、YYYY / bits / fullsize；启用RAW16容器。callback只PullImageV4、复制当前请求区域并发布，队列上限3，闲时不积累完整帧。capture用单调时间+0.3s+曝光阈值和新帧丢弃；on_frame在协调线程落盘。
- [ ] **Step 4 — 验证失效与关闭。** `test_timeout_returns_partial_metadata`、`test_disconnect_wakes_waiter`、`test_invalid_frame_shape_fails`、`test_capture_budget_prechecked`、`test_stop_restore_close_all_attempted`；注入Stop / 读回失败仍逐项尝试恢复与Close，保存失败明细。开AE时逐帧有效曝光保留；缺失有效字段则说明仅SDK设置读回，不伪造曝光中点。
- [ ] **Step 5 — 记录并提交。** 提交 `feat: acquire fresh monochrome RAW frames with verified camera settings`。

### Task 6: 模拟设备、协调事务与状态版本

**Files:** 创建 `src/lab_mcp/devices/simulated.py`、`src/lab_mcp/controller.py`、`instance_lock.py`、`tests/test_controller.py`、`tests/test_joint_capture.py`、`tests/test_instance_lock.py`。

**Interfaces:**
- Consumes: 两个adapter Protocol、资产 / 采集 / 操作store、公共模型和纯图像函数。
- Produces: `SimulatedSLM`、`SimulatedCamera` 同adapter签名；`LabController(config:LabConfig,slm:SLMAdapter,camera:CameraAdapter,assets:AssetStore,captures:CaptureStore,journal:OperationJournal)`。
- controller：`status()->dict`、`execute(op:str,args:dict,*,operation_id:str|None=None,expected_version:int|None=None)->dict`、`operation_get(operation_id:str)->dict`、`close()->dict`；operation_id校验UUID。`InstanceLock(runtime_dir:Path)` 为上下文管理器，Windows用OS级锁而非仅PID文件。
- `execute` 的op枚举对应设计中的修改工具；`lab_connect/disconnect`、`slm_*`、`ccd_set_settings/capture`、`lab_load_and_capture` 全部进入该入口；资产上传由AssetStore管理。

- [ ] **Step 1 — 写事务失败测试。** `test_joint_preflight_before_any_mutation` 第二个asset错误 / 缺席角色时两设备调用计数0；`test_joint_order_and_no_interleaving` 验证camera settings→SLM2→SLM1→capture；`test_repeat_offset_grating_restore_from_original` 三次重复配置hash相同，restore返回注册的原图配置。

  ```python
  # connected_controller、joint_args由本任务fixtures创建；事件表只记录实际修改/采图。
  def test_joint_order_and_no_interleaving(connected_controller, joint_args):
      result = connected_controller.execute('lab_load_and_capture', joint_args)
      assert result['status'] == 'succeeded'
      assert connected_controller.test_device_events == [
          'camera.settings', 'slm2.show', 'slm1.show', 'camera.capture']
  ```

  `test_device_events` 仅在fixture测试包装器中提供，不加入生产controller接口。
- [ ] **Step 2 — 验证红灯。** `& .venv/Scripts/python.exe -m pytest tests/test_controller.py tests/test_joint_capture.py tests/test_instance_lock.py -q`，预期实现缺失失败。
- [ ] **Step 3 — 实现协调层。** 同步全局操作锁内做ID去重 / 版本检查→完整预检→intent落盘→按步骤执行→保存结果 / state_version；status读取独立缓存锁，不被capture阻塞。保留原始asset+位置+grating，修改从基图重算；slm_restore使用as_restore或配置restore_source显式登记的配置快照，connect时预检配置恢复源但不自动投屏。uniform是新全panel基图，清空先前附加grating / 小图偏移。
- [ ] **Step 4 — 验证并发 / 失败。** `test_concurrent_same_id_executes_once`、`test_version_conflict_precedes_sdk`、`test_save_failure_reports_submitted_stage`、`test_uncertain_operation_not_replayed`、`test_status_during_capture_is_responsive`、`test_only_one_instance_can_own_runtime`。simulate相机使用可重复的非对称图案 / 已显示状态依赖信号，所有结果标simulation，不冒充光学模型。
- [ ] **Step 5 — 记录并提交。** 提交 `feat: coordinate idempotent SLM camera transactions and simulated operation`。

### Task 7: 网络 MCP、认证和结果下载

**Files:** 创建 `src/lab_mcp/server/{__init__,tools,app,security}.py`、`tests/test_mcp_protocol.py`、`tests/test_http_security.py`、`tests/test_downloads.py`。

**Interfaces:**
- Consumes: `LabController`、`LabConfig`、`AssetStore`、`CaptureStore`、`LabError`。
- Produces: `create_mcp(controller:LabController,assets:AssetStore,captures:CaptureStore)->MCPServer`；`create_app(config:LabConfig,controller:LabController,*,token:str)->Starlette`；`BearerAndOriginMiddleware(app,*,token:str,allowed_hosts:list[str],allowed_origins:list[str])`。
- MCP端点 `/mcp`；下载 `/captures/{capture_id}/{file_id}`，URL不含token。资源 `lab://status`、`capture://{capture_id}/metadata`、`capture://{capture_id}/preview`。

- [ ] **Step 1 — 写真实协议 / HTTP失败测试。** 官方客户端使用 `from mcp import Client`，通过带认证http client的Streamable HTTP transport连接sim ASGI / 回环服务，验证设计全部工具名、schema单位、8/10bit、preview ImageContent。`test_missing_or_wrong_token` 返回401；`test_invalid_host_or_origin` 返回403；`test_download_requires_registered_id` 拒绝路径穿越 / 未登记ID。

  ```python
  # asgi_client fixture以本任务create_app和simulate controller构建。
  @pytest.mark.asyncio
  async def test_missing_token(asgi_client):
      response = await asgi_client.post('/mcp', headers={'Host': '127.0.0.1:8765'}, json={})
      assert response.status_code == 401
  ```
- [ ] **Step 2 — 验证红灯。** `& .venv/Scripts/python.exe -m pytest tests/test_mcp_protocol.py tests/test_http_security.py tests/test_downloads.py -q`，预期server接口缺失失败。
- [ ] **Step 3 — 实现MCP与ASGI。** 使用2.3.0的 `MCPServer` / `streamable_http_app()` 及Starlette lifespan，外层认证保护所有路由；保留SDK Host/Origin防护，按config allowlist配置。工具typed输入调用controller，所有阻塞操作在 `asyncio.to_thread` 中执行；控制锁保留在线程内，网络取消不取消真实执行。读工具正确声明readOnly，修改工具声明修改性质；回传JSON+PNG内容块。
- [ ] **Step 4 — 验证端到端。** `test_upload_load_capture_preview_download` 上传NPY→load→offset10,61→载波→expo→capture→PNG解码→RAW下载hash核对；`test_cancelled_client_does_not_reexecute` 断开后operation_get可取唯一结果；`test_legacy_handshake_client` 验证2025-11-25握手兼容；`test_logs_do_not_contain_token_or_base64`。全部PASS后才声称MCP调用链可用。
- [ ] **Step 5 — 记录并提交。** 服务body限额4 MiB容纳1 MiB base64块；预览≤1024，RAW用文件流；提交 `feat: serve authenticated MCP tools previews and RAW downloads`。

### Task 8: 可运行入口、客户端配置和分阶段验收

**Files:** 创建 `src/lab_mcp/{cli,__main__}.py`、`scripts/{start-lab-mcp,setup-lan-firewall}.ps1`、`client_examples/{codex.config.toml,claude.desktop.json}`、`docs/{operations,acceptance}.md`、`tests/test_cli.py`、`tests/test_smoke.py`。

**Interfaces:**
- Consumes: create_app / controller / config / instance_lock及全部已定义接口。
- Produces: `main(argv:list[str]|None=None)->int`；`lab-mcp serve --config <path> --mode simulate|hardware`；`lab-mcp probe --config <path>`；`lab-mcp smoke --url <url> --token-env LAB_MCP_TOKEN`。probe在独占进程无投屏窗口时运行，输出候选和CCD身份，不更改绑定猜测。
- 启动脚本使用项目venv；若启动后台helper，`Start-Process -WindowStyle Hidden`，投屏窗口仍在交互式会话。防火墙脚本必需显式本机地址 / 远端地址或私网范围，仅Private profile、指定端口；不自动调用。

- [ ] **Step 1 — 写入口失败测试。** `test_cli_simulate_never_loads_vendor`；`test_hardware_flag_and_binding_required`；`test_probe_refuses_active_owner`；`test_cli_error_redacts_secrets`；`test_smoke_uses_real_mcp` 在模拟服务上断言upload、配置、capture、下载hash一致。

  ```python
  def test_hardware_flag_and_binding_required(tmp_path):
      # fixture配置使用已定义硬件示例，绑定未配置；此失败发生在DLL加载之前。
      code = main(['serve', '--config', 'config/hardware.example.toml', '--mode', 'hardware'])
      assert code != 0
  ```
- [ ] **Step 2 — 验证红灯。** `& .venv/Scripts/python.exe -m pytest tests/test_cli.py tests/test_smoke.py -q`，预期cli / scripts缺失失败。
- [ ] **Step 3 — 实现入口和操作文档。** 明确simulate、probe、绑定、hardware、停止的步骤；令牌从环境读取，命令行不明文回显。查询官方OpenAI Codex MCP文档及Anthropic客户端文档；Codex提供HTTP/Bearer-env模板，Claude本地stdio入口按支持情况提供标准远程MCP桥接配置，注明桥接所需Node / 包版本；不把实验电脑变成云端公网connector。
- [ ] **Step 4 — 完成无需硬件的验证。** `& .venv/Scripts/python.exe -m pytest -q` 全部PASS；`& .venv/Scripts/python.exe -m compileall -q src` 退出0；`& .venv/Scripts/python.exe -m pip check` 无破损依赖；CLI help与一次真实回环网络smoke成功。只做一次全量验证，后续有新改动 / 失败才重跑相关范围。
- [ ] **Step 5 — 当前设备探测和小范围联调。** 核验无本项目owner，运行probe，保存runtime探测报告；让用户确认候选与物理SLM2的对应、已知加载图、曝光和restore图后进行投屏 / CCD联调。若ToupView占用CCD，报告占用，等待用户释放，不关闭其进程。记录offset10,61、一次小幅光栅、SDK曝光读回、RAW有效位深、freshness及下载hash；SLM1保持缺席。
- [ ] **Step 6 — 局域网交付与阶段结论。** 给出具体本机私网地址、启动命令和两种客户端配置；另一台电脑执行相同smoke。无法直接接触该电脑时留下完整验收步骤，明确远端连接待用户执行，不能用回环测试代替。SLM1插入后按关闭owner→probe→绑定→8bit联调独立验收。
- [ ] **Step 7 — 收尾审查和提交。** 按选择的执行流程完成最终代码审查，修复实际问题；更新README / LOG / REPORT / AGENTS，区分sim、真实SDK和局域网证据；确认输出归档 / 临时物清理，提交 `feat: deliver CLI client setup and verified experiment control workflow`。

## 覆盖检查与阶段交付

| 设计要求 | 负责实施 | 验证依据 |
|---|---|---|
| 配置、当前偏移、用户约束 | 1、2、8 | typed config、像素放置、CLI |
| SDK唯一owner、窗口、同SN、缺席 / 热插拔 | 4、6 | SDK fake / 绑定 / 状态测试 + 后续现场probe |
| RAW、曝光 / AE、ROI、新帧、关闭恢复 | 5 | camera fake / 时间身份 / 异常测试 + 后续SDK读回 |
| 图片位深、RGB10、panel、光栅 / LUT / 振幅 | 2、6 | 独立码值预期 / 重复重算测试 |
| 上传 / 路径 / 大图、逐帧保存 / partial | 2、3、7 | 对抗输入 / 磁盘失败 / 下载登记 |
| 串行联合操作、版本、去重、uncertain | 3、6、7 | 并发 / 断网 / 失败阶段测试 |
| MCP工具 / 资源 / 图像 / 下载 /认证 | 7、8 | 实际SDK client回环MCP与网络smoke |
| 交互式桌面、单实例、CLI、客户端配置 | 6、8 | OS锁 / CLI / 官方配置核验 |
| 核心文档、记录、清理与验收边界 | 每任务、8 | Git diff / 文档检查 / 证据分级 |

模拟MCP交付（任务1..8的无硬件部分）可独立使用和检验。现场投屏采图与远端联调使用该同一程序，不另造一次性实验脚本；SLM1未插入和远端电脑不可访问均不阻塞完成代码 / 回环验收，但必须在最终状态中如实列为未完成的现场验证。

## 执行方式与本次交接

推荐 **本会话直接执行（Native）**：8个任务依赖共同模型、设备协议和协调接口，直接执行便于统一这些接口，避免多轮上下文交接；完成后按流程做独立代码审查。

可选 **逐任务子代理执行（Subagent-driven）**：各任务由新实施代理完成并经过新审查代理检查，适合希望每个阶段都有独立审查的情况，代价是更多上下文和审查轮次。

本计划编写完成后由主代理自审规范覆盖、步骤粒度、类型一致性、五项Review Focus和文档比例，不为计划自审派代理。用户审阅计划并选择执行方式后才开始安装产品依赖和业务实现。硬件联调前所需的物理角色 / 图片 / 曝光确认在任务8明确请求，不阻塞之前的代码工作。

## 参考

- [官方 MCP Python SDK 2.x 文档](https://py.sdk.modelcontextprotocol.io/)，当前稳定路线使用MCPServer。
- [MCP 包元数据](https://pypi.org/pypi/mcp/json)，本次只读核验2.3.0 / Requires-Python≥3.10；本项目选择本机已核验的3.12。
- [运行和传输选项](https://py.sdk.modelcontextprotocol.io/run/)。
