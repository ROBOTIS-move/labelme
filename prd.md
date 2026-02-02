# [PRD] Gaemi Project: Cloud-Native Labelme 고도화

| 문서 버전 | 1.0 | 작성일 | 2026-01-29 |
| :--- | :--- | :--- | :--- |
| **프로젝트명** | Cloud-Native Labelme | **기반 플랫폼** | ROS 2 / Python / Firebase |
| **대상 독자** | 개발팀, 데이터 관리자 | **상태** | **확정 (Approved)** |

## 1. 개요 (Overview)

### 1.1 배경 및 목적
기존의 로컬 파일 기반 및 Google Drive 수동 동기화 방식은 버전 관리의 어려움, 동시성 문제, 데이터 보안 취약점, 작업 비효율을 초래함. 이를 **Firebase 기반의 실시간 중앙 집중형 시스템**으로 전환하여 작업 효율성을 극대화하고 데이터 파이프라인을 자동화하고자 함.

### 1.2 핵심 목표
1.  **자동화 (Automation):** 파일 입출력(Download/Upload)의 자동화 및 FIFO 기반 작업 할당.
2.  **협업 효율 (Collaboration):** 동시 작업 충돌 방지 및 실시간 상태 공유.
3.  **데이터 무결성 (Integrity):** 메타데이터 자동 주입 및 휴먼 에러(빈 파일 제출 등) 방지.
4.  **비용 최적화 (Cost):** 순환형(Rotation) 데이터 정책으로 클라우드 비용 최소화 (Free Tier 유지).

---

## 2. 시스템 아키텍처 (System Architecture)

-   **Client App:** Labelme (Customized for Robotis)
    -   **UI:** Python/Qt 기반 기존 UI 확장.
    -   **Auth:** Firebase Auth (Email/PW) 기반 사용자 인증 (Admin Key 미포함).
    -   **Data:** `Pyrebase4` (REST API) 및 `Firebase Storage SDK` 활용.
-   **Backend (Serverless):**
    -   **Firebase Storage:** 원본 이미지 및 결과 JSON 파일 저장소.
    -   **Cloud Firestore:** 작업 상태, 할당 정보, 메타데이터, 코멘트 저장소.
-   **Admin Ops:**
    -   **Scheduler:** 마감 기한(48h) 초과 작업 회수, 좀비 데이터 정리.
    -   **Seeder/Exporter:** 초기 데이터 적재 및 완료 데이터(GT) NAS 백업/삭제.

---

## 3. 사용자 시나리오 및 기능 명세 (Functional Requirements)

### 3.1 시작 및 진입 (Startup & Entry)
* **로그인 (Authentication):**
    * 프로그램 실행 시 ID/PW 입력 창 표시.
    * Firebase Auth 연동하여 유효한 사용자만 진입 허용.
* **버전 체크 (Version Control):**
    * DB의 `system_config` 내 `min_version`과 현재 클라이언트 버전 비교.
    * 하위 버전일 경우 "업데이트 필요" 알림 후 강제 종료.
* **작업 모드 선택 (Mode Selection):**
    * 로그인 성공 시 다이얼로그 표시.
    * **Labeling:** 일반 작업 (`ready` 상태 할당).
    * **Review:** 1차 검토 (`review_ready` 상태 할당, 본인 작업 제외).
    * **Final Review:** 최종 검토 (`final_review_ready` 상태 할당, **관리자 코드 입력 필수**).
* **자동 복구 (Auto-Resume):**
    * 로컬 캐시 폴더 스캔 → 파일 존재 시 DB 상태 대조.
    * 유효한 할당(Processing & Time Valid)인 경우 **자동 열기**.
    * 만료/회수된 경우 **로컬 파일 자동 삭제** 후 모드 선택 화면 유지.

### 3.2 작업 공간 (Workspace)
* **FIFO 자동 할당:**
    * 파일 열기(`Open Dir`) 기능 비활성화 또는 `Load Task` 버튼으로 대체.
    * 클릭 시 DB에서 `created_at`이 가장 오래된 `ready` 상태 작업을 `processing`으로 변경(Lock) 후 다운로드.
* **정보 표시 (Info Panel):**
    * **타이머:** 하단 상태바에 `남은 시간: OO시간 OO분` 표시 (48시간 기준, 임박 시 붉은색).
    * **커뮤니케이션:** 우측 도크(Dock)에 채팅 UI 형태의 **메모(Comments)** 기능 추가 (DB 실시간 동기화).

