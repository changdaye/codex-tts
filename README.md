# codex-tts

`codex-tts` 是一个面向交互式 `codex` CLI 的本地语音包装器。你通过它启动 `codex` 之后，它会监听本地 Codex 会话的 rollout 数据，并在 assistant 产生新的 `final_answer` 时自动朗读出来。

当前版本的边界很明确：

- 只朗读最终回复，不朗读 `commentary`
- 以 macOS 为目标平台，默认通过系统 `say` 播放
- 启动参数可以覆盖音色、语速、倍率和语速预设
- 同一场 Codex 会话中的每条新 `final_answer` 都会继续朗读
- 播报前会自动清洗文本，不朗读裸 URL，Markdown 链接只保留标题
- 语音失败不会中断 Codex 主流程

## 适用场景

- 你平时主要用交互式 `codex`，希望最终答案自动播报
- 你想保留原来的 Codex 使用方式，只在外层加一层本地语音能力
- 你只关心最终结果，不想听中间执行过程

## 环境要求

- macOS
- Python `3.11+`
- `codex` 已安装并且在 `PATH` 中可直接运行
- 系统自带 `say` 可用
- 当前用户可访问本地 `~/.codex` 状态和会话文件

## 快速开始

如果你是直接从源码目录运行，先创建虚拟环境：

```bash
cd /path/to/codex-tts
python3 -m venv .venv
source .venv/bin/activate
```

最稳的启动方式是直接从源码运行：

```bash
PYTHONPATH=src python -m codex_tts.cli --preset ultra -- --no-alt-screen
```

如果你已经把命令入口装进当前虚拟环境，也可以直接：

```bash
codex-tts --preset ultra -- --no-alt-screen
```

进入 Codex 后，发一个很短的测试问题，例如：

```text
请只回复：测试成功
```

正常行为是：

- 中间执行过程不朗读
- 最终回复出来时朗读一次
- 同一个会话里后续新的最终回复也会继续朗读
- 回复里的 URL 不会被读出来

## 使用示例

基础启动：

```bash
PYTHONPATH=src python -m codex_tts.cli -- --no-alt-screen
```

切换音色并使用预设语速：

```bash
PYTHONPATH=src python -m codex_tts.cli --voice Tingting --preset faster -- --no-alt-screen
```

按倍率调整语速：

```bash
PYTHONPATH=src python -m codex_tts.cli --speed 3 -- --no-alt-screen
```

直接指定绝对语速：

```bash
PYTHONPATH=src python -m codex_tts.cli --rate 540 -- --no-alt-screen
```

查看当前系统可用音色：

```bash
PYTHONPATH=src python -m codex_tts.cli --list-voices
```

显式指定配置文件：

```bash
PYTHONPATH=src python -m codex_tts.cli --config ~/.codex-tts/config.toml -- --no-alt-screen
```

`--` 前面是 `codex-tts` 自己的参数，`--` 后面会原样透传给真实的 `codex`。

## 启动参数

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `--config` | `Path` | 配置文件路径，默认是 `~/.codex-tts/config.toml` |
| `--voice` | `str` | 本次运行覆盖配置文件里的音色 |
| `--rate` | `int` | 本次运行直接指定绝对语速 |
| `--speed` | `float` | 本次运行按倍率调整当前语速，例如 `3` |
| `--preset` | `str` | 本次运行使用内置语速预设 |
| `--list-voices` | flag | 列出当前后端支持的系统音色并退出 |

注意：

- `--rate`、`--speed`、`--preset` 三者互斥，一次只能选一个
- 如果不传这些覆盖参数，就沿用配置文件中的值
- `--voice` 可以和 `--rate`、`--speed`、`--preset` 组合使用

## 语速预设

| 预设 | 最终语速 |
| --- | --- |
| `normal` | `180` |
| `fast` | `270` |
| `faster` | `360` |
| `ultra` | `540` |

如果你已经知道自己想要固定速度，也可以不用预设，直接传 `--rate`。

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

配置字段：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `backend` | `"say"` | 语音后端，当前只支持 macOS `say` |
| `voice` | `"Tingting"` | 默认音色 |
| `rate` | `180` | 默认语速 |
| `speak_phase` | `"final_only"` | 当前只支持最终回复播报 |

优先级规则：

- 启动参数优先级高于配置文件
- 配置文件优先级高于内置默认值

## 工作原理

`codex-tts` 的主流程是：

1. 启动真实的 `codex`
2. 记录当前工作目录和启动时间
3. 在 `~/.codex/state_5.sqlite` 里找到这次新开的 thread
4. 根据 thread 的 `rollout_path` 持续读取 rollout JSONL
5. 每当发现新的 assistant `final_answer`，就调用 TTS 后端播放

它不会去解析终端界面的 ANSI 文本，而是直接读取 Codex 自己的结构化会话数据。

在真正调用 TTS 之前，还会做一层轻量清洗：

- 裸 URL 会被移除
- Markdown 链接会从 `[标题](url)` 变成只读 `标题`
- 清洗后产生的多余空白和空行会被压缩

## 限制

- 当前只支持 macOS `say`
- 当前只播报最终回复，不播报错误或中间状态
- 多个 Codex 会话同时在同一目录并发运行时，不保证 100% 匹配准确
- 当前实现使用轮询，不是文件系统事件监听

## 排障

没有声音：

```bash
say "测试成功"
```

如果这句都没有声音，先检查系统音量、输出设备和 macOS 语音本身。

不知道系统有哪些音色：

```bash
PYTHONPATH=src python -m codex_tts.cli --list-voices
```

命令找不到：

- 先确认你已经 `source .venv/bin/activate`
- 如果没有安装命令入口，就直接用 `PYTHONPATH=src python -m codex_tts.cli`

Codex 有回复但没有朗读：

- 确认你是通过 `codex-tts` 启动的，而不是直接运行 `codex`
- 确认这条回复已经进入最终阶段，而不是还停留在 `commentary`
- 尽量避免在同一目录同时跑多个独立 Codex 会话

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

## 后续方向

- 增加 OpenAI / ElevenLabs / Edge TTS 后端
- 增加错误提示播报模式
- 优化多会话识别
- 评估 daemon 模式
