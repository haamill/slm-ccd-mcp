# 验收建议清单

本文档用于通用验收，不绑定任何特定实验现场。

## A. 模拟模式（必做）

1. 启动服务：

   ```bash
   python -m lab_mcp serve --config config/simulation.toml --mode simulate
   ```

2. 使用 MCP 客户端执行：
   - `lab_status`
   - `lab_connect`
   - `asset_upload_begin/chunk/finish`
   - `slm_load_image`
   - `ccd_set_settings`
   - `ccd_capture`
3. 校验返回：
   - 有效 `capture_id`
   - `preview.png` 可读取
   - RAW 下载 SHA256 与 manifest 一致

## B. 本机 CLI 冒烟

```bash
python -m lab_mcp smoke --url http://127.0.0.1:8765/mcp
```

硬件模式冒烟必须显式附加：

```bash
python -m lab_mcp smoke --url http://<HOST>:<PORT>/mcp --allow-hardware --image <IMAGE_PATH> --exposure-us <US>
```

## C. 硬件模式（按需）

1. 先 `probe` 并确认绑定信息。
2. 在客户端执行最小闭环：
   - `lab_connect`
   - `slm_load_image`
   - `ccd_get_settings` / `ccd_set_settings`
   - `ccd_capture`
3. 确认：
   - 采图结果包含 manifest 与可下载 RAW
   - 设备参数读回与请求一致（在允许范围内）
   - 失败场景返回结构化错误，而不是静默成功

## D. 跨机验收（局域网）

1. 客户端与服务端使用一致 token。
2. 客户端能访问 `http://<HOST>:<PORT>/mcp`。
3. 完成一次采图并成功下载 RAW。
4. 校验下载哈希与 manifest 一致。

## E. 失败与恢复验证

- 对写操作传入 `operation_id`，断线后使用 `operation_get` 恢复结果。
- 验证非法路径、错误 token、越界参数等都被正确拒绝。