### 3.3 액션 및 로직 (Core Actions)
* **제출 및 다음 (Submit & Next):**
    * **유효성 검사:** `shapes` 리스트가 비어있을 경우 "빈 데이터 경고" 팝업.
    * **데이터 처리:**
        * JSON 내 `imageData` 필드 **강제 Null 처리**.
        * JSON 내 `imagePath`는 경로 제외하고 **파일명만 기입**.
        * DB에 저장된 메타데이터(`serviceArea`, `classType`)를 JSON에 **자동 주입**.
    * **업로드:** JSON 파일 업로드 (로컬 마스크/오버레이 파일은 업로드 제외).
    * **상태 전이:**
        * Labeling → `review_ready`
        * Review → `final_review_ready`
        * Final Review → `done` (DB에 `is_gt: true` 플래그 추가)
    * **정리 (Clean-up):** 업로드 성공 확인 후 로컬 파일 즉시 삭제 → 다음 작업 자동 로드.
* **작업 포기 (Drop Task):**
    * 메뉴바 기능. 실행 시 DB 상태를 `ready`로 원복하고 로컬 파일 삭제.
    * 일일 반납 횟수 제한 적용 (매일 자정 클라이언트 로컬 카운트 초기화).
* **작업 폐기 (Discard Task):**
    * 작업 불가능 이미지 처리.
    * **사유 입력 팝업 필수** (예: 너무 어두움, 렌즈 가림 등).
    * DB 상태를 `discarded`로 변경하고 사유(`discard_reason`) 기록.

### 3.4 예외 및 안전 장치 (Safety)
* **오프라인 차단:** 인터넷 미연결 감지 시 프로그램 실행 및 데이터 제출 차단.
* **동시성 제어:** Firestore Transaction을 사용하여 동일 이미지 중복 할당 원천 차단.
* **파일명 유니크:** 배포 단계에서 파일명 중복이 없음을 전제로, 파일명을 DB Document ID로 사용.

---

## 4. 데이터베이스 스키마 (Firestore Schema)

### Collection: `tasks`
| Field Name | Type | Description |
| :--- | :--- | :--- |
| **Document ID** | String | 이미지 파일명 (예: `cam_front_12345.jpg`) |
| `status` | String | `ready` \| `processing` \| `review_ready` \| `final_review_ready` \| `done` \| `discarded` |
| `worker_id` | String | 현재 할당된 작업자 ID (Email) |
| `created_at` | Timestamp | 데이터 생성일 (FIFO 정렬 기준) |
| `assigned_at` | Timestamp | 작업 시작 시간 (마감 기한 계산용) |
| `updated_at` | Timestamp | 마지막 상태 변경 시간 |
| `storage_image_path` | String | Storage 내 이미지 경로 |
| `storage_json_path` | String | Storage 내 JSON 경로 |
| `meta_service_area` | String | (자동주입용) 지역 정보 |
| `meta_class_type` | String | (자동주입용) 뷰 타입 정보 |
| `discard_reason` | String | 폐기 시 사유 |
| `is_gt` | Boolean | 최종 완료 여부 (`done` 상태 시 true) |
| `comments` | Array | `[{user: "id", msg: "text", time: ...}]` |

### Collection: `users`
| Field Name | Type | Description |
| :--- | :--- | :--- |
| **Document ID** | String | 사용자 ID (Email) |
| `role` | String | `labeler` \| `reviewer` \| `admin` |
| `drop_count` | Number | 금일 작업 반납 횟수 |
| `last_active` | Timestamp | 마지막 접속 시간 |

### Collection: `system_config`
| Field Name | Type | Description |
| :--- | :--- | :--- |
| **Document ID** | String | `app_info` (고정) |
| `min_version` | String | 최소 실행 가능 클라이언트 버전 (예: "2.1.0") |
| `admin_code` | String | Final Review 진입용 암호 |

---

## 5. 운영 및 유지보수 (Operations)

### 5.1 데이터 순환 정책 (Data Rotation)
* **비용 절감 전략:** 클라우드 스토리지는 '임시 작업 공간'으로만 활용.
* **프로세스:**
    1.  최종 검토 완료(`status: done`)된 데이터 주기적 확인.
    2.  로컬 서버/NAS로 다운로드 및 포맷 변환(GT 생성).
    3.  데이터 무결성 검증 후 **Firebase Storage 및 DB에서 즉시 삭제**.
* **기대 효과:** Storage 용량을 항상 무료 구간(5GB) 이내로 유지하여 비용 '0원' 달성.

### 5.2 좀비 데이터 관리 (Zombie Task Handling)
* **Server-side:** 별도 스케줄러(Cloud Functions 또는 Admin Script)가 실행.
* **Logic:** `assigned_at` + 48시간이 지난 `processing` 상태의 작업을 `ready`로 강제 초기화 및 `worker_id` 해제.

---

## 6. 작업 흐름도 (State Transition)

### Labeler: Ready → (Work) → Review Ready

### Reviewer: Review Ready → (Work) → Final Review Ready

### 반려 시: Review Ready → Ready (코멘트 첨부)

### Admin: Final Review Ready → (Work) → Done (GT Created)

### Common: 모든 단계에서 Discarded (폐기) 또는 Ready (포기/만료)로 이동 가능.