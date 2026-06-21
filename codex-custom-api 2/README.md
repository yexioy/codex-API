# Codex 自定义 API 一键配置

把 Codex 接到你的中转 / 聚合 / 自建 API。会**保留**你 `config.toml` 里现有的所有配置（插件、computer-use、MCP 等），只新增/更新自定义 provider，并自动备份。

## 唯一前置条件：装好 Python 3

- Windows：到 https://www.python.org/downloads/ 下载安装，**安装时务必勾选 “Add python.exe to PATH”**。
- Mac：通常自带；没有就 `brew install python` 或去官网下载。

（脚本依赖的 `tomlkit` 会在首次运行时自动安装，无需手动处理。）

## 怎么用

### 方式一：双击（最简单）

- **Windows**：双击 `配置Codex-Windows.bat`
- **Mac**：双击 `配置Codex-Mac.command`
  （若双击没反应，先在终端跑一次：`chmod +x "配置Codex-Mac.command"`）

然后按提示依次填 **Base URL、API Key、模型名**，再选一下协议即可。

### 方式二：命令行

```bash
# Mac / Linux
python3 codex-setup.py --base-url https://你的中转/v1 --key sk-xxx --model gpt-5.4

# Windows
py codex-setup.py --base-url https://你的中转/v1 --key sk-xxx --model gpt-5.4
```

不带参数运行则进入交互式问答模式。

## 几个有用的选项

| 选项 | 作用 |
|---|---|
| `--profile <名字>` | 不改全局，建一个可切换的 profile（保护 Codex App 原有功能），用 `codex --profile <名字>` 启动 |
| `--wire-api chat\|responses` | 通信协议。多数中转只支持 `chat`；新版 Codex 常要求 `responses`（默认） |
| `--env-key` | key 改用环境变量注入（更安全，但桌面 App 可能读不到） |
| `--id <id>` / `--name <名>` | 自定义 provider 的标识与显示名 |
| `--reasoning xhigh` | 推理强度 minimal/low/medium/high/xhigh |
| `--no-test` | 跳过连通性测试 |

## 常见问题

- **启动后立刻 404 / 空流**：多半是新版 Codex 只认 `responses`，而你的中转只给 `chat`。解决：在网关侧加 ChatCompletions→Responses 转换后用 `responses`，或换用支持 `chat` 的旧版 Codex CLI。
- **改完不生效**：要**完全退出** Codex 再重开（App 是彻底退出，不是关窗口）。
- **配置写哪了**：`~/.codex/config.toml`（Windows 是 `C:\Users\你\.codex\config.toml`）。每次运行前都会自动备份成 `config.toml.bak.<时间戳>`。
- **想还原**：把备份文件改回 `config.toml` 即可。

## 贡献

欢迎提 Issue / PR：新增更多中转适配、wire_api 自动探测、纯批处理免 Python 版本等。

## 许可证

[MIT](LICENSE) © yexioy
