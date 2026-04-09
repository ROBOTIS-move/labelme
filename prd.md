# [PRD] Gaemi Project: Cloud-Native Labelme 고도화

| 문서 버전 | 1.1 | 작성일 | 2026-02-03 |
| :--- | :--- | :--- | :--- |
| **프로젝트명** | Cloud-Native Labelme | **기반 플랫폼** | ROS 2 / Python / Firebase |
| **대상 독자** | 개발팀, 데이터 관리자 | **상태** | **구현 완료 (UI/Logic)** / Backend 연동 대기 |

## 1. 개요 (Overview)

### 1.1 배경 및 목적
기존의 로컬 파일 기반 및 Google Drive 수동 동기화 방식은 버전 관리의 어려움, 동시성 문제, 데이터 보안 취약점, 작업 비효율을 초래함. 이를 **Firebase 기반의 실시간 중앙 집중형 시스템**으로 전환하여 작업 효율성을 극대화하고 데이터 파이프라인을 자동화하고자 함.

### 1.2 핵심 목표
1.  **자동화 (Automation):** 파일 입출력(Download/Upload)의 자동화 및 FIFO 기반 작업 할당.
2.  **협업 효율 (Collaboration):** 동시 작업 충돌 방지 및 실시간 상태 공유.
3.  **데이터 무결성 (Integrity):** 메타데이터 자동 주입 및 휴먼 에러(빈 파일 제출 등) 방지.
4.  **비용 최적화 (Cost):** 순환형(Rotation) 데이터 정책으로 클라우드 비용 최소화 (Free Tier 유지).

### 1.3 Cloud-Native 모드 (Hybrid Architecture)
-   **Mode Flag:** 로그인 성공 시 `is_cloud_native_mode = True`로 활성화되며, 일반 Labelme 기능과 격리됨.
-   **Local Simulation:** Firebase 연동 전까지 로컬 파일 시스템(`processing/`, `postpone/`)을 이용하여 클라우드 동작을 모사함.

---

## 2. 시스템 아키텍처 (System Architecture)

-   **Client App:** Labelme (Customized for Robotis)
    -   **UI:** Python/Qt 기반 기존 UI 확장 (English with Korean Tooltips).
    -   **Widgets:**
        -   `LoginDialog`: 사용자 인증.
        -   `ModeSelectionDialog`: 작업 단계 선택.
        -   `TaskInfoWidget`: 타이머 및 모드 상태 표시 (Dock).
        -   `CommentWidget`: 작업자 간 코멘트 교환 (Dock).
        -   `PostponedListDialog`: 보류 작업 목록 및 복구.
        -   `DiscardDialog`: 작업 폐기 사유 입력.
    -   **Path Config:** 환경 변수 `LABELME_WORK_DIR` 또는 기본 경로(`~/.labelme/cloud_tasks`) 사용.
-   **Backend (Serverless) - Planned:**
    -   **Firebase Storage:** 원본 이미지 및 결과 JSON 파일 저장소.
    -   **Cloud Firestore:** 작업 상태, 할당 정보, 메타데이터, 코멘트 저장소.
-   **Admin Ops:**
    -   **Scheduler:** 마감 기한(48h) 초과 작업 회수, 일일 Drop 카운트 초기화.

---

## 3. 사용자 시나리오 및 기능 명세 (Functional Requirements)

### 3.1 시작 및 진입 (Startup & Entry)
* **로그인 (Authentication):**
    * 앱 시작 시 `LoginDialog` 표시.
    * 유효한 사용자 ID 입력 시 Cloud-Native 모드 활성화.
* **작업 모드 선택 (Mode Selection):**
    * **Labeling:** 일반 작업 (신규 할당).
    * **Review:** 1차 검토 (본인 작업 제외).
    * **Final Review:** 최종 검토 (관리자 코드 필요).
* **자동 복구 (Auto-Resume):**
    * 실행 시 `_session.json`을 감지하여 비정상 종료된 작업(이미지, 모드, 타이머)을 자동 복구.
    * 사용자 ID가 일치하는 경우에만 복구 수행.

### 3.2 작업 공간 (Workspace)
* **FIFO 자동 할당 (Load Task):**
    * `processing_dir` 내 작업을 우선적으로 로드 (Firebase 연동 시 쿼리 기반 할당).
