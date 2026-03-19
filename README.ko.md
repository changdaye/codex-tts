# codex-tts

언어: [简体中文](README.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

`codex-tts`는 대화형 `codex` CLI를 위한 로컬 음성 래퍼입니다. `codex-tts`를 통해 Codex를 실행하면 로컬 rollout 데이터를 감시하고, assistant의 새로운 `final_answer`가 생성될 때마다 자동으로 읽어 줍니다.

## 어떤 문제를 해결하나

터미널에서 Codex를 주로 사용할 때 보통 이런 상황이 생깁니다.

- Codex는 이미 끝났는데 다른 창을 보고 있다
- 중간 진행 상황은 필요 없고 최종 결과만 알고 싶다
- Codex 본체는 건드리지 않고 음성만 추가하고 싶다

`codex-tts`는 이 범위에만 집중합니다. Codex를 수정하지 않고 바깥에 얇은 음성 레이어를 추가합니다.

## 현재 기능

- 최종 답변만 읽고 `commentary`는 읽지 않음
- macOS를 대상으로 하며 기본적으로 시스템 `say`를 사용
- 같은 Codex 세션 안에서 새 `final_answer`가 나오면 계속 읽음
- 실행 시 음성, 절대 속도, 배수, 속도 프리셋을 덮어쓸 수 있음
- 읽기 전에 텍스트를 정리하여 URL은 읽지 않고 Markdown 링크는 링크 제목만 남김
- 음성 재생이 실패해도 Codex 본 흐름은 중단하지 않음
- `--verbose`로 thread 선택과 스킵 이유를 stderr에 출력할 수 있음

## 요구 사항

- macOS
- Python `3.11+`
- `codex`가 설치되어 있고 `PATH`에서 실행 가능해야 함
- macOS `say` 사용 가능
- 로컬 `~/.codex` 상태 파일과 세션 파일에 접근 가능해야 함

## 설치

### 방법 1: 전역 명령으로 설치

가장 권장하는 방식입니다. 설치 후에는 어느 디렉터리에서든 `codex-tts`를 실행할 수 있습니다.

```bash
cd /path/to/codex-tts
python3 -m venv .venv
bash scripts/install.sh
```

설치 스크립트는 launcher를 다음 위치에 생성합니다.

```text
~/.local/bin/codex-tts
```

셸에서 아직 `~/.local/bin`이 `PATH`에 없다면 추가하세요.

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

설치 위치를 바꾸고 싶다면 환경 변수를 사용할 수 있습니다.

```bash
CODEX_TTS_INSTALL_DIR="$HOME/bin" bash scripts/install.sh
```

### 방법 2: 소스에서 직접 실행

전역 명령을 아직 설치하고 싶지 않다면 저장소에서 직접 실행할 수 있습니다.

```bash
cd /path/to/codex-tts
python3 -m venv .venv
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --preset ultra -- --no-alt-screen
```

이 방식은 `PATH` 변경이 필요 없지만 저장소 기준으로 실행해야 합니다.

### 전역 launcher 제거

전역 명령이 더 이상 필요 없다면 다음을 실행하세요.

```bash
cd /path/to/codex-tts
bash scripts/uninstall.sh
```

이 스크립트는 `~/.local/bin/codex-tts`만 삭제합니다. 저장소, `.venv`, 설정 파일은 삭제하지 않습니다.

## 빠른 시작

전역 설치를 마쳤다면 가장 짧은 실행 명령은 다음입니다.

```bash
codex-tts --preset ultra -- --no-alt-screen
```

소스에서 직접 실행한다면 다음을 사용하세요.

```bash
PYTHONPATH=src python -m codex_tts.cli --preset ultra -- --no-alt-screen
```

Codex가 열리면 먼저 짧은 테스트 프롬프트를 보내 보세요.

```text
정확히: 테스트 성공
```

정상 동작은 다음과 같습니다.

- 실행 중간 상태는 읽지 않음
- 최종 답변이 나오면 한 번 읽음
- 같은 세션에서 이후 최종 답변도 계속 읽음
- 답변 안의 URL은 읽지 않음

## 자주 쓰는 예시

기본 실행:

```bash
codex-tts -- --no-alt-screen
```

음성을 바꾸고 프리셋 사용:

```bash
codex-tts --voice Tingting --preset faster -- --no-alt-screen
```

배수로 속도 조정:

```bash
codex-tts --speed 3 -- --no-alt-screen
```

절대 속도 직접 지정:

```bash
codex-tts --rate 540 -- --no-alt-screen
```

사용 가능한 시스템 음성 보기:

```bash
codex-tts --list-voices
```

진단 로그 출력:

```bash
codex-tts --verbose -- --no-alt-screen
```

설정 파일을 명시적으로 지정:

```bash
codex-tts --config ~/.codex-tts/config.toml -- --no-alt-screen
```

설명:

- `--` 앞의 인자는 `codex-tts` 자체 옵션입니다
- `--` 뒤의 인자는 실제 `codex` 명령으로 그대로 전달됩니다

## 명령 옵션

| 옵션 | 타입 | 설명 |
| --- | --- | --- |
| `--config` | `Path` | 설정 파일 경로. 기본값은 `~/.codex-tts/config.toml` |
| `--voice` | `str` | 이번 실행에서 음성을 덮어씀 |
| `--rate` | `int` | 이번 실행에서 절대 속도를 직접 지정 |
| `--speed` | `float` | 현재 속도에 배수를 곱함. 예: `3` |
| `--preset` | `str` | 이름 있는 속도 프리셋 사용 |
| `--list-voices` | flag | 사용 가능한 음성 목록을 출력하고 종료 |
| `--verbose` | flag | thread 선택과 스킵 이유를 stderr에 출력 |

규칙:

- `--rate`, `--speed`, `--preset`은 동시에 사용할 수 없음
- 아무 것도 지정하지 않으면 설정 파일 값을 사용
- `--voice`는 `--rate`, `--speed`, `--preset`과 함께 사용할 수 있음

## 속도 프리셋

| 프리셋 | 최종 속도 |
| --- | --- |
| `normal` | `180` |
| `fast` | `270` |
| `faster` | `360` |
| `ultra` | `540` |

원하는 절대 속도를 이미 알고 있다면 `--rate`를 바로 사용해도 됩니다.

## 설정 파일

기본 설정 파일 경로:

```text
~/.codex-tts/config.toml
```

예시:

```toml
backend = "say"
voice = "Tingting"
rate = 180
speak_phase = "final_only"
verbose = false
```

필드 설명:

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `backend` | `"say"` | 음성 백엔드. 현재는 macOS `say`만 지원 |
| `voice` | `"Tingting"` | 기본 음성 |
| `rate` | `180` | 기본 읽기 속도 |
| `speak_phase` | `"final_only"` | 현재는 최종 답변 읽기만 지원 |
| `verbose` | `false` | stderr 디버그 로그 출력 여부 |

검증 규칙:

- `backend`는 현재 `say`만 허용
- `rate`는 `0`보다 커야 함
- `voice`는 앞뒤 공백 제거 후 비어 있으면 안 됨
- `speak_phase`는 현재 `final_only`만 허용
- `verbose`는 불리언이어야 함

우선순위:

1. CLI 인자
2. 설정 파일
3. 내장 기본값

## 동작 방식

실행 흐름은 다음과 같습니다.

1. 실제 `codex`를 실행
2. 작업 디렉터리와 시작 시각을 기록
3. `~/.codex/state_5.sqlite`에서 새 thread를 찾음
4. 그 thread의 rollout JSONL 파일을 계속 추적
5. 새 assistant `final_answer`를 발견할 때마다 읽어 줌

터미널 ANSI 출력은 파싱하지 않습니다. 대신 Codex가 저장하는 구조화된 로컬 세션 데이터를 직접 읽습니다.

## 읽기 전 텍스트 정리 규칙

TTS에 넘기기 전에 가벼운 정리 단계가 있습니다.

- 순수 URL은 제거
- Markdown 링크는 `[제목](url)`에서 제목만 남김
- 불필요한 공백과 빈 줄을 압축
- 정리 후 읽을 내용이 남지 않으면 읽지 않음

이 정리는 음성 출력에만 적용되며, 터미널에 보이는 원문은 바꾸지 않습니다.

## 현재 제한 사항

- macOS `say`만 지원
- 최종 답변만 읽고 오류나 중간 상태는 읽지 않음
- 같은 디렉터리에서 여러 Codex 세션을 동시에 실행하면 완벽한 매칭을 보장하지 않음
- 파일 시스템 이벤트가 아니라 폴링 기반 구현

## 문제 해결

### 소리가 나지 않을 때

먼저 macOS 음성 자체를 확인하세요.

```bash
say "테스트 성공"
```

이것도 소리가 안 나면 다음을 확인하세요.

- 시스템 볼륨
- 현재 오디오 출력 장치
- 이 프로젝트 밖에서도 macOS 음성이 정상 동작하는지

### 명령을 찾을 수 없을 때

소스에서 직접 실행한다면 다음을 사용하세요.

```bash
PYTHONPATH=src python -m codex_tts.cli --help
```

전역 설치를 했다면 다음을 확인하세요.

- `bash scripts/install.sh`를 실행했는지
- `~/.local/bin`이 `PATH`에 들어 있는지
- `source ~/.zshrc` 등으로 셸 설정을 다시 불러왔는지

### Codex는 답했는데 읽지 않을 때

다음을 먼저 확인하세요.

- `codex-tts`를 통해 시작했는지, 그냥 `codex`를 실행한 것은 아닌지
- 해당 응답이 아직 `commentary`가 아니라 실제 최종 단계인지
- 같은 디렉터리에서 여러 개의 서로 다른 Codex 세션을 동시에 돌리고 있지 않은지

그래도 이유가 보이지 않으면 `--verbose`를 붙여 다시 실행하세요.

```bash
codex-tts --verbose -- --no-alt-screen
```

thread 후보 선택, rollout 감시 연결, 정리 후 텍스트가 비어서 읽기를 건너뛴 경우 같은 이유를 stderr에 출력합니다。

### 사용 가능한 음성을 보고 싶을 때

```bash
codex-tts --list-voices
```

## 개발 및 테스트

전체 테스트 실행:

```bash
source .venv/bin/activate
python -m pytest -q
```

CLI 도움말 확인:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m codex_tts.cli --help
```

설치 스크립트만 테스트:

```bash
source .venv/bin/activate
python -m pytest tests/test_install_script.py -q
```

## 이후 계획

- OpenAI / ElevenLabs / Edge TTS 백엔드 추가
- 오류 알림 읽기 기능 추가
- 다중 세션 매칭 개선
- daemon 모드 검토
