# SLM / CCD MCP

[中文说明](README.md)

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-6A5ACD)](https://modelcontextprotocol.io/)
[![GitHub Issues](https://img.shields.io/github/issues/haamill/slm-ccd-mcp)](https://github.com/haamill/slm-ccd-mcp/issues)

This project enables remote control of an SLM and CCD on a laboratory computer over a local network through [MCP (Model Context Protocol)](https://modelcontextprotocol.io/). It supports simulation mode (without hardware) and hardware mode (Windows + vendor SDKs).

## Features

- Streamable HTTP MCP service at [`/mcp`](https://github.com/haamill/slm-ccd-mcp)
- SLM image upload, loading, offset adjustment, grating control, and image restoration
- CCD settings read/write and RAW capture with preview and download support
- Combined `lab_load_and_capture` operation for sequential loading and capture in one request
- Operation deduplication with `operation_id` and result recovery through `operation_get`
- Token authentication, Host/Origin validation, and restricted file access

## Requirements

- [Python 3.12+](https://www.python.org/downloads/)
- Dependencies listed in [`pyproject.toml`](pyproject.toml) and [`requirements.lock.txt`](requirements.lock.txt)
- Additional requirements for hardware mode:
  - Windows x64
  - HDSLM / ToupCam SDKs installed
  - An interactive desktop session because the SLM window requires a message pump

## Installation

```bash
python -m venv .venv
. .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.lock.txt
pip install -e .
```

For development and testing, install the optional development dependencies:

```bash
pip install -e ".[dev]"
```

## Configuration

- Simulation mode: [`config/simulation.toml`](config/simulation.toml)
- Hardware example: [`config/hardware.example.toml`](config/hardware.example.toml)
- Client templates: [`client_examples/`](client_examples/)

Provide the access token through an environment variable, `LAB_MCP_TOKEN` by default:

```bash
python -m lab_mcp init-token --output config/local.token
```

Inject the token into the service and client process environments.

## Running the Service

### Simulation mode

```bash
python -m lab_mcp serve --config config/simulation.toml --mode simulate
```

### Hardware mode

```bash
python -m lab_mcp serve --config config/local.toml --mode hardware
```

You can also use [`scripts/start-lab-mcp.ps1`](scripts/start-lab-mcp.ps1):

```powershell
.\\scripts\\start-lab-mcp.ps1 -ConfigPath config/local.toml
```

## Device Discovery and Binding

In hardware mode, run device discovery first:

```bash
python -m lab_mcp probe --config config/local.toml
```

The result is written to [`runtime/probe.json`](runtime/probe.json). If device models or serial numbers are not unique, complete the binding using display position, panel dimensions, and role constraints.

## MCP Clients

- [Codex configuration example](client_examples/codex.config.toml)
- [Claude Desktop configuration example](client_examples/claude.desktop.json)

Replace the example URL, hostname, and authentication header values with those for your environment.

## Tool List

- Status and connection: `lab_status`, `lab_connect`, `lab_disconnect`
- Assets: `asset_list`, `asset_upload_begin`, `asset_upload_chunk`, `asset_upload_finish`
- SLM: `slm_load_image`, `slm_set_offset`, `slm_set_grating`, `slm_make_amplitude_grating`, `slm_show_uniform`, `slm_restore`
- CCD: `ccd_get_settings`, `ccd_set_settings`, `ccd_capture`
- Combined operation and recovery: `lab_load_and_capture`, `operation_get`

## Testing

```bash
pytest -q
```

CLI smoke test:

```bash
python -m lab_mcp smoke --url http://127.0.0.1:8765/mcp
```

> Hardware smoke tests require the explicit `--allow-hardware --image --exposure-us` options.

## Project Structure

```text
slm-ccd-mcp/
├── src/lab_mcp/          # Core implementation
├── tests/                # Tests
├── config/               # Configuration examples
├── client_examples/      # Client configuration templates
├── scripts/              # PowerShell helper scripts
├── docs/                 # Operation and acceptance documentation
├── pyproject.toml
└── requirements.lock.txt
```

## Security and Limitations

- A valid access credential is required.
- Host/Origin validation is enabled to reduce cross-origin abuse.
- Arbitrary shell execution and arbitrary-path file access are not provided.
- `runtime/` may contain captured results and run records and should generally be treated as local runtime data.
- The service does not guarantee optical results automatically; validate actual results independently on the experimental side.

## Contributing and License

Bug reports and improvement suggestions are welcome through [Issues](https://github.com/haamill/slm-ccd-mcp/issues) or [Pull Requests](https://github.com/haamill/slm-ccd-mcp/pulls).

This repository currently does not include a `LICENSE` file. Confirm the licensing terms before reuse.
