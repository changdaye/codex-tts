# codex-tts

`codex-tts` 是一个面向交互式 Codex CLI 的本地语音包装器。它不改 Codex 本体，而是在你用 `codex-tts` 启动 Codex 时，监听本地 rollout 数据，并在检测到 assistant 的最终回复后自动朗读出来。

当前版本的边界很明确：

- 只朗读最终回复，不朗读 `commentary`
- macOS 优先，默认通过系统 `say` 播放
- 基于本地 `~/.codex/state_5.sqlite` 和 rollout JSONL 做会话识别
- 语音失败不影响 Codex 主流程

## 功能

- 启动原生 `codex`，参数原样透传
- 解析本地 rollout JSONL 中的 `final_answer`
- 对最终回复做去重，避免重复播报
- 提供可插拔的 TTS 后端接口，当前内置 `say`

## 安装

建议在项目目录内使用虚拟环境：

```bash
cd /Users/changdaye/Downloads/codex-tts
python3 -m venv .venv
source .venv/bin/activate
pip3 install pytest
```

如果你后续准备把项目安装成命令行工具，再执行：

```bash
pip3 install -e .
```

## 使用

最常见的用法是直接把它当作 `codex` 包装器：

```bash
codex-tts -- --no-alt-screen
```

也可以在单次启动时直接覆盖语音参数：

```bash
codex-tts --speed 1.5 -- --no-alt-screen
codex-tts --rate 260 --voice Tingting -- --no-alt-screen
codex-tts --preset ultra -- --no-alt-screen
```

查看当前系统可用音色：

```bash
codex-tts --list-voices
```

也可以显式指定配置文件：

```bash
codex-tts --config ~/.codex-tts/config.toml -- --no-alt-screen
```

运行流程如下：

1. `codex-tts` 启动真实的 `codex`
2. 它轮询本地 Codex 状态库，找到当前活跃 thread
3. 根据 thread 的 `rollout_path` 读取 rollout JSONL
4. 遇到 assistant 的 `final_answer` 时调用 TTS 后端播放

### 启动参数

- `--voice`: 本次运行覆盖配置文件中的音色
- `--rate`: 本次运行直接指定绝对语速
- `--speed`: 本次运行按倍率调整当前配置语速，例如 `1.5`
- `--preset`: 本次运行使用语速预设，当前支持 `normal`、`fast`、`faster`、`ultra`
- `--list-voices`: 列出当前后端支持的系统音色并退出

`--rate`、`--speed` 和 `--preset` 不能同时使用；如果都不传，就沿用配置文件或默认值。

## 配置

默认配置文件位置：

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

当前字段说明：

- `backend`: 语音后端，当前支持 `say`
- `voice`: `say` 使用的系统音色
- `rate`: 语速
- `speak_phase`: 当前只支持 `final_only`

## 测试

在虚拟环境中运行：

```bash
source .venv/bin/activate
python -m pytest -v
```

## 当前限制

- 只支持 macOS `say`
- 只播报最终回复
- 多个并发 Codex 会话同时在同一目录运行时，不保证 100% 匹配准确
- 当前实现使用轮询，不是文件系统事件监听

## GitHub 发布

如果你要创建私有仓库并推送当前目录：

```bash
gh auth status
gh repo create codex-tts --private --source . --remote origin --push
```

确认远程后：

```bash
git remote -v
```

## 后续方向

- 增加 OpenAI / ElevenLabs / Edge TTS 后端
- 增加错误提示播报模式
- 优化多会话识别
- 评估 daemon 模式
