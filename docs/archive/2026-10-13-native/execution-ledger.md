# SDD ledger — plan: docs/superpowers/plans/2026-10-13-slm-ccd-mcp-implementation.md

Execution: Native, approved by user “开始” on 2026-10-13. Branch feat/slm-ccd-mcp, base c93d311.
Ruling: Work in the user's new standalone repository on a feature branch at the required delivery path; no additional worktree — preserves one runnable project directory; cost: future parallel modifications need a separate checkout.
Pre-flight: Tasks 1→2/3/4/5/6/7/8 share strict DTOs: consistent.
Pre-flight: Tasks 2→3/6 share code and LUT readers / panel metadata: consistent.
Pre-flight: Tasks 3→6/7 share journal and streamed capture store: consistent.
Pre-flight: Tasks 4/5→6 use synchronous adapters, callbacks never mutate devices: consistent.
Pre-flight: Tasks 6→7/8 expose controller execute/status and app factory: consistent.
Task 1: in_progress, base c93d311; initial repository has no application or tests.

Task 5: Ruling: Windows monotonic clock readings are quantized at about16ms; freshness test uses hand-authored frame timestamps instead of 2ms wall-clock gaps — deterministic threshold test, no production freshness relaxation; cost: live precision remains host-clock limited and is recorded.
Task 1: complete (commits c93d311..0154092, tests: .venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_imports.py -q → 13 passed in 0.31s)
Task 2: complete (commits 0154092..1ea1453, tests: .venv/Scripts/python.exe -m pytest tests/test_image_io.py tests/test_panel.py tests/test_grating.py tests/test_preview.py -q → 11 passed in 0.63s)
Task 3: complete (commits 1ea1453..88e9bff, tests: .venv/Scripts/python.exe -m pytest tests/test_assets.py tests/test_captures.py tests/test_journal.py -q → 8 passed, 1 skipped in 0.81s)
Task 4: complete (commits 88e9bff..039360a, tests: .venv/Scripts/python.exe -m pytest tests/test_slm_owner.py tests/test_display_binding.py tests/test_display_binding.py tests/test_window_visibility.py -q → 9 passed in 0.34s)
Task 5: complete (commits 039360a..60c9d5b, tests: .venv/Scripts/python.exe -m pytest tests/test_camera_settings.py tests/test_camera_frames.py tests/test_camera_shutdown.py -q → 9 passed in 0.51s)
Task 6: complete (commits 60c9d5b..b46d1a5, tests: .venv/Scripts/python.exe -m pytest tests/test_controller.py tests/test_joint_capture.py tests/test_instance_lock.py -q → 9 passed in 1.25s)
Task 7: complete (commits b46d1a5..e918be6, tests: .venv/Scripts/python.exe -m pytest tests/test_mcp_protocol.py tests/test_http_security.py tests/test_downloads.py -q → 7 passed in 2.43s)

### Final review and single fix pass
Final: Ruling: Review minors7/8 regraded Important — defaultSLM1 failure blocks the normal amplitude workflow; huge finite phi0 silently corrupts accepted phase output — cost if wrong: regression-test maintenance only.
Final: fixed findings1..8 — tests/test_review_regressions.py 12 failing→12 passing, full suite83 passed/2 Windows file-symlink permission skips; directoryjunction exercised on Windows.
Final: Ruling: Optical response/first-order direction/exposure-start timing — dark SDK frame and software freshness validate transport only; laser-off optical verification remains pending — cost if wrong: later optical test may reveal calibration/timing errors.
Final: Ruling: Native window identity/occlusion — full Windows monitor-interface snapshot and actual native window health will be checked during integration, no physical framebuffer readback claimed — cost if wrong: desktop overlay/driver differences need site-specific adjustment.
Final: Ruling: Remote routing/firewall/Claude compatibility — concrete client templates and LAN endpoint delivered, other computer inaccessible here so remote smoke remains user acceptance — cost if wrong: campus isolation or client differences may prevent connection.
Final: Ruling: Vendor DLL/crash physical state — use SDK results with conservative uncertainty and explicit cleanup; no claim about DLL internal correctness or pattern persistence after process death — cost if wrong: physical state needs operator inspection.
Task8: Ruling: User permits vendorGUI closure and laser is off, with no image/exposure supplied — preserve CCD exposure, use explicitly marked newtest image after physical role confirmation, never claim recovery of the former MagicHolo pattern — cost if wrong: user must reload desired experimental pattern.
Task8: Ruling: Currentprobe now finds two identicalSLMs — stop SLM submission until physical role confirmation, CCD-only integration can proceed — cost if wrong: delays SLM integration but avoids illuminating the wrong panel.
