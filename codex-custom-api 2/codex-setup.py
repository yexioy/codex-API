#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
codex-setup —— 一键为 Codex 配置自定义 API（中转 / 聚合 / 自建网关）

它会保留你 ~/.codex/config.toml 里现有的所有内容（插件、computer-use、MCP 等），
只新增 / 更新自定义 provider 部分，并先自动备份。

用法
----
交互式（新手推荐，跑起来按提示填三样东西即可）：
    python3 codex-setup.py

命令行（适合脚本化 / 批量）：
    python3 codex-setup.py \
        --base-url https://你的中转/v1 \
        --key sk-xxxx \
        --model gpt-5.4

常用可选项：
    --name "My Relay"        provider 显示名（默认用 id）
    --id   myrelay           provider id（config 里 [model_providers.<id>] 的名字）
    --wire-api chat|responses 协议，默认 responses；中转多为 chat（见文末说明）
    --profile <name>         不改全局，改成一个可切换的 profile（保护 App 原有功能）
    --env-key                key 用环境变量注入而非写进文件（更安全，但 App 可能读不到）
    --reasoning xhigh        推理强度 minimal/low/medium/high/xhigh
    --no-test                跳过连通性测试
"""

import argparse
import datetime as _dt
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Windows / 旧终端编码兜底：强制 UTF-8 输出，避免打印 ✓ ⚠ 等符号时闪退
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


# ---------- 依赖自检：缺 tomlkit 就自动装 ----------
def _ensure_tomlkit():
    try:
        import tomlkit  # noqa
        return
    except ImportError:
        pass
    print("· 缺少依赖 tomlkit，正在自动安装 ...")
    for cmd in (
        [sys.executable, "-m", "pip", "install", "tomlkit", "-q"],
        [sys.executable, "-m", "pip", "install", "tomlkit", "-q", "--break-system-packages"],
        [sys.executable, "-m", "pip", "install", "tomlkit", "-q", "--user"],
    ):
        try:
            subprocess.check_call(cmd)
            return
        except subprocess.CalledProcessError:
            continue
    sys.exit("✗ 无法自动安装 tomlkit，请手动运行: pip install tomlkit")


_ensure_tomlkit()
import tomlkit  # noqa: E402


# ---------- 小工具 ----------
def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    while True:
        val = input(f"{prompt}{hint}: ").strip()
        if val:
            return val
        if default:
            return default
        print("  这个不能为空，请重新输入。")


def normalize_base_url(url: str, assume_yes: bool = False) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        print(f"  ⚠ base_url 没有 http(s) 前缀，已自动补成 https://{url}")
        url = "https://" + url
    if not url.endswith("/v1"):
        if assume_yes:
            url = url + "/v1"
            print(f"  ⚠ base_url 末尾缺 /v1，已自动补上 -> {url}")
        else:
            print(f"  ⚠ base_url 末尾通常需要 /v1，当前为: {url}")
            if input("  是否自动补上 /v1？(Y/n): ").strip().lower() in ("", "y", "yes"):
                url = url + "/v1"
    return url


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = path.parent / (path.name + f".bak.{ts}")
    shutil.copy2(path, bak)
    return bak


def test_endpoint(base_url: str, api_key: str) -> None:
    """尽力而为地探测 /models，失败不影响配置，仅作提示。"""
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            ok = 200 <= r.status < 300
            print(f"  · 连通性测试 GET {url} -> {r.status} {'✓' if ok else ''}")
    except urllib.error.HTTPError as e:
        # 401/403 说明能连通但 key/权限有问题；404 说明该端点没暴露 /models，都不致命
        print(f"  · 连通性测试 -> HTTP {e.code}（能连上服务器，"
              f"{'但 key 可能无效' if e.code in (401, 403) else '该网关未暴露 /models，可忽略'}）")
    except Exception as e:  # noqa: BLE001
        print(f"  · 连通性测试失败：{e}（不影响写入，启动 Codex 时再看实际报错）")


def setup_env_var(name: str, value: str) -> None:
    """--env-key 模式：尽量帮用户把环境变量持久化。"""
    system = platform.system()
    if system == "Windows":
        try:
            subprocess.check_call(["setx", name, value],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  · 已用 setx 写入用户环境变量 {name}（对【新开】的终端 / App 生效）")
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ setx 失败：{e}，请手动设置环境变量 {name}")
        return
    # macOS / Linux
    shell = os.environ.get("SHELL", "")
    rc = Path.home() / (".zshrc" if "zsh" in shell else ".bashrc")
    line = f'\nexport {name}="{value}"\n'
    try:
        existing = rc.read_text(encoding="utf-8") if rc.exists() else ""
        if f"export {name}=" not in existing:
            with rc.open("a", encoding="utf-8") as f:
                f.write(line)
            print(f"  · 已把 export {name} 追加到 {rc}")
        else:
            print(f"  · {rc} 里已有 {name}，未重复写入（如需更新请手动改）")
        print(f"  → 让它生效：source {rc} 或重开终端")
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ 写入 {rc} 失败：{e}，请手动添加: export {name}=\"<你的key>\"")
    if system == "Darwin":
        print("  ⚠ 注意：从 Dock/启动台 打开的 Codex App 读不到 ~/.zshrc 里的环境变量。"
              "若用 App 建议改用默认的写入文件模式（去掉 --env-key）。")


# ---------- 主流程 ----------
def main() -> None:
    p = argparse.ArgumentParser(add_help=True, description="一键配置 Codex 自定义 API")
    p.add_argument("--base-url")
    p.add_argument("--key")
    p.add_argument("--model")
    p.add_argument("--name")
    p.add_argument("--id")
    p.add_argument("--wire-api", choices=["chat", "responses"])
    p.add_argument("--profile")
    p.add_argument("--reasoning")
    p.add_argument("--env-key", action="store_true")
    p.add_argument("--no-test", action="store_true")
    a = p.parse_args()

    interactive = not (a.base_url and a.key and a.model)
    if interactive:
        print("=" * 56)
        print(" Codex 自定义 API 一键配置")
        print("=" * 56)

    base_url = normalize_base_url(
        a.base_url or ask("中转 / API 的 Base URL（例: https://xxx/v1）"),
        assume_yes=bool(a.base_url),
    )
    api_key = a.key or ask("API Key（sk- 开头那一串）")
    model = a.model or ask("模型名（中转里实际可用的名字，例: gpt-5.4）")
    pid = a.id or (a.profile or "myrelay")
    pid = pid.replace(" ", "_")
    name = a.name or pid
    reasoning = a.reasoning  # None 则不写

    if a.wire_api:
        wire = a.wire_api
    elif interactive:
        print("\n协议 wire_api：")
        print("  1) responses  —— 新版 Codex 默认/常常强制要求（推荐先试这个）")
        print("  2) chat       —— 多数中转/聚合站只支持这个；若你的网关没做 Responses 转换就选它")
        wire = "chat" if ask("选 1 或 2", "1") == "2" else "responses"
    else:
        wire = "responses"

    use_inline_key = not a.env_key
    env_key_name = (pid.upper() + "_API_KEY").replace("-", "_")

    # 读取 / 新建 config.toml
    home = codex_home()
    home.mkdir(parents=True, exist_ok=True)
    cfg = home / "config.toml"
    bak = backup(cfg)
    doc = tomlkit.parse(cfg.read_text(encoding="utf-8")) if cfg.exists() else tomlkit.document()

    # provider 块
    prov = tomlkit.table()
    prov["name"] = name
    prov["base_url"] = base_url
    prov["wire_api"] = wire
    prov["requires_openai_auth"] = False
    if use_inline_key:
        prov["api_key"] = api_key
    else:
        prov["env_key"] = env_key_name
    prov["request_max_retries"] = 4
    prov["stream_max_retries"] = 10
    prov["stream_idle_timeout_ms"] = 300000

    if "model_providers" not in doc:
        doc["model_providers"] = tomlkit.table()
    doc["model_providers"][pid] = prov

    if a.profile:
        # profile 模式：不动全局 model_provider，App 原有功能不受影响
        if "profiles" not in doc:
            doc["profiles"] = tomlkit.table()
        prof = tomlkit.table()
        prof["model_provider"] = pid
        prof["model"] = model
        if reasoning:
            prof["model_reasoning_effort"] = reasoning
        doc["profiles"][a.profile] = prof
    else:
        # 全局模式
        doc["model"] = model
        doc["model_provider"] = pid
        if reasoning:
            doc["model_reasoning_effort"] = reasoning

    cfg.write_text(tomlkit.dumps(doc), encoding="utf-8")
    if use_inline_key:
        try:
            os.chmod(cfg, 0o600)  # key 在文件里，收紧权限
        except Exception:  # noqa: BLE001
            pass

    if not use_inline_key:
        setup_env_var(env_key_name, api_key)

    if not a.no_test:
        test_endpoint(base_url, api_key)

    # 总结
    print("\n" + "=" * 56)
    print("✓ 配置完成")
    print("=" * 56)
    if bak:
        print(f"  备份      : {bak}")
    print(f"  配置文件  : {cfg}")
    print(f"  provider  : [model_providers.{pid}]  base_url={base_url}  wire_api={wire}")
    if a.profile:
        print(f"  profile   : {a.profile}（CLI 用 `codex --profile {a.profile}` 启动；App 在界面里选）")
    else:
        print(f"  默认模型  : {model}（已设为全局默认）")
    print(f"  key 方式  : {'写入文件(已 chmod 600)' if use_inline_key else f'环境变量 {env_key_name}'}")
    print("\n下一步：完全退出 Codex（App 要彻底退出，不是关窗口）再重开。")
    if wire == "chat":
        print("提示：若启动后立刻 404 / 空流，多半是新版 Codex 只认 responses。"
              "请在网关侧加 ChatCompletions→Responses 转换后改成 responses，或换用支持 chat 的旧版 CLI。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消。")
