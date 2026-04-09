# AGENTS.md — 자율 에이전트 운영 매뉴얼 (한국어)

> **심각도: CRITICAL** — 이 문서의 모든 규칙은 **협상 불가**입니다.
> Hard Constraint 위반 시 즉시 롤백됩니다.
> 코드 한 줄이라도 수정하기 전에 이 파일을 **전부** 읽으십시오.

---

## 1. 프로젝트 개요

[wkentaro/labelme](https://github.com/wkentaro/labelme) v5.0.1 기반의 커스텀 엔터프라이즈 어노테이션 플랫폼입니다.
**Firebase 기반 클라우드 네이티브 워크플로우**(Worker → Reviewer → Final Reviewer → Supervisor)와 다중 역할 인증, 태스크 상태 머신, 작업 시간 추적, 암호화된 감사 추적 기능이 통합되어 있습니다.
AI 오토 라벨링 인프라는 Shape의 `probability` 필드를 통해 존재하며, 직접적인 ML 모델 통합이 예정되어 있습니다.

---

## 2. 기술 스택

| 레이어 | 기술 |
|---|---|
| **GUI 프레임워크** | PyQt5 / PySide2 (`qtpy` 추상화 레이어 경유) |
| **언어** | Python 3.8+ |
| **이미지 처리** | OpenCV (`cv2` ≥ 4.6.0), Pillow, imgviz |
| **데이터 형식** | JSON (Labelme 스키마), YAML (설정) |
| **네트워킹** | `requests` (Firebase HTTP REST) |
| **암호화** | `cryptography.Fernet` (대칭키) |
| **스레딩** | `QThread` + Signal/Slot (`threading.Thread` 절대 사용 금지) |
| **설정** | PyYAML, `default_config.yaml` |
| **AI (예정)** | PyTorch 2.x (device-agnostic, AMP) |

---

## 3. 디렉터리 구조 및 아키텍처

```
labelme/                          # 루트 패키지
├── __init__.py                   # 버전: 5.0.1
├── __main__.py                   # 진입점
├── app.py                        # ★ MainWindow — 핵심 파일 (~4000 LOC)
├── label_file.py                 # ★ JSON I/O — 스키마 핵심
├── shape.py                      # ★ Shape 기하학 + 렌더링
├── logger.py                     # 로깅 설정
├── testing.py                    # 테스트 헬퍼
│
├── config/
│   ├── __init__.py
│   └── default_config.yaml       # ★ 라벨, 단축키, Shape 색상, 독 표시 설정
│
├── widgets/                      # UI 컴포넌트만 — 비즈니스 로직 금지
│   ├── canvas.py                 # ★ 드로잉 캔버스 — 시그널: zoomRequest, newShape 등
│   ├── label_dialog.py           # 라벨 입력/선택
│   ├── label_list_widget.py      # Shape 리스트 독
│   ├── comment_widget.py         # 다중 사용자 코멘트 시스템
│   ├── task_info_widget.py       # 모드 배지 + 마감 타이머
│   ├── image_popup.py            # 마스크/오버레이 이미지 뷰어
│   ├── login_dialog.py           # 인증 대화상자
│   ├── mode_selection_dialog.py  # 라벨링/리뷰/최종리뷰 선택기
│   ├── loading_dialog.py         # 애니메이션 로딩 인디케이터
│   ├── discard_dialog.py         # 사유 기재 태스크 반려
│   ├── postponed_list_dialog.py  # 보류 태스크 복원 (이중 모드: 디렉토리 스캔 / 리스트 기반)
│   ├── work_history_dialog.py    # 라운드/모드별 작업 분석
│   └── ...                       # 기타 표준 Labelme 위젯
│
├── utils/                        # 순수 유틸리티 함수 — 상태 없음, Qt import 최소화
│   ├── image.py                  # EXIF, base64, 이미지 변환
│   ├── shape.py                  # 마스크 ↔ 폴리곤 변환
│   ├── draw.py                   # 렌더링 헬퍼
│   ├── qt.py                     # Qt 헬퍼 함수
│   ├── version_checker.py        # GitHub 릴리즈 버전 확인
│   ├── path_utils.py             # 경로 조작
│   ├── measure_working_time.py   # 작업 시간 추적 + 암호화
│   └── encrypt_cache.py          # Fernet 암복호화 + YAML 캐시
│
├── firebase/                     # 클라우드 통합 레이어 — 네트워크 I/O는 여기에만
│   ├── constants.py              # ★ TaskStatus 열거형, 상태 전이, 역할 매핑
│   ├── database_manager.py       # REST API 호출 (CRUD)
│   ├── image_manager.py          # 이미지 업/다운로드 (서명된 URL)
│   ├── authority_checker.py      # 사용자 인증/역할 검증
│   ├── workers.py                # ★ QThread 워커 — 비동기 Firebase 작업
│   ├── utils.py                  # ConfigLoader (YAML)
│   └── config/
│       └── config.yaml           # ★ Firebase API 엔드포인트 — 시크릿 커밋 금지
│
├── cli/                          # 커맨드라인 유틸리티
│   └── ...                       # draw_json, json_to_dataset 등
│
└── icons/                        # 아이콘 리소스
```

### 3.1 관심사 분리 — 절대 법칙

```
┌─────────────────────────────────────────────────────────────────────┐
│                          금지 구역                                   │
│                                                                     │
│  widgets/*.py  →  절대 포함 금지: HTTP 호출, DB 쿼리,               │
│                   파일 암호화, 모델 추론, 상태 머신                    │
│                                                                     │
│  firebase/*.py →  절대 포함 금지: QPainter, QWidget 서브클래싱,       │
│                   직접 UI 조작, 캔버스 드로잉                         │
│                                                                     │
│  utils/*.py    →  절대 포함 금지: QThread, Signal/Slot 정의,         │
│                   Firebase API 호출, 위젯 인스턴스화                  │
└─────────────────────────────────────────────────────────────────────┘
```

| 레이어 | 허용 Import | 금지 Import |
|---|---|---|
| `widgets/` | `qtpy`, `labelme.shape`, `labelme.utils.*` | `labelme.firebase.*`, `requests` |
| `firebase/` | `qtpy.QtCore` (QThread/Signal만), `requests`, `labelme.firebase.*` | `qtpy.QtWidgets`, `qtpy.QtGui`, `labelme.widgets.*` |
| `utils/` | 표준 라이브러리, `numpy`, `PIL`, `cv2`, `yaml`, `cryptography` | `qtpy.QtWidgets`, `labelme.firebase.*` |
| `app.py` | 전체 (오케스트레이터) | — (단, HC-08 참조) |

> **⚠ 알려진 기술 부채 (확대 금지):**
> 아래 파일들은 관심사 분리 원칙을 위반하며 리팩터링 예정입니다.
> 이 파일들을 참조 패턴으로 사용하지 마십시오. 이 선례를 따라 새로운 위반을 추가하지 마십시오.
>
> | 파일 | 위반 사항 | 올바른 접근 |
> |---|---|---|
> | `widgets/login_dialog.py` | `firebase.authority_checker` import, UI 스레드에서 동기 HTTP 호출 | `QThread` worker로 위임해야 함 |
> | `widgets/mode_selection_dialog.py` | `firebase.constants`, `firebase.database_manager` import, 동기 DB 호출 | `QThread` worker로 위임해야 함 |
>
> **해결된 기술 부채:**
>
> | 날짜 | 파일 | 해결 내용 |
> |---|---|---|
> | 2026-04-07 | `app.py` → `submitTaskAction` | `EncryptCache.run_single()`을 메인 GUI 스레드에서 `SubmitTaskWorker.execute()`로 이동 (HC-01 준수). 워커가 자체 `EncryptCache` 인스턴스를 생성하여 스레드 간 공유 가변 상태 방지. |
> | 2026-04-07 | `app.py` → `_on_load_postpone_list_finished` | 25줄 인라인 `QDialog`를 `PostponedListDialog` 위젯으로 교체. 다이얼로그가 이중 모드 지원: 디렉토리 스캔(`postpone_dir` + `user_id`) 및 리스트 기반(`image_names` Firebase 파라미터). |

### 3.2 애플리케이션 아키텍처 패턴

**모든 비동기 작업은 반드시 이 정확한 흐름을 따라야 합니다:**

```
사용자 액션 (클릭/단축키)
    │
    ▼
MainWindow 메서드 (app.py)
    │
    ├─ (1) 입력 검증 / 확인 다이얼로그 표시
    │
    ├─ (2) LoadingDialog 표시
    │
    ├─ (3) Worker(QThread) 인스턴스화
    │       ├─ worker.finished.connect(self._on_<action>_finished)
    │       ├─ worker.error.connect(self._on_firebase_error)
    │       └─ worker.start()
    │
    ▼
Worker.execute() — 백그라운드 스레드에서 실행
    │
    ├─ 네트워크 I/O, 파일 I/O, 무거운 연산
    │
    ├─ 절대 금지: self.canvas, self.labelList, 모든 QWidget 접근
    │
    └─ Emit: self.finished.emit(result_dict) 또는 self.error.emit(msg)
         │
         ▼
    MainWindow 슬롯 (메인 스레드)
         │
         ├─ UI 업데이트 (캔버스, 독, 상태 바)
         ├─ LoadingDialog 숨김
         └─ 에러 처리
```

### 3.3 새 기능 추가 — 필수 단계

새 기능(위젯, 도구, 통합)을 추가할 때 반드시 **이 순서**를 따라야 합니다:

| 단계 | 작업 | 확인 사항 |
|---|---|---|
| 1 | 대상 디렉터리 `CONTEXT.md` 읽기 | 기존 컴포넌트 이해 |
| 2 | **참조 구현체** 찾기 (HC-10 참조) | 패턴을 처음부터 만들지 않기 |
| 3 | 영향 범위 평가 (HC-09 참조) | 사용자에게 Blast Radius 보고 |
| 4 | 관심사 분리 원칙에 따라 코드 작성 | 레이어 위반 = 즉시 FAIL |
| 5 | `app.py`에서 Signal/Slot 연결 | 라이프사이클 규칙 준수 (HC-03) |
| 6 | 코드 리뷰 에이전트 실행 (HC-07) | 진행 전 PASS 필수 |
| 7 | 테스트 + 린트 실행 | 모두 통과 |
| 8 | `CONTEXT.md` + `CONTEXT_KO.md` 업데이트 | 문서 동기화 유지 |
| 9 | 핵심 파일 수정 시 사용자 승인 요청 | HC-08 |

---

## 4. Hard Constraints

> **이것들은 절대적입니다. 예외는 없습니다. "이번 한 번만" 같은 것은 없습니다.**

---

### HC-01: 메인 스레드 블로킹 금지

**규칙:** 메인 GUI 스레드(`QApplication.exec_()` 실행 위치)에서 **절대로** 다음을 실행하면 안 됩니다:
- AI/ML 모델 추론 (어떤 시간이든)
- HTTP 요청 (`requests.get/post/put/delete`)
- 1MB 초과 파일 작업 (읽기/쓰기)
- 대용량 파일 이미지 인코딩/디코딩
- `time.sleep()` > 100ms
- 외부 데이터에 의존하는 반복 횟수의 루프

**시행:**
```python
# 올바름 — 백그라운드 스레드
worker = LoadTaskWorker(mode, user_id, processing_dir)
worker.finished.connect(self._on_load_task_finished)
worker.error.connect(self._on_firebase_error)
worker.start()

# 치명적 위반 — UI 블로킹
response = requests.get(url)  # 메인 스레드에서
result = model.predict(image)  # 메인 스레드에서
```

**무거운 연산이 필요한 경우:**
1. 적절한 모듈에 `QThread` 서브클래스 생성 (네트워크는 `firebase/workers.py`, 연산은 대상 모듈의 새 `workers.py`)
2. `Signal`을 통해 결과 emit
3. 연결된 `Slot`(메인 스레드)에서만 UI 업데이트

**공유 객체의 스레드 안전성:**
유틸리티 객체(예: `EncryptCache`)를 `QThread` 워커에 전달할 때, 스레드 간 가변 인스턴스를 **절대** 공유하지 마십시오. 대신 `execute()` 내부에서 lazy import를 사용하여 새 인스턴스를 생성하여 상태 오염을 방지하십시오:
```python
# 올바름 — 워커별 격리된 인스턴스
def execute(self):
    from labelme.utils.encrypt_cache import EncryptCache
    encrypt = EncryptCache()
    encrypt.run_single(path, json_path, worker_name=self.user_id)

# 잘못됨 — 공유 가변 인스턴스, 경쟁 조건 위험
def execute(self):
    self.shared_encrypt.run_single(...)  # 메인 스레드도 이것을 사용할 수 있음
```

---

### HC-02: 엄격한 JSON 형식 호환성

**규칙:** Labelme JSON 스키마는 **모든** 기존 어노테이션 파일과 하위 호환성을 유지해야 합니다.

**보호되는 스키마 (label_file.py):**
```json
{
  "version": "string",
  "flags": {},
  "shapes": [
    {
      "label": "string",
      "points": [[x, y], ...],
      "group_id": "int|null",
      "probability": "float|null",
      "shape_type": "polygon|rectangle|line|linestrip|circle|point",
      "flags": {}
    }
  ],
  "imagePath": "string",
  "imageData": "base64_string|null",
  "imageHeight": "int",
  "imageWidth": "int",
  "classType": "string"
}
```

**해서는 안 되는 것:**
- 기존 키 삭제 또는 이름 변경
- 기존 값의 타입 변경
- `save()` 출력의 키 순서 변경 (다운스트림 도구가 의존할 수 있음)
- 필수 키 추가 (새 키는 반드시 `null` 기본값이거나 하위 호환을 위해 생략 가능해야 함)

**해도 되는 것:**
- `null` 기본값의 새로운 **선택적** 키 추가
- `shape_type` 열거형에 새 값 추가 (단, `shape.py`와 `canvas.py`에 등록 필요)

**보조 스키마 — 코멘트 파일 (`{image_stem}_comments.json`):**
```json
[
  { "user": "string (표시명 또는 사용자 ID)", "text": "string" },
  ...
]
```
- `widgets/comment_widget.py`에서 어노테이션 JSON과 함께 저장
- 객체 배열, 각각 `user`와 `text` 키 — 필수 키 추가 금지

**검증:** `label_file.py`, `shape.py`, 또는 `comment_widget.py`를 수정한 후 반드시:
1. 기존 어노테이션 JSON을 로드하여 에러 없이 파싱되는지 확인
2. 다시 저장하고 출력이 동일한지 확인 (라운드트립 테스트)

---

### HC-03: Qt Signal & Slot 라이프사이클

**규칙:** Signal/Slot 연결은 메모리 누수, 중복 발화, 삭제된 객체 크래시를 방지하도록 관리해야 합니다.

**3a. 중복 연결 금지:**
```python
# 잘못됨 — 두 번 호출 시 시그널당 슬롯이 두 번 발화
self.canvas.newShape.connect(self.newShape)
self.canvas.newShape.connect(self.newShape)  # 중복!

# 올바름 — 재연결 전 disconnect, 또는 __init__에서 한 번만 연결
try:
    self.canvas.newShape.disconnect(self.newShape)
except (TypeError, RuntimeError):
    pass
self.canvas.newShape.connect(self.newShape)
```

**3b. 안전한 스레드 종료:**
```python
# 올바름 — 파괴 전 항상 스레드 완료 대기
if self.worker is not None:
    self.worker.quit()
    self.worker.wait(5000)  # 5초 타임아웃
    if self.worker.isRunning():
        self.worker.terminate()  # 최후의 수단
    self.worker.deleteLater()
    self.worker = None
```

**3c. Lambda 슬롯 — 명명된 메서드 또는 `functools.partial` 권장:**

> **참고:** 현재 코드베이스(`app.py` ~496-536행)는 action 연결에 lambda를 사용합니다.
> 이는 기존 코드이므로 — 사용자의 명시적 요청 없이 리팩터링하지 마십시오.
> **새로운** 연결에는 disconnect 가능성을 위해 명명된 메서드 또는 `functools.partial`을 사용하십시오.

```python
# 기존 코드 (허용) — 요청 없이 리팩터링 금지
action.triggered.connect(lambda: self.toggleDrawMode(False, createMode="polygon"))

# 새 코드 권장 — disconnect 가능, 메모리 누수 위험 없음
from functools import partial
action.triggered.connect(partial(self.toggleDrawMode, False, createMode="polygon"))

# 새 코드 최선 — 명명된 메서드
action.triggered.connect(self._on_create_polygon)
```

**3d. 크로스 스레드 시그널 안전:**
- `QThread`에서 메인 스레드 슬롯으로 emit된 시그널은 자동 큐잉 (안전)
- 크로스 스레드 시그널에 `Qt.DirectConnection` 절대 사용 금지
- `QThread.run()` 내에서 `QWidget` 메서드 절대 호출 금지

---

### HC-04: 상태 관리 — 백그라운드 UI 업데이트 금지

**규칙:** 백그라운드 스레드는 **어떠한** UI 상태도 직접 읽거나 쓸 수 없습니다.

**QThread.run() / execute()에서 금지:**
```python
# 백그라운드 스레드에서 이 모든 것은 치명적 위반:
self.parent().canvas.shapes.append(shape)     # 캔버스 수정
self.parent().labelList.addItem(item)          # 위젯 수정
self.parent().setWindowTitle("...")            # 윈도우 수정
self.parent().statusBar().showMessage("...")   # 상태바 수정
QMessageBox.warning(None, "Error", msg)        # 위젯 생성
QPixmap(path)                                  # 비GUI 스레드의 QPixmap
```

**올바른 패턴:**
```python
# QThread 서브클래스에서:
class MyWorker(QThread):
    progress = Signal(int)         # 진행 상황 업데이트 emit
    result_ready = Signal(dict)    # 최종 결과 emit
    error = Signal(str)            # 에러 emit

    def run(self):
        # 시그널만 emit — 위젯 절대 접근 금지
        for i, item in enumerate(self.items):
            processed = self.process(item)
            self.progress.emit(i)
        self.result_ready.emit({'data': processed})

# MainWindow에서 (메인 스레드):
self.worker.result_ready.connect(self._update_canvas_with_result)
```

---

### HC-05: CONTEXT.md 관리

**규칙:** 기능 코드가 포함된 모든 디렉터리에는 반드시 `CONTEXT.md`(영문)와 `CONTEXT_KO.md`(한국어 미러)가 있어야 합니다.

**작업 시작 전:**
1. 대상 디렉터리의 `CONTEXT.md` 읽기
2. 존재하지 않으면 코드 작성 전에 아래 템플릿으로 **생성**
3. 존재하면 현재 코드와 최신 상태인지 확인

**작업 완료 후:**
1. 변경 사항을 반영하여 `CONTEXT.md` 업데이트
2. 동일한 내용을 한국어로 번역하여 `CONTEXT_KO.md` 동기화
3. 두 파일은 동일한 구조와 섹션 헤더를 가져야 함

**템플릿:**
```markdown
# <디렉터리명> — Context

## Purpose
<이 디렉터리/모듈이 하는 일 한 단락>

## Key Files
| File | Responsibility | Signals/Slots | Dependencies |
|---|---|---|---|

## Architecture Notes
<패턴, 제약사항, 주의점>

## Recent Changes
| Date | Change | Author/Agent |
|---|---|---|
```

---

### HC-06: AGENTS_GUIDE_KO.md 동기화

**규칙:** 이 문서의 한국어 미러가 프로젝트 루트의 `AGENTS_GUIDE_KO.md`에 반드시 존재해야 합니다.

- `AGENTS.md`가 생성되거나 수정될 때 `AGENTS_GUIDE_KO.md`도 **같은 커밋에서** 업데이트되어야 함
- 내용은 의미적으로 동일해야 함 — 모든 산문을 한국어로 번역, 코드 블록과 표는 영문 유지
- 섹션 번호와 구조가 정확히 일치해야 함
- 같은 작업에서 번역할 수 없는 경우 TODO 항목을 만들고 사용자에게 알릴 것

---

### HC-07: 필수 코드 리뷰 에이전트

**규칙:** 사용자에게 코드 변경사항을 제시하기 전에 반드시 **"Strict Senior Code Reviewer"** 페르소나를 사용한 자체 리뷰를 수행해야 합니다.

**리뷰 체크리스트 (모든 항목을 평가해야 함):**

| # | 확인 사항 | 카테고리 |
|---|---|---|
| 1 | 메인 스레드 블로킹 없음 (HC-01) | 스레딩 |
| 2 | JSON 스키마 호환성 (HC-02) | 데이터 |
| 3 | Signal/Slot 라이프사이클 올바름 (HC-03) | 메모리 |
| 4 | 백그라운드 UI 변경 없음 (HC-04) | 스레딩 |
| 5 | 관심사 분리 준수 | 아키텍처 |
| 6 | 하드코딩된 경로, 시크릿, 자격증명 없음 | 보안 |
| 7 | 에러 처리 존재 (무시 금지) | 신뢰성 |
| 8 | 기존 코드 패턴/스타일 준수 | 일관성 |
| 9 | `ament_flake8` 준수 | 스타일 |
| 10 | 미사용 import 또는 데드 코드 없음 | 청결성 |

**출력 형식 (필수):**

```markdown
## Code Review Report

| Status | File | Line | Issue |
|---|---|---|---|
| PASS | widgets/my_widget.py | — | All checks passed |
| FAIL | firebase/workers.py | 42 | HC-01: requests.get() called in main thread |
| FAIL | app.py | 1337 | HC-03: Duplicate signal connection |
```

**FAIL 시:**
1. 모든 실패 항목 수정
2. 리뷰 재실행
3. 모든 행이 PASS를 보일 때까지 반복
4. 그 후에만 사용자에게 제시

---

### HC-08: 사용자 승인 필수 — 보호 파일

**규칙:** 다음 파일들은 **어떤 수정이든** 사용자의 명시적 승인이 필요합니다:

| 파일 | 이유 |
|---|---|
| `app.py` | 핵심 애플리케이션 — 하나의 변경이 전체 도구를 망칠 수 있음 |
| `label_file.py` | JSON 스키마 — 저장/로드된 모든 어노테이션에 영향 |
| `config/default_config.yaml` | 사용자 대면 설정 — 모든 사용자에게 영향 |
| `firebase/config/config.yaml` | API 엔드포인트 — 클라우드 연결에 영향 |
| `firebase/constants.py` | 상태 머신 — 잘못된 전이는 워크플로우 손상 |
| `shape.py` (루트) | Shape 기하학 — 렌더링, 저장, 모든 도구에 영향 |
| `setup.py` | 의존성 — 모든 사용자의 설치에 영향 |
| `*.yaml` / `*.json` (설정) | 설정 — 런타임 동작에 영향 |
| `AGENTS.md` | 이 파일 — 모든 미래 에이전트 동작에 영향 |
| `labelme/__init__.py` | 버전 — 업데이트 확인에 영향 |

**워크플로우:**
1. 의도한 변경과 그 이유를 설명
2. 정확한 diff 표시 (이전 → 이후)
3. 수정된 파일을 import/의존하는 모든 파일 나열
4. 사용자의 승인 입력을 **대기**
5. 그 후에만 변경 적용

**절대로** 보호 파일 변경을 비보호 파일과 함께 단일 작업으로 묶지 마십시오.

---

### HC-09: 영향 범위 평가 (Blast Radius)

**규칙:** 아래 표의 파일을 수정하기 전에 반드시 의존성 분석을 수행하고 사용자에게 제시해야 합니다.

| 모듈 | 일반적 종속 요소 |
|---|---|
| `widgets/canvas.py` | `app.py`, `shape.py`, 모든 드로잉 작업 |
| `shape.py` | `canvas.py`, `label_file.py`, `utils/shape.py`, `app.py` |
| `label_file.py` | `app.py`, 모든 저장/로드 작업, `firebase/workers.py` |
| `firebase/constants.py` | `firebase/workers.py`, `firebase/database_manager.py`, `app.py` |
| `firebase/workers.py` | `app.py` (모든 비동기 작업) |
| `utils/image.py` | `label_file.py`, `app.py`, `cli/*` |

**평가 형식:**
```markdown
## Impact Scope Assessment

**Target:** `widgets/canvas.py` — `newSignalName` 시그널 추가
**Direct dependents:** app.py (line 202에서 시그널 연결)
**Transitive dependents:** None
**Risk:** LOW — 추가적 변경, 기존 동작 수정 없음
**Backward compatible:** YES
```

리스크가 **MEDIUM** 또는 **HIGH**인 경우, 변경은 먼저 계획으로 제시(코드 없이)하고 사용자 승인을 기다려야 합니다.

---

### HC-10: 참조 템플릿 — 패턴을 발명하지 말 것

**규칙:** 새 기능을 추가할 때 반드시 먼저 기존 참조 구현체를 찾아 학습해야 합니다.

| 새 기능 유형 | 참조 구현체 |
|---|---|
| 새 QThread Worker | `firebase/workers.py` → `LoadTaskWorker` |
| 새 Dialog 위젯 | `widgets/mode_selection_dialog.py`, `widgets/discard_dialog.py`, 또는 `widgets/postponed_list_dialog.py` (이중 모드 패턴) |
| 새 Dock 위젯 | `widgets/comment_widget.py` 또는 `widgets/task_info_widget.py` |
| 새 Canvas 도구/모드 | `widgets/canvas.py` → `createMode` / `editMode` 패턴 |
| 새 Firebase API 호출 | `firebase/database_manager.py` → 기존 메서드 |
| 새 CLI 명령어 | `cli/draw_json.py` |
| 새 Shape 유형 | `shape.py` → `paint()`의 기존 shape type 처리 |
| 새 설정 옵션 | `config/default_config.yaml` → 기존 항목 |
| 새 Signal/Slot | `app.py` lines 176-246 → 기존 연결 패턴 |

**프로세스:**
1. 참조 구현체를 전체 읽기
2. 패턴 파악: 에러 처리, 시그널 이름, 파라미터 규칙
3. 새 코드에서 동일한 패턴 따르기
4. 코드 리뷰(HC-07)에서 참조와의 패턴 일관성 검증

---

## 5. 태스크 상태 머신

> 이 상태 머신의 수정은 사용자 승인이 필요합니다 (HC-08).

```
                    ┌──────────┐
                    │  READY   │
                    └────┬─────┘
                         │ load (labeling)
                    ┌────▼──────────┐
               ┌────│  PROCESSING   │
               │    └────┬──────────┘
               │         │ submit
               │    ┌────▼──────────────┐
               │    │  REQUEST_REVIEW   │
               │    └────┬──────────────┘
               │         │ load (review)
               │    ┌────▼──────────┐
               │    │   REVIEWING   │
               │    └────┬──────────┘
               │         │ submit (needs modification)
               │    ┌────▼──────┐
               │    │  MODIFY   │
               │    └────┬──────┘
               │         │ load (labeling)
               │    ┌────▼──────────┐
               │    │  MODIFYING    │
               │    └────┬──────────┘
               │         │ submit
               │    ┌────▼──────────────────┐
               │    │  FINISHED_MODIFY      │
               │    └────┬──────────────────┘
               │         │ load (review)
               │    ┌────▼──────────────┐
               │    │  RE_REVIEWING     │
               │    └────┬──────────────┘
               │         │ submit
               │    ┌────▼──────────────────────┐
               │    │  REQUEST_FINAL_REVIEW     │
               │    └────┬──────────────────────┘
               │         │ load (final_review)
               │    ┌────▼──────────────────┐
               │    │  FINAL_REVIEWING      │
               │    └────┬──────────────────┘
               │         │ submit
               │    ┌────▼──────────┐
               │    │   READY_GT    │ ← Ground Truth
               │    └───────────────┘
               │
               │    ┌───────────┐
               └───►│ POSTPONE  │ (모든 활성 상태)
                    └───────────┘
                    ┌───────────┐
                    │  DISCARD  │ (리뷰어 반려)
                    └───────────┘
```

---

## 6. 명령어

### 6.1 애플리케이션

```bash
# 애플리케이션 실행
python -m labelme

# 특정 이미지 디렉터리로 실행
python -m labelme /path/to/images

# 출력 디렉터리 지정 실행
python -m labelme /path/to/images --output /path/to/output
```

### 6.2 리소스 컴파일

> **참고:** 이 프로젝트는 현재 `.qrc` 리소스 파일 없이 `labelme/icons/` 디렉터리에서 직접 아이콘을 로드합니다.
> 아래 명령어는 향후 `.qrc`가 도입될 경우에만 필요합니다.

```bash
# Qt 리소스 컴파일 (.qrc 파일이 존재할 경우에만)
pyrcc5 labelme/icons/resources.qrc -o labelme/icons/resources_rc.py
```

### 6.3 테스트

```bash
# 전체 테스트 실행
python -m pytest tests/ -v

# 특정 테스트 모듈 실행
python -m pytest tests/labelme_tests/test_app.py -v
python -m pytest tests/labelme_tests/utils_tests/ -v
python -m pytest tests/labelme_tests/widgets_tests/ -v

# 커버리지 포함 실행
python -m pytest tests/ --cov=labelme --cov-report=term-missing
```

### 6.4 린팅

```bash
# ament_flake8 (이 프로젝트의 주요 린터)
python -m flake8 labelme/ --max-line-length=120

# 타입 체크 (mypy 사용 가능 시)
python -m mypy labelme/ --ignore-missing-imports
```

### 6.5 빌드 & 설치

```bash
# 개발 설치
pip install -e .

# 배포 빌드
python setup.py sdist bdist_wheel
```

---

## 7. 워크플로우 / 완료 정의

### 7.1 작업 전 체크리스트

코드를 작성하기 전에 다음 **모두**를 완료하십시오:

- [ ] **CONTEXT.md 읽기** — 대상 디렉터리 (없으면 생성 — HC-05)
- [ ] **참조 구현체 식별** — 사용할 패턴 (HC-10)
- [ ] **영향 범위 평가** — 공유 모듈 수정 시 (HC-09)
- [ ] **보호 파일 목록 확인** — 사용자 승인이 필요한가? (HC-08)
- [ ] **스레딩 모델 계획** — 이 작업에 QThread가 필요한가? (HC-01)
- [ ] **JSON 호환성 확인** — 저장/로드에 영향을 주는가? (HC-02)

### 7.2 작업 후 체크리스트

코드 작성 후 다음 **모두**를 검증해야 합니다:

- [ ] **Thread Safety**: 메인 스레드에 블로킹 호출 없음; Worker 스레드에서 UI 접근 없음
- [ ] **JSON Round-Trip**: `label_file.py` 또는 `shape.py` 수정 시, load → save → load가 동일한 출력 생성
- [ ] **Signal/Slot 감사**: 중복 연결 없음; 모든 worker에 안전한 종료 경로
- [ ] **관심사 분리**: 섹션 3.1 위반 크로스 레이어 import 없음
- [ ] **코드 리뷰 에이전트**: 리뷰어 스폰, 모든 행 PASS (HC-07)
- [ ] **린트 클린**: `flake8` 경고 없이 통과
- [ ] **테스트 통과**: `pytest tests/ -v` 모두 녹색
- [ ] **CONTEXT.md 업데이트**: 영문/한국어 버전 모두 (HC-05)
- [ ] **AGENTS_GUIDE_KO.md 동기화**: AGENTS.md 수정 시 (HC-06)
- [ ] **사용자 승인 획득**: 보호 파일 변경 시 (HC-08)

### 7.3 커밋 규칙

```
<type>(<scope>): <description>

Refs: #<issue_number>
```

- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Scope: 모듈명 (예: `widgets`, `firebase`, `canvas`, `label-file`)
- Atomic commits: 커밋당 하나의 논리적 변경
- 커밋 메시지는 **영어**로

---

## 8. 비상 절차

### JSON 호환성을 실수로 깨뜨린 경우:
1. 즉시 **중단**
2. `git diff label_file.py shape.py` — 깨진 변경 식별
3. 해당 변경 되돌리기
4. `tests/labelme_tests/data/`의 기존 테스트 어노테이션 파일로 검증
5. 사용자에게 보고

### UI 프리즈를 유발한 경우:
1. 블로킹 작업 식별 (HTTP 호출 또는 메인 스레드의 무거운 연산일 가능성 높음)
2. `firebase/workers.py` 패턴을 따라 `QThread` worker로 이동
3. 섹션 3.2에 따라 Signal/Slot으로 연결

### 태스크 상태 머신을 손상시킨 경우:
1. `firebase/constants.py` 확인 — `STATUS_TRANSITIONS`와 `LOAD_SOURCE_STATUSES`
2. 섹션 5의 상태 다이어그램에 따라 전이가 유효한지 검증
3. 잘못된 전이는 태스크를 고립시킬 수 있음 — 즉시 사용자에게 에스컬레이션

---

## 9. 금지 행위 — 무관용

| 행위 | 이유 | 결과 |
|---|---|---|
| GUI 코드에서 `import threading` | Qt 자체 스레딩이 있음; 혼합 시 정의되지 않은 동작 | 즉시 롤백 |
| `QThread`에서 `QPixmap` 또는 `QImage` 생성 | 크래시 — Qt GUI 객체는 메인 스레드 전용 | 즉시 롤백 |
| 승인 없이 `STATUS_TRANSITIONS` 수정 | 전체 워크플로우 파이프라인 손상 가능 | 즉시 롤백 |
| 소스에 Firebase URL/토큰 하드코딩 | 보안 위반 | 즉시 롤백 |
| `imageData`를 필수 필드로 추가 | `store_data: false`로 저장된 모든 파일 깨짐 | 즉시 롤백 |
| `main`에 `git push --force` | 공유 히스토리 파괴 | 절대 금지 |
| `tests/`의 테스트 데이터 삭제 | CI 검증 깨짐 | 절대 금지 |
| "타이밍"을 위해 메인 스레드에서 `sleep()` 추가 | UI 프리즈; 대신 `QTimer` 사용 | 즉시 롤백 |
| `Exception` catch 후 조용히 pass | 버그 숨김, 상태 손상 | 즉시 롤백 |
| 디버깅용 print() 작성 (코드에 남김) | `logging.getLogger(__name__)` 사용할 것 | 커밋 전 반드시 제거 |

---

> **최종 경고:** 이 문서는 당신의 운영 계약서입니다.
> 규칙이 불편하게 느껴진다면, 그것은 규칙이 제대로 작동하고 있다는 뜻입니다.
> 확신이 없으면 **사용자에게 물어보십시오**. 침묵은 동의가 아닙니다.
