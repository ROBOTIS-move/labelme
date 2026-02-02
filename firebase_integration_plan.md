# Labelme Cloud-Native: Firebase 연동 계획

## 개요

이 문서는 Labelme Cloud-Native UI 구현 현황과 Firebase 연동을 위해 구현해야 할 사항을 정리합니다. 현재(2026-02-02) UI 및 로컬 시뮬레이션 기능은 대부분 구현되었으며, 이를 실제 Firebase 백엔드와 연결하는 작업이 남아있습니다.

---

## 1. 현재 구현 현황 (Local Simulation)

### 1.1 UI 및 위젯

| 파일 | 클래스 | 역할 | 상태 |
|------|--------|------|------|
| `widgets/login_dialog.py` | `LoginDialog` | 사용자 ID 입력 (Mock: jsh@robotis.com, "") | ✅ 완료 (영문화) |
| `widgets/mode_selection_dialog.py` | `ModeSelectionDialog` | 모드 선택 (Labeling/Review/Final Review) | ✅ 완료 (영문화) |
| `widgets/comment_widget.py` | `CommentWidget` | 코멘트 관리 (JSON 기반, 본인 글 삭제) | ✅ 완료 (영문) |
| `widgets/task_info_widget.py` | `TaskInfoWidget` | 모드 배지 및 타이머 표시 (Green/Yellow/Red) | ✅ 완료 (영문화) |
| `widgets/discard_dialog.py` | `DiscardDialog` | 작업 폐기 사유 입력 | ✅ 완료 (영문화) |
| `widgets/postponed_list_dialog.py` | `PostponedListDialog` | 보류된 작업 목록 표시 및 선택 (동적 이미지 형식 지원) | ✅ 완료 (영문화) |

**UI 언어**: 모든 사용자 표시 텍스트는 영문으로 표시되며, 한글은 Tooltip으로 제공됩니다.

### 1.2 핵심 로직 (`app.py`)

| 기능 | 설명 | 상태 |
|------|------|------|
| **세션 관리** | `_session.json` 기반 작업 상태(이미지, 모드, 타이머) 자동 저장 및 복구 | ✅ 완료 |
| **타이머 Persistence** | `_load_time.txt` 기반 로드 시간 영구 저장 (재시작 시 유지) | ✅ 완료 |
| **Postpone 정책** | 사용자별 디렉터리(`postpone/{user_id}/`)로 파일 이동 및 격리 | ✅ 완료 |
| **Load Postpone** | `PostponedListDialog`를 통해 보류된 작업 선택 및 복구 | ✅ 완료 |
| **Load Task** | 로컬 파일 다이얼로그 (`openDirDialog`) | ⚠️ 임시 (Firebase 연동 필요) |
| **Submit** | 로컬 저장 + 완전한 파일/UI 정리 (closeFile 로직) | ✅ 완료 (로컬) |
| **Drop** | 일일 횟수 제한(3회) + 완전한 파일/UI 정리 | ✅ 완료 (Mock, Firebase 연동 필요) |
| **Discard** | 사유 입력 + 완전한 파일/UI 정리 | ✅ 완료 (로컬) |
| **Postpone** | 파일 이동 + 완전한 파일/UI 정리 | ✅ 완료 (로컬) |
| **imagePath 저장** | JSON 저장 시 `basename`만 저장 (전체 경로 제외) | ✅ 완료 |
| **Drop 횟수 제한** | `_check_drop_count()` 메서드로 Firebase 조회 (현재 Mock) | ✅ 구현 (Firebase 연동 필요) |

### 1.3 최근 개선 사항

- **파일 정리 로직 개선**: Submit/Drop/Postpone 액션에서 `resetState()` 외에 `setClean()`, `toggleActions(False)`, `canvas.setEnabled(False)` 등 완전한 UI 정리 수행
- **동적 이미지 형식 지원**: `QtGui.QImageReader.supportedImageFormats()`를 사용하여 하드코딩된 확장자 목록 제거
- **UI 영문화**: 모든 메시지박스, 다이얼로그 텍스트를 영어로 변경하고 한글 툴팁 추가

---

## 2. Firebase 연동 구현 사항

### 2.1 Firebase 서비스 구성

| 서비스 | 용도 |
|--------|------|
| **Firebase Auth** | (Optional) 사용자 인증. 현재는 ID 입력 방식 유지 가능. |
| **Firestore** | 작업 메타데이터(상태, 할당 정보), 코멘트, 사용자 정보, **Drop 카운트** 저장 |
| **Firebase Storage** | 원본 이미지, 결과 JSON 파일 저장 |

### 2.2 Firestore 데이터 구조 (제안)

#### tasks/{task_id}
```javascript
{
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

    // 폐기 정보 (상태가 discarded인 경우)
    "discard_reason": "Image is too dark for labeling",
    "discarded_at": timestamp,

    // 코멘트 (Array of Maps)
    "comments": [
        { "user_id": "user1", "text": "검수 완료", "created_at": timestamp }
    ]
}
```

#### users/{user_id}
```javascript
{
    "email": "jsh@robotis.com",
    "drop_count": 2,  // 오늘의 Drop 횟수 (자정에 Watcher가 0으로 초기화)
    "last_drop_reset": timestamp  // 마지막 초기화 시각
}
```

#### system_config/settings
```javascript
{
    "admin_code": "admin123",
    "max_daily_drops": 3,
    "task_deadline_hours": 48
}
```

---

## 3. 함수별 연동 계획

