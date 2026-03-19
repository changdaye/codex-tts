# codex-tts

言語: [简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

`codex-tts` は、対話型 `codex` CLI 向けのローカル音声ラッパーです。`codex-tts` 経由で Codex を起動すると、ローカルの rollout データを監視し、assistant の新しい `final_answer` を自動で読み上げます。

## 何を解決するか

ターミナル中心で Codex を使っていると、よく次のような状況があります。

- Codex はすでに完了しているが、別のウィンドウを見ている
- 途中経過ではなく最終結果だけを知りたい
- Codex 本体は変更せずに音声通知だけ追加したい

`codex-tts` は、この用途だけに絞った薄いラッパーです。Codex を改造せず、外側に音声機能を足します。

## 現在の機能

- 読み上げ対象は最終返信のみで、`commentary` は読まない
- macOS を対象にし、既定ではシステムの `say` を使う
- 同じ Codex セッション内で新しい `final_answer` が出るたびに読み上げる
- 音声、絶対速度、倍率、速度プリセットを実行時に上書きできる
- 読み上げ前にテキストを整形し、URL は読まず、Markdown リンクはラベルだけを残す
- 音声再生に失敗しても Codex 本体の処理は止めない
- `--verbose` で thread 選択やスキップ理由の診断ログを stderr に出せる

## 動作要件

- macOS
- Python `3.11+`
- `codex` がインストール済みで `PATH` から実行できること
- macOS の `say` が利用できること
- ローカルの `~/.codex` 状態ファイルとセッションファイルにアクセスできること

## インストール

### 方法 1: グローバルコマンドとしてインストール

これが最もおすすめです。インストール後は、どのディレクトリからでも `codex-tts` を実行できます。

```bash
cd /path/to/codex-tts
bash scripts/bootstrap.sh
bash scripts/install.sh
```

インストーラは次の場所に launcher を作成します。

```text
~/.local/bin/codex-tts
```

まだ `~/.local/bin` が `PATH` に入っていなければ、追加してください。

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

インストール先を変更したい場合は、環境変数で指定できます。

```bash
CODEX_TTS_INSTALL_DIR="$HOME/bin" bash scripts/install.sh
```

インストーラはリポジトリ直下かどうかと `.venv/bin/python` の有無を確認します。環境がまだなら `bash scripts/bootstrap.sh` を先に実行するよう案内します。`codex` が `PATH` に無い場合も警告します。

### 方法 2: ソースから直接実行

グローバルコマンドをまだ入れたくない場合は、リポジトリから直接実行できます。

```bash
cd /path/to/codex-tts
bash scripts/bootstrap.sh
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --preset ultra -- --no-alt-screen
```

この方法では `PATH` の変更は不要ですが、リポジトリ前提で実行します。

### グローバル launcher のアンインストール

グローバルコマンドを不要にした場合は、次を実行します。

```bash
cd /path/to/codex-tts
bash scripts/uninstall.sh
```

このスクリプトは `~/.local/bin/codex-tts` だけを削除します。リポジトリ本体、`.venv`、設定ファイルは削除しません。

## クイックスタート

グローバルインストール済みなら、最短の起動方法は次です。

```bash
codex-tts --preset ultra -- --no-alt-screen
```

ソースから直接実行する場合は次です。

```bash
PYTHONPATH=src python -m codex_tts.cli --preset ultra -- --no-alt-screen
```

Codex が開いたら、まず短いテスト用プロンプトを送ってください。

```text
テスト成功 とだけ返してください
```

期待される挙動:

- 実行中の途中経過は読み上げない
- 最終回答が出たときだけ 1 回読む
- 同じセッション内の後続の最終回答も引き続き読む
- 返信内の URL は読み上げない

## よく使う例

基本起動:

```bash
codex-tts -- --no-alt-screen
```

音声を変えて速度プリセットを使う:

```bash
codex-tts --voice Tingting --preset faster -- --no-alt-screen
```

倍率で速度を変える:

```bash
codex-tts --speed 3 -- --no-alt-screen
```

絶対速度を直接指定する:

```bash
codex-tts --rate 540 -- --no-alt-screen
```

利用可能な音声一覧を見る:

```bash
codex-tts --list-voices
```

診断ログを出す:

```bash
codex-tts --verbose -- --no-alt-screen
```

設定ファイルを明示的に指定する:

```bash
codex-tts --config ~/.codex-tts/config.toml -- --no-alt-screen
```

補足:

- `--` より前は `codex-tts` 自身の引数です
- `--` より後ろはそのまま本物の `codex` に渡されます

## コマンド引数

| オプション | 型 | 説明 |
| --- | --- | --- |
| `--config` | `Path` | 設定ファイルのパス。既定値は `~/.codex-tts/config.toml` |
| `--voice` | `str` | 今回の実行だけ音声を上書きする |
| `--rate` | `int` | 今回の実行だけ絶対速度を指定する |
| `--speed` | `float` | 現在の速度に倍率をかける。例: `3` |
| `--preset` | `str` | 名前付き速度プリセットを使う |
| `--list-voices` | flag | 利用可能な音声一覧を表示して終了する |
| `--verbose` | flag | thread 選択やスキップ理由を stderr に出力する |

ルール:

- `--rate`、`--speed`、`--preset` は同時に使えません
- どれも指定しない場合は設定ファイルの値を使います
- `--voice` は `--rate`、`--speed`、`--preset` と組み合わせ可能です

## 速度プリセット

| プリセット | 最終速度 |
| --- | --- |
| `normal` | `180` |
| `fast` | `270` |
| `faster` | `360` |
| `ultra` | `540` |

必要な速度が決まっているなら、`--rate` を直接使ってもかまいません。

## 設定ファイル

既定の設定ファイルパス:

```text
~/.codex-tts/config.toml
```

例:

```toml
backend = "say"
voice = "Tingting"
rate = 180
speak_phase = "final_only"
verbose = false
```

項目:

| 項目 | 既定値 | 説明 |
| --- | --- | --- |
| `backend` | `"say"` | 音声バックエンド。現時点では macOS `say` のみ |
| `voice` | `"Tingting"` | 既定の音声 |
| `rate` | `180` | 既定の読み上げ速度 |
| `speak_phase` | `"final_only"` | 現時点では最終回答のみ読み上げ対応 |
| `verbose` | `false` | stderr に診断ログを出すかどうか |

検証ルール:

- `backend` は現在 `say` のみ
- `rate` は `0` より大きい必要がある
- `voice` は前後の空白を除去した後に空であってはいけない
- `speak_phase` は現在 `final_only` のみ
- `verbose` は真偽値である必要がある

優先順位:

1. CLI 引数
2. 設定ファイル
3. 内蔵デフォルト

## 仕組み

実行フローは次のとおりです。

1. 本物の `codex` を起動する
2. 作業ディレクトリと起動時刻を記録する
3. `~/.codex/state_5.sqlite` から新しい thread を見つける
4. その thread の rollout JSONL を継続監視する
5. 新しい assistant `final_answer` を検出したら読み上げる

ターミナルの ANSI 出力を解析するのではなく、Codex 自身の構造化セッションデータを直接読みます。

## 読み上げ前のテキスト整形

TTS に渡す前に、次の軽い整形を行います。

- 生の URL は削除する
- Markdown リンクは `[ラベル](url)` から `ラベル` だけを残す
- 余分な空白や空行を圧縮する
- 整形後に読む内容が残らなければ、何も読み上げない

これは音声出力だけに適用され、ターミナル表示は変わりません。

## 現在の制限

- macOS `say` のみ対応
- 最終回答のみ。エラーや途中状態は読み上げない
- 同じディレクトリで複数の Codex セッションを並行実行すると、完全一致は保証しない
- 実装はポーリングベースで、ファイルシステムイベント監視ではない

## トラブルシューティング

### 音が出ない

まず macOS の音声機能自体を確認します。

```bash
say "テスト成功"
```

これで音が出ない場合は、次を確認してください。

- システム音量
- 現在の出力デバイス
- macOS の音声機能がこのプロジェクト外でも正常か

### コマンドが見つからない

ソースから実行するなら、次を使ってください。

```bash
PYTHONPATH=src python -m codex_tts.cli --help
```

グローバルインストール済みなら、次を確認してください。

- `bash scripts/install.sh` を実行したか
- `~/.local/bin` が `PATH` に入っているか
- `source ~/.zshrc` などで shell 設定を再読み込みしたか

### Codex は返信しているのに読み上げない

まず次を確認してください。

- `codex-tts` 経由で起動したか。素の `codex` ではないか
- その返信が `commentary` ではなく最終段階に到達しているか
- 同じディレクトリで無関係な Codex セッションを複数同時に動かしていないか

それでも原因が見えない場合は、`--verbose` を付けて再実行してください。

```bash
codex-tts --verbose -- --no-alt-screen
```

thread 候補の選択、rollout の監視開始、整形後に空になったため未読み上げになったケースなどを stderr に出します。

### 利用可能な音声を見たい

```bash
codex-tts --list-voices
```

## 開発とテスト

全テストを実行:

```bash
bash scripts/bootstrap.sh
source .venv/bin/activate
python -m pytest -q
```

CLI ヘルプを確認:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --help
```

インストーラスクリプトだけをテスト:

```bash
source .venv/bin/activate
python -m pytest tests/test_install_script.py -q
```

CI メモ:

- GitHub Actions は push と pull request ごとに `python -m pytest -q` を実行します
- 変更を渡す前にローカルでも全テストを回すのが安全です

## 今後の予定

- OpenAI / ElevenLabs / Edge TTS バックエンド追加
- エラー通知の読み上げ追加
- 複数セッション識別の改善
- daemon モードの検討
