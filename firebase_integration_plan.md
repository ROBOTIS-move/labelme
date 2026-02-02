# Labelme Cloud-Native: Firebase 연동 계획

## 개요

이 문서는 Labelme Cloud-Native UI 구현 현황과 Firebase 연동을 위해 구현해야 할 사항을 정리합니다. 현재(2026-02-02) UI 및 로컬 시뮬레이션 기능은 대부분 구현되었으며, 이를 실제 Firebase 백엔드와 연결하는 작업이 남아있습니다.

---

## 1. 현재 구현 현황 (Local Simulation)

### 1.1 UI 및 위젯

| 파일 | 클래스 | 역할 | 상태 |
|------|--------|------|------|
| `widgets/login_dialog.py` | `LoginDialog` | 사용자 ID 입력 (Mock: ADMIN, USER1, USER2) | ✅ 완료 |
| `widgets/mode_selection_dialog.py` | `ModeSelectionDialog` | 모드 선택 (Labeling/Review/Final Review) | ✅ 완료 |
| `widgets/comment_widget.py` | `CommentWidget` | 코멘트 관리 (JSON 기반, 본인 글 삭제) | ✅ 완료 |
| `widgets/task_info_widget.py` | `TaskInfoWidget` | 모드 베지 및 타이머 표시 (Green/Yellow/Red) | ✅ 완료 |
| `widgets/discard_dialog.py` | `DiscardDialog` | 작업 폐기 사유 입력 | ✅ 완료 |
| `widgets/postponed_list_dialog.py` | `PostponedListDialog` | 보류된 작업 목록 표시 및 선택 | ✅ 완료 |

### 1.2 핵심 로직 (`app.py`)

| 기능 | 설명 | 상태 |
|------|------|------|
| **세션 관리** | `_session.json` 기반 작업 상태(이미지, 모드, 타이머) 자동 저장 및 복구 | ✅ 완료 |
| **타이머 Persistence** | `_load_time.txt` 기반 로드 시간 영구 저장 (재시작 시 유지) | ✅ 완료 |
| **Postpone 정책** | 사용자별 디렉터리(`postpone/{user_id}/`)로 파일 이동 및 격리 | ✅ 완료 |
| **Load Postpone** | `PostponedListDialog`를 통해 보류된 작업 선택 및 복구 | ✅ 완료 |
| **Load Task** | 로컬 파일 다이얼로그 (`openDirDialog`) | ⚠️ 임시 |
| **Submit** | 로컬 저장 및 세션 클리어 | ⚠️ 로컬 저장 |
| **Drop/Discard** | 세션 클리어 및 초기화 | ✅ 완료 |
| **작업 경로** | `/home/hun/GT_manager/GT_ALGO/review/ODAS_571` 고정 | ⚠️ 임시 |

---

## 2. Firebase 연동 구현 사항

### 2.1 Firebase 서비스 구성

| 서비스 | 용도 |
|--------|------|
| **Firebase Auth** | (Optional) 사용자 인증. 현재는 ID 입력 방식 유지 가능. |
| **Firestore** | 작업 메타데이터(상태, 할당 정보), 코멘트, 사용자 정보 저장 |
| **Firebase Storage** | 원본 이미지, 결과 JSON 파일 저장 |

### 2.2 Firestore 데이터 구조 (제안)

```javascript
tasks/{task_id} {
    // 기본 정보
    "image_path": "images/image001.jpg",
    "json_path": "annotations/image001.json", // 완료된 경우
    "filename": "image001.jpg",

    // 상태 관리
    "status": "ready", // ready, in_progress, postponed, completed, discarded
    "mode": "labeling", // labeling, review, final_review
    
    // 할당 정보
    "assigned_to": "user1",
    "assigned_at": timestamp,
    "deadline": timestamp, // 할당 시점 + 48시간

    // 코멘트 (Array of Maps)
    "comments": [
        { "user_id": "user1", "text": "검수 완료", "created_at": timestamp }
    ]
}
```

---

## 3. 함수별 연동 계획

### 3.1 `loadTaskAction` (작업 할당)
- **현재**: `openDirDialog`로 로컬 파일 열기
- **연동 후**:
    1. Firestore에서 `status='ready'` AND `mode=current_mode`인 작업 쿼리 (FIFO).
    2. 트랜잭션으로 상태 업데이트 (`status='in_progress'`, `assigned_to=user_id`, `deadline=now+48h`).
    3. Storage에서 이미지(및 이전 JSON) 다운로드 -> `processing/` 디렉터리.
    4. `loadFile` 호출.

### 3.2 `submitTaskAction` (제출)
- **현재**: 로컬 저장 -> 세션 삭제 -> 초기화
- **연동 후**:
    1. 로컬 JSON 저장.
    2. Storage에 JSON 업로드.
    3. Firestore 업데이트 (`status='completed'`, `json_path=...`).
    4. 로컬 파일 (`processing/` 내) 삭제.
    5. 세션 삭제 및 초기화.

### 3.3 `postponeTaskAction` (보류)
- **현재**: `processing/` -> `postpone/{user_id}/`로 파일 이동
- **연동 후**:
    1. 로컬 JSON 저장.
    2. Storage에 JSON 업로드.
    3. Firestore 업데이트 (`status='postponed'`).
    4. 로컬 파일 삭제.

### 3.4 `loadPostponeTaskAction` (보류 작업 로드)
- **현재**: `postpone/{user_id}/` 파일 리스트 -> 선택 -> `processing/`로 이동
- **연동 후**:
    1. Firestore에서 `status='postponed'` AND `assigned_to=user_id`인 작업 목록 쿼리.
    2. `PostponedListDialog`에 목록 표시.
    3. 선택 시 Storage에서 최신 JSON 및 이미지 다운로드 -> `processing/`.
    4. Firestore 업데이트 (`status='in_progress'`).

### 3.5 `CommentWidget` (동기화)
- **현재**: 로컬 `_comments.json` 파일 읽기/쓰기
- **연동 후**:
    - **Load**: Firestore `tasks/{id}/comments` 필드 읽기.
    - **Add**: `arrayUnion`으로 코멘트 추가.
    - **Delete**: `arrayRemove`로 코멘트 삭제 (권한 확인).

---

## 4. 보안 및 배포 고려사항

1. **인증 키 관리**: 서비스 계정 키(`serviceAccountKey.json`)는 절대 코드에 포함하거나 Git에 올리지 않음. 환경 변수 또는 보안 경로(`/home/hun/keys/...`) 사용.
2. **오프라인 모드**: 네트워크 끊김 시 로컬 `_session.json`을 통해 작업 보호 (현재 구현된 로직 유지).
3. **버전 관리**: 클라이언트 버전과 서버 API 버전 호환성 체크 로직 필요.