### 3.1 `loadTaskAction` (작업 할당)
- **현재**: `openDirDialog`로 로컬 파일 열기
- **연동 후**:
    1. Firestore에서 `status='ready'` AND `mode=current_mode`인 작업 쿼리 (FIFO: `created_at` 기준).
    2. 트랜잭션으로 상태 업데이트 (`status='in_progress'`, `assigned_to=user_id`, `assigned_at=now`, `deadline=now+48h`).
    3. Storage에서 이미지(및 이전 JSON) 다운로드 → `processing/` 디렉터리.
    4. `loadFile` 호출.

### 3.2 `submitTaskAction` (제출)
- **현재**: 로컬 저장 → 세션 삭제 → 완전한 UI/파일 정리
- **연동 후**:
    1. 로컬 JSON 저장 (`imagePath`는 `basename`만).
    2. Storage에 JSON 업로드.
    3. Firestore 업데이트:
        - Labeling → `status='review_ready'`
        - Review → `status='final_review_ready'`
        - Final Review → `status='done'`, `is_gt=true`
    4. 로컬 파일 (`processing/` 내) 삭제.
    5. 세션 삭제 및 완전한 정리.

### 3.3 `postponeTaskAction` (보류)
- **현재**: `processing/` → `postpone/{user_id}/`로 파일 이동
- **연동 후**:
    1. 로컬 JSON 저장.
    2. Storage에 JSON 업로드 (진행 중 상태 백업).
    3. Firestore 업데이트 (`status='postponed'`).
    4. 로컬 파일 삭제.
    5. 완전한 정리.

### 3.4 `loadPostponeTaskAction` (보류 작업 로드)
- **현재**: `postpone/{user_id}/` 파일 리스트 → 선택 → `processing/`로 이동
- **연동 후**:
    1. Firestore에서 `status='postponed'` AND `assigned_to=user_id`인 작업 목록 쿼리.
    2. `PostponedListDialog`에 목록 표시.
    3. 선택 시 Storage에서 최신 JSON 및 이미지 다운로드 → `processing/`.
    4. Firestore 업데이트 (`status='in_progress'`, `deadline` 갱신).

### 3.5 `dropTaskAction` (작업 포기)
- **현재**: 로컬 Mock으로 횟수 체크 (항상 0 반환) → 3회 미만이면 허용
- **연동 후**:
    1. **`_check_drop_count()` 구현**:
        ```python
        def _check_drop_count(self) -> int:
            from firebase_admin import firestore
            db = firestore.client()
            user_ref = db.collection('users').document(self.current_user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                return user_doc.to_dict().get('drop_count', 0)
            return 0
        ```
    2. 횟수가 3 이상이면 경고 팝업 → 차단.
    3. 3 미만이면:
        - Firestore에서 `users/{user_id}/drop_count` 증가 (트랜잭션).
        - `tasks/{task_id}` 상태를 `ready`로 원복.
        - 로컬 파일 삭제 및 완전한 정리.

> **Watcher 프로그램**: 매일 자정에 모든 사용자의 `drop_count`를 0으로 초기화.

### 3.6 `discardTaskAction` (작업 폐기)
- **현재**: 사유 입력 → 로컬 정리
- **연동 후**:
    1. `DiscardDialog`로 사유 입력.
    2. Firestore 업데이트 (`status='discarded'`, `discard_reason=...`, `discarded_at=now`).
    3. 로컬 파일 삭제 및 완전한 정리.

### 3.7 `CommentWidget` (실시간 동기화)
- **현재**: 로컬 `_comments.json` 파일 읽기/쓰기
- **연동 후**:
    - **Load**: Firestore `tasks/{id}/comments` 필드 읽기.
    - **Add**: `arrayUnion`으로 코멘트 추가.
    - **Delete**: `arrayRemove`로 코멘트 삭제 (권한 확인: `user_id` 일치).

---

## 4. 보안 및 배포 고려사항

1. **인증 키 관리**: 서비스 계정 키(`serviceAccountKey.json`)는 절대 코드에 포함하거나 Git에 올리지 않음. 환경 변수 또는 보안 경로(`/home/hun/keys/...`) 사용.
2. **오프라인 모드**: 네트워크 끊김 시 로컬 `_session.json`을 통해 작업 보호 (현재 구현된 로직 유지).
3. **버전 관리**: 클라이언트 버전과 서버 API 버전 호환성 체크 로직 필요.
4. **Firestore 보안 규칙**: Read/Write 권한을 사용자별로 제한.
5. **데이터 검증**: 클라이언트에서 제출된 데이터의 무결성을 서버(Cloud Functions)에서 검증.

---

## 5. 다음 단계

1. **Firebase 프로젝트 설정**:
   - Firebase Console에서 프로젝트 생성.
   - Firestore, Storage 활성화.
   - 서비스 계정 키 다운로드 및 보안 경로에 저장.

2. **Python Firebase SDK 설치**:
   ```bash
   pip install firebase-admin
   ```

3. **`firebase_manager.py` 모듈 생성**:
   - Firebase 초기화 및 공통 함수 관리.
   - `get_ready_task()`, `update_task_status()`, `upload_to_storage()` 등.

4. **기존 Mock 로직을 Firebase 연동으로 교체**:
   - 각 액션(`loadTaskAction`, `submitTaskAction` 등)의 TODO 주석 부분을 실제 Firebase 코드로 대체.

5. **Watcher 프로그램 개발**:
   - Cron 또는 Cloud Scheduler를 사용하여 매일 자정 `drop_count` 초기화.

6. **테스트 및 검증**:
   - 로컬 환경에서 Firebase 연동 테스트.
   - 동시성 테스트 (여러 사용자가 동시에 작업 할당).
   - 네트워크 장애 시나리오 테스트.