* **정보 표시 (Info Panel):**
    * **Task Info:** 현재 모드(Labeling/Review 등)와 남은 시간(48시간 카운트다운) 표시.
    * **Comments:** Review 모드 이상에서 활성화되며, 작업에 대한 이슈 트래킹 가능.
* **작업 경로 유연성:**
    * 하드코딩된 경로 대신 사용자 홈 디렉터리(`~/.labelme/cloud_tasks`) 또는 환경 변수(`LABELME_WORK_DIR`)를 우선 사용.

### 3.3 액션 및 로직 (Core Actions)
* **제출 (Submit):**
    * **검증:** 빈 데이터 제출 시 경고.
    * **처리:** JSON 생성 시 `imageData` 제거, `imagePath`는 파일명(basename)만 유지.
    * **정리:** 제출 완료 후 로컬 파일 삭제 및 UI 상태(Canvas, Actions) 완전 초기화 (`closeFile` 로직).
    * **상태 전이:** Labeling → Review → Final Review → Done.
* **작업 포기 (Drop Task):**
    * **정책:** 일일 3회 제한 (현재 Mock 구현, Firebase 연동 시 `users/{id}/drop_count` 확인).
    * **동작:** 제한 초과 시 차단, 허용 시 작업 반납 처리 후 로컬 삭제 및 초기화.
* **작업 보류 (Postpone):**
    * **격리:** 현재 작업을 `postpone/{user_id}/` 디렉터리로 이동하여 격리.
    * **복구:** `Load Postpone` 메뉴를 통해 보류된 작업 목록(`PostponedListDialog`) 확인 및 재개.
    * **지원 포맷:** Qt가 지원하는 모든 이미지 포맷 동적 지원.
* **작업 폐기 (Discard Task):**
    * **절차:** `DiscardDialog`를 통해 사유 입력 필수.
    * **처리:** 사유 기록 후 로컬 삭제 및 초기화.

### 3.4 예외 및 안전 장치 (Safety)
* **완전한 상태 정리 (State Cleanup):**
    * Submit/Drop/Postpone/Discard 실행 시 반드시 `resetState`, `setClean`, `toggleActions(False)`, `canvas.setEnabled(False)`를 호출하여 UI 버그 방지.
* **타이머 영속성:**
    * `_load_time.txt`를 통해 재시작 후에도 할당 시간 유지.
* **UI 영문화:**
    * 글로벌/내부 협업을 위해 모든 메시지는 영문으로 제공, 편의를 위해 한글 툴팁 제공.

---

## 4. 데이터베이스 스키마 (Firestore Schema - Proposed)

### Collection: `tasks`
| Field Name | Type | Description |
| :--- | :--- | :--- |
| **Document ID** | String | 이미지 파일명 |
| `status` | String | `ready`, `in_progress`, `postponed`, `review_ready`, `final_review_ready`, `done`, `discarded` |
| `worker_id` | String | 현재 할당된 작업자 ID |
| `assigned_at` | Timestamp | 작업 시작 시간 |
| `deadline` | Timestamp | 마감 기한 |
| `comments` | Array | 코멘트 리스트 |
| `discard_reason` | String | 폐기 사유 |

### Collection: `users`
| Field Name | Type | Description |
| :--- | :--- | :--- |
| **Document ID** | String | 사용자 ID |
| `drop_count` | Number | 금일 작업 반납 횟수 (매일 자정 리셋) |

---

## 5. 구현 현황 요약 (Implementation Status)

| 컴포넌트 | 구현 상태 | 비고 |
| :--- | :--- | :--- |
| **All Dialogs & Widgets** | ✅ 완료 | Login, Mode, Comment, TaskInfo, Discard, PostponeList |
| **Local Logic (Session)** | ✅ 완료 | Auto-save, Auto-resume, Path Config |
| **Action Logic** | ✅ 완료 | Submit, Drop(Mock Limit), Postpone(User-based), Discard |
| **File Cleanup** | ✅ 완료 | UI/Data State 완전 초기화 로직 적용 |
| **Firebase Integration** | ⏳ 대기 | `firebase_integration_plan.md`에 상세 계획 수립됨 |