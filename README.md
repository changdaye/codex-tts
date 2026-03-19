# codex-tts

语言: [简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

`codex-tts` 是一个面向交互式 `codex` CLI 的本地语音包装器。你通过它启动 `codex` 之后，它会监听本地 Codex 会话的 rollout 数据，并在 assistant 产生新的 `final_answer` 时自动朗读出来。

## 它解决什么问题

如果你平时主要在终端里用 Codex，经常会遇到这几个问题：

- Codex 已经给出最终答案，但你正在看别的窗口
- 你只关心最终结果，不想听中间执行过程
- 你想保留原来的 Codex 使用方式，而不是改 Codex 本体

`codex-tts` 的思路很直接：不改 Codex，只在外层包一层本地语音能力。

## 当前能力

- 只朗读最终回复，不朗读 `commentary`
- 以 macOS 为目标平台，默认通过系统 `say` 播放
- 同一场 Codex 会话中的每条新 `final_answer` 都会继续朗读
- 支持运行时覆盖音色、绝对语速、倍率和语速预设
- 播报前会自动清洗文本，不朗读裸 URL，Markdown 链接只保留标题
- 语音失败不会中断 Codex 主流程

## 环境要求

- macOS
- Python `3.11+`
- `codex` 已安装并且在 `PATH` 中可直接运行
- 系统自带 `say` 可用
- 当前用户可访问本地 `~/.codex` 状态库和会话文件

## 安装

### 方案 1：安装为全局命令

这是最推荐的方式。安装完成后，你可以在任意目录直接运行 `codex-tts`。

```bash
cd /path/to/codex-tts
python3 -m venv .venv
bash scripts/install.sh
```

安装脚本会把 launcher 写到默认目录：

```text
~/.local/bin/codex-tts
```

如果你的 shell 还没有把 `~/.local/bin` 放进 `PATH`，加入这一行：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

安装脚本支持自定义安装目录。如果你不想装到 `~/.local/bin`，可以这样：

```bash
CODEX_TTS_INSTALL_DIR="$HOME/bin" bash scripts/install.sh
```

### 方案 2：直接从源码运行

如果你暂时不想安装全局命令，可以直接在仓库里启动：

```bash
cd /path/to/codex-tts
python3 -m venv .venv
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --preset ultra -- --no-alt-screen
```

这种方式不依赖 `PATH`，但需要你在仓库目录里运行。

### 卸载全局命令

如果你之后不想继续把 `codex-tts` 暴露为全局命令：

```bash
cd /path/to/codex-tts
bash scripts/uninstall.sh
```

这个脚本只会删除 `~/.local/bin/codex-tts` 这个 launcher，不会删除仓库目录、`.venv` 或配置文件。

## 快速开始

如果你已经完成了全局安装，最直接的启动方式是：

```bash
codex-tts --preset ultra -- --no-alt-screen
```

如果你是从源码直接运行，对应命令是：

```bash
PYTHONPATH=src python -m codex_tts.cli --preset ultra -- --no-alt-screen
```

进入 Codex 之后，可以先发一个很短的测试请求，例如：

```text
请只回复：测试成功
```

正常行为应该是：

- 中间执行过程不朗读
- 最终回复出来时朗读一次
- 同一个会话里后续新的最终回复也会继续朗读
- 如果回复里带 URL，URL 不会被读出来

## 常见用法

基础启动：

```bash
codex-tts -- --no-alt-screen
```

切换音色并使用语速预设：

```bash
codex-tts --voice Tingting --preset faster -- --no-alt-screen
```

按倍率调整语速：

```bash
codex-tts --speed 3 -- --no-alt-screen
```

直接指定绝对语速：

```bash
codex-tts --rate 540 -- --no-alt-screen
```

查看当前系统可用音色：

```bash
codex-tts --list-voices
```

显式指定配置文件：

```bash
codex-tts --config ~/.codex-tts/config.toml -- --no-alt-screen
```

说明：

- `--` 前面是 `codex-tts` 自己的参数
- `--` 后面会原样透传给真实的 `codex`

## 参数说明

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `--config` | `Path` | 配置文件路径，默认是 `~/.codex-tts/config.toml` |
| `--voice` | `str` | 本次运行覆盖配置文件里的音色 |
| `--rate` | `int` | 本次运行直接指定绝对语速 |
| `--speed` | `float` | 本次运行按倍率调整当前语速，例如 `3` |
| `--preset` | `str` | 本次运行使用内置语速预设 |
| `--list-voices` | flag | 列出当前后端支持的系统音色并退出 |

需要注意的规则：

- `--rate`、`--speed`、`--preset` 三者互斥，一次只能选一个
- 如果你不传这些覆盖参数，就沿用配置文件中的值
- `--voice` 可以和 `--rate`、`--speed`、`--preset` 组合使用

## 语速预设

| 预设 | 最终语速 |
| --- | --- |
| `normal` | `180` |
| `fast` | `270` |
| `faster` | `360` |
| `ultra` | `540` |

如果你已经知道自己要多少语速，也可以跳过预设，直接用 `--rate`。

## 配置文件

默认配置文件路径：

```text
~/.codex-tts/config.toml
```

示例：

```toml
backend = "say"
voice = "Tingting"
rate = 180
speak_phase = "final_only"
```

字段说明：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `backend` | `"say"` | 语音后端，当前只支持 macOS `say` |
| `voice` | `"Tingting"` | 默认音色 |
| `rate` | `180` | 默认语速 |
| `speak_phase` | `"final_only"` | 当前只支持最终回复播报 |

优先级规则：

1. 启动参数优先级最高
2. 配置文件次之
3. 内置默认值最低

## 工作原理

`codex-tts` 的主流程是：

1. 启动真实的 `codex`
2. 记录当前工作目录和启动时间
3. 在 `~/.codex/state_5.sqlite` 里找到这次新开的 thread
4. 根据 thread 的 `rollout_path` 持续读取 rollout JSONL
5. 每当发现新的 assistant `final_answer`，就调用 TTS 后端播放

它不会去解析终端界面的 ANSI 文本，而是直接读取 Codex 自己的结构化会话数据。

## 播报文本清洗规则

在真正调用 TTS 之前，还会做一层轻量清洗：

- 裸 URL 会被移除
- Markdown 链接会从 `[标题](url)` 变成只读 `标题`
- 清洗后产生的多余空白和空行会被压缩
- 如果清洗后只剩空内容，就不会朗读

这层清洗只影响语音播报，不影响你在终端里看到的原始文本。

## 当前限制

- 当前只支持 macOS `say`
- 当前只播报最终回复，不播报错误或中间状态
- 多个 Codex 会话同时在同一目录并发运行时，不保证 100% 匹配准确
- 当前实现使用轮询，不是文件系统事件监听

## 排障

### 没有声音

先直接测试系统语音本身：

```bash
say "测试成功"
```

如果这句都没有声音，先检查：

- 系统音量
- 当前输出设备
- macOS 的语音功能本身是否正常

### 命令找不到

如果你是源码运行方式，就直接使用：

```bash
PYTHONPATH=src python -m codex_tts.cli --help
```

如果你是全局安装方式，确认：

- 你执行过 `bash scripts/install.sh`
- `~/.local/bin` 已经加入 `PATH`
- 当前 shell 已经重新加载过配置，例如 `source ~/.zshrc`

### Codex 有回复，但没有朗读

确认下面几件事：

- 你是通过 `codex-tts` 启动的，而不是直接运行 `codex`
- 这条回复已经进入最终阶段，而不是还停留在 `commentary`
- 尽量避免在同一目录同时跑多个独立 Codex 会话

### 想看可用音色

```bash
codex-tts --list-voices
```

## 开发与测试

运行测试：

```bash
source .venv/bin/activate
python -m pytest -q
```

查看 CLI 帮助：

```bash
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --help
```

测试安装脚本：

```bash
source .venv/bin/activate
python -m pytest tests/test_install_script.py -q
```

## 后续方向

- 增加 OpenAI / ElevenLabs / Edge TTS 后端
- 增加错误提示播报模式
- 优化多会话识别
- 评估 daemon 模式
