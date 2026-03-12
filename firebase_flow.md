# Firebase 연동 흐름

## 상태 흐름 다이어그램

```
                          ┌──────────────────────────────────────────────────────────────┐
                          │                        메인 흐름                              │
                          │                                                              │
  [슈퍼바이저 생성] ──► READY                                                             │
                            │                                                            │
                   Worker   │  태스크 로드                                                │
                            ▼                                                            │
                        PROCESSING ──── 연기 ──► POSTPONE                                │
                            │                       │                                    │
                            │              연기된 태스크 로드 (assigned_at 갱신)           │
                            │                       │                                    │
                            │◄──────────────────────┘                                   │
                            │                                                            │
                   Worker   │  제출                                                      │
                            ▼                                                            │
                      REQUEST_REVIEW                                                     │
                            │                                                            │
                  Reviewer  │  태스크 로드                                                │
                            ▼                                                            │
                        REVIEWING                                                        │
                            │                                                            │
                  Reviewer  │  제출                                                      │
                            ├───── 코멘트 있음 ──────► MODIFY                             │
                            │                           │                                │
                            │                  Worker   │  수정 로드 (worker_id=me 필터)  │
                            │                           ▼                                │
                            │                       MODIFYING                            │
                            │                           │                                │
                            │                  Worker   │  제출                           │
                            │                           ▼                                │
                            │                     FINISHED_MODIFY                        │
                            │                           │                                │
                            │                 Reviewer  │  태스크 로드                    │
                            │                           ▼                                │
                            │                      RE_REVIEWING                          │
                            │                           │                                │
                            │                 Reviewer  │  제출                           │
                            │                           │                                │
                            ├───── 코멘트 없음 ─────────┤                                │
                            │  (MODIFY 건너뜀)          │                                │
                            │                           ▼                                │
                            │                  REQUEST_FINAL_REVIEW                      │
                            │                           │                                │
                            │               Supervisor  │  태스크 로드                    │
                            │                           ▼                                │
                            │                    FINAL_REVIEWING                         │
                            │                           │                                │
                            │               Supervisor  │  제출                           │
                            │                           ▼                                │
                            │                        READY_GT                            │
                            │                     (외부 프로그램 처리)                    │
                            │                                                            │
                          └──────────────────────────────────────────────────────────────┘

  사이드 경로:
  ───────────
  PROCESSING ──── Drop ──────► READY (worker_id 초기화 + dropImageList에 추가)
  any status ──── Discard ───► DISCARD (discard_reason 기록)
```

---

## Startup 흐름

```
앱 시작
  │
  ├─ QTimer.singleShot(100ms) → _showStartupDialogs()
  │
  ├─ 1. LoginDialog → user_id 획득
  │     └─ 취소 시 앱 종료
  │
  ├─ 2. AuthorityChecker.check_authority(user_id)
  │     ├─ 사용자 존재 → user_data 반환
  │     └─ 미존재 → DEFAULT_DATA로 생성 후 반환
  │
  ├─ 3. 세션 복구 확인: _load_session_info()
  │     ├─ 세션 존재 & user_id 일치
  │     │     → 모드/상태 복원 → loadFile() → 타이머/세션 재설정
  │     └─ 세션 없거나 user 불일치 → _selectModeAndApply()
  │
  └─ 4. _selectModeAndApply()
        ├─ ModeSelectionDialog → mode 선택 (취소 시 앱 종료)
        │     ├─ review 선택 시 → user_data['reviewer']=True 필요
        │     └─ final_review 선택 시 → user_data['finalReviewer']=True 필요
        └─ _applyModeSettings(mode) → UI 구성
```

---

## 사용자 데이터 (AuthorityChecker)

```json
{
  "name": "",
  "reviewer": false,
  "finalReviewer": false,
  "supervisor": false,
  "5-generation": false,
  "dropCount": 0,
  "dropImageList": []
}
```

| 필드 | 설명 |
|------|------|
| `reviewer` | Review 모드 접근 권한 |
| `finalReviewer` | Final Review 모드 접근 권한 |
| `supervisor` | 클래스 타입 필터 우회 (모든 classType 로드 가능) |
| `5-generation` | FrontViewSegmentation 전용 작업자 |
| `dropCount` | 누적 Drop 횟수 (3회 제한) |
| `dropImageList` | Drop한 이미지명 목록 (재로드 방지) |

---

## 액션 핸들러

### 태스크 로드 (`loadTaskAction`)

```
사용자가 [태스크 로드] 클릭
  │
  ├─ 가드: 이미지 이미 로드됨? → 경고 후 반환
  │
  ├─ 로딩 커서 표시
  │
  ├─ LoadTaskWorker(mode, user_id, processing_dir,
  │     is_5_generation, is_supervisor, drop_image_list) 시작
  │     │
  │     ├─ 소스 상태로 후보 검색 (LOAD_SOURCE_STATUSES[mode])
  │     │     └─ review 모드: workerId ≠ 현재 user (자기 작업 자기 리뷰 방지)
  │     ├─ 클래스 타입 필터링 (_filter_by_class_type)
  │     │     ├─ supervisor → 전체 허용
  │     │     ├─ 5-generation → FrontViewSegmentation만
  │     │     └─ 일반 → FrontViewSegmentation 제외
  │     ├─ Drop 이미지 필터링 (_filter_by_drop_list)
  │     │     └─ dropImageList에 포함된 imageName 제외
  │     ├─ FIFO 정렬 (createdAt ASC) → 가장 오래된 항목 선택
  │     ├─ Claim & Verify (최대 3회 재시도, 300ms 대기)
  │     │     └─ update_document(doc_id, {status, assignedAt, user_field})
  │     │        → 재조회 → user_field == self.user_id 검증
  │     └─ 파일 다운로드 (image, json, encrypt, comment) → processing_dir
  │
  ├─ 성공 시 → _on_load_task_finished()
  │     ├─ current_doc_id, current_task_status, current_document 설정
  │     ├─ loadFile(local_image_path)
  │     ├─ get_target_class → choose_labels_class
  │     └─ 데드라인 타이머 시작 + 세션 저장
  │
  └─ 에러 시 → _on_firebase_error() → 경고 다이얼로그
```

**모드별 소스 상태:**

| 모드           | 소스 상태                                         | 다음 상태                     |
|----------------|--------------------------------------------------|-------------------------------|
| labeling       | `ready`                                          | `processing`                  |
| review         | `request_review`, `finished_modify`              | `reviewing` / `re_reviewing`  |
| final_review   | `request_final_review`                           | `final_reviewing`             |

### 수정 로드 (`loadModifyTaskAction`)

```
Worker 전용. 필터: source_statuses=[MODIFY], user_filter_field='workerId'
→ 자기 태스크만 로드. 다음 상태: MODIFYING. 이후 흐름은 태스크 로드와 동일.
※ dropImageList 필터 미적용 (자신이 작업한 문서 수정이므로 제외 불필요)
```

### 연기 로드 (`loadPostponeTaskAction`)

```
사용자가 [연기 로드] 클릭
  │
  ├─ LoadPostponeWorker(user_id, processing_dir) 시작
  │     └─ get_documents_by_status_and_user(POSTPONE, workerId, user_id)
  │        (파일 다운로드 없이 목록만 반환)
  │
  ├─ 성공 시 → _on_load_postpone_list_finished()
  │     ├─ 인라인 QDialog로 연기 태스크 목록 표시
  │     ├─ 사용자가 태스크 선택 (더블클릭)
  │     └─ RestorePostponeWorker(selected_doc, user_id, processing_dir) 시작
  │           ├─ postpone/{user_id}/{folder}/{filename} 경로에서 다운로드
  │           │     (image 필수, json/encrypt/comment optional)
  │           └─ update_document(doc_id, {status=processing, assignedAt})
  │
  └─ 복원 성공 시 → _on_restore_postpone_finished()
        ├─ current_task_status = PROCESSING (고정)
        └─ loadFile()
```

### 제출 (`submitTaskAction`)

```
사용자가 [제출] 클릭
  │
  ├─ 가드: 이미지 없음 / doc_id 없음 → 경고 후 반환
  │
  ├─ 확인 다이얼로그 (라벨 없으면 빈 주석 경고)
  │
  ├─ saveFile() 로컬 저장
  ├─ load_time 파일 삭제
  │
  ├─ SubmitTaskWorker(doc_id, current_status, processing_dir,
  │     basename, mode, user_id) 시작
  │     │
  │     ├─ 타임스탬프 기반 스토리지 경로: {type}/{YYYYMMDDHHMMSS}/{filename}
  │     │     image   → image/{ts}/{basename}{ext}
  │     │     json    → json/{ts}/{basename}.json
  │     │     encrypt → encrypt/{ts}/{basename}_encrypt.bin
  │     │     comment → comment/{ts}/{basename}_comments.json (없으면 경로 비움)
  │     │
  │     ├─ 특수 로직: REVIEWING 상태에서 코멘트 파일 없으면
  │     │     MODIFY 건너뛰고 바로 REQUEST_FINAL_REVIEW로 전이
  │     │
  │     ├─ STATUS_TRANSITIONS로 다음 상태 결정
  │     ├─ update_document(doc_id, {status, updatedAt, storage_paths})
  │     └─ user_id 있으면 postpone 스토리지 잔여 파일 삭제
  │
  ├─ 성공 시 → _on_submit_finished()
  │     ├─ 세션 초기화 + 로컬 파일 정리 (_cleanup_processing_files)
  │     ├─ Firebase 상태 초기화
  │     ├─ comment_widget 초기화
  │     └─ UI 초기화 (toggleActions(False), canvas 비활성화)
  │
  └─ 에러 시 → _on_firebase_error()
```

**제출 상태 전환:**

| 현재 상태           | 다음 상태                 | 비고                          |
|---------------------|---------------------------|-------------------------------|
| `processing`        | `request_review`          |                               |
| `modifying`         | `finished_modify`         |                               |
| `reviewing`         | `modify`                  | 코멘트 없으면 → `request_final_review` |
| `re_reviewing`      | `request_final_review`    |                               |
| `final_reviewing`   | `ready_gt`                | 이후 외부 프로그램에서 처리   |

### 연기 (`postponeTaskAction`)

```
사용자가 [연기] 클릭
  │
  ├─ 가드: doc_id 없음 → 경고
  ├─ 확인 다이얼로그
  │
  ├─ saveFile() 로컬 저장
  │
  ├─ PostponeTaskWorker(doc_id, user_id, processing_dir, basename) 시작
  │     ├─ postpone/{user_id}/{folder}/{filename}에 파일 업로드
  │     └─ update_document(doc_id, {status=postpone, updatedAt})
  │
  └─ 성공 시 → _on_postpone_finished()
        └─ 세션/파일 정리 + 상태 초기화
```

### Drop (`dropTaskAction`)

```
사용자가 [태스크 Drop] 클릭
  │
  ├─ 가드: doc_id 없음 → 경고
  ├─ Drop 횟수 확인 (current_user_data['dropCount'])
  │     └─ ≥3회 → 거부
  ├─ 확인 다이얼로그
  │
  ├─ DropTaskWorker(doc_id, mode, user_id, drop_count, drop_image_list) 시작
  │     ├─ update_document(doc_id, {status=ready, user_field='', assignedAt='', updatedAt})
  │     └─ update_user(user_id, {dropCount: +1, dropImageList: +[doc_id]})
  │
  └─ 성공 시 → _on_drop_finished()
        ├─ current_user_data['dropCount'] 로컬 동기화
        ├─ current_user_data['dropImageList'] 로컬 동기화
        └─ 세션/파일 정리 + 상태 초기화
```

### Discard (`discardTaskAction`)

```
사용자가 [태스크 Discard] 클릭
  │
  ├─ 가드: doc_id 없음 → 경고
  ├─ DiscardDialog → 사유 입력 (필수)
  │
  ├─ DiscardTaskWorker(doc_id, reason) 시작
  │     └─ update_document(doc_id, {status=discard, discardReason, updatedAt})
  │
  └─ 성공 시 → _on_discard_finished()
        └─ 세션/파일 정리 + 상태 초기화
```

### Check Labels (`check_labels`)

```
사용자가 [Administrator > Check Labels] 클릭
  │
  ├─ 가드: self.filename is None → "No image loaded." 경고 후 반환
  │
  ├─ Lazy Init: ImagePopup 미존재 시
  │     └─ ImagePopup(parent=self, folder_path=os.path.dirname(self.filename)) 생성
  │
  ├─ _classType에 따라 위젯 상태 설정
  │     ├─ segmentation → masked_widget + overlayed_widget 활성화
  │     └─ detection    → object_widget 활성화
  │
  └─ self.ImagePopup.popUp(self.filename, True)
        └─ processing_dir 하위 masked_image/, overlayed_image/ 에서 이미지 검색 후 팝업 표시
```

---

## 필터링 로직

### 1. 클래스 타입 필터 (`_filter_by_class_type`)

```python
supervisor=True  → 전체 허용
5-generation=True → FrontViewSegmentation만
일반 Worker       → FrontViewSegmentation 제외
```

### 2. Drop 이미지 필터 (`_filter_by_drop_list`)

```python
dropImageList가 비어있으면 → 필터 없음
그 외 → imageName이 dropImageList에 포함된 후보 제외
```

**적용 범위:**
- `loadTaskAction` (일반 로드): **적용 O**
- `loadModifyTaskAction` (수정 로드): 적용 X — 자신이 작업한 문서 수정이므로 제외 불필요
- `loadPostponeTaskAction` (연기 로드): 적용 X — 자신이 보류한 문서이므로 제외 불필요

### 3. Reviewer 자기 작업 배제

```python
mode == 'review' → workerId ≠ current_user_id 조건
(Reviewer가 자신이 작업한 태스크 검토 방지)

# REQUEST_REVIEW 상태에서 추가 적용
reviewerId == '' 조건
(이미 다른 Reviewer가 Claim한 문서 배제 — Race Condition 방어)
```

---

## 로컬 파일 정리 (`_cleanup_processing_files`)

submit, postpone, drop, discard 완료 시 공통 호출.

```
_cleanup_processing_files()
  │
  ├─ processing_dir/{basename}* 패턴 매칭 파일 삭제
  │
  └─ 생성된 이미지 디렉토리 삭제 (shutil.rmtree)
        ├─ processing_dir/masked_image/
        └─ processing_dir/overlayed_image/
```

---

## 모드별 버튼/UI 표시

| 버튼/UI          | Worker (labeling) | Reviewer (review) | Supervisor (final_review) |
|------------------|:-----------------:|:-----------------:|:-------------------------:|
| 태스크 로드      | O                 | O                 | O                         |
| 수정 로드        | O                 | X                 | X                         |
| 연기 로드        | O                 | X                 | X                         |
| 제출             | O                 | O                 | O                         |
| 연기             | O                 | X                 | X                         |
| Drop             | O                 | X                 | X                         |
| Discard          | O                 | O                 | O                         |
| comment_dock     | O (read-only)     | O (editable)      | O (editable)              |
| shape_dock       | O                 | O                 | O                         |
| flag/label/file  | X                 | X                 | X                         |

---

## 스토리지 경로 규칙

| 타입      | 업로드 경로 (타임스탬프 포함)                          | 연기 경로                                              |
|-----------|-------------------------------------------------------|--------------------------------------------------------|
| Image     | `image/{YYYYMMDDHHMMSS}/{filename}`                   | `postpone/{user_id}/image/{filename}`                  |
| JSON      | `json/{YYYYMMDDHHMMSS}/{basename}.json`               | `postpone/{user_id}/json/{basename}.json`              |
| Encrypt   | `encrypt/{YYYYMMDDHHMMSS}/{basename}_encrypt.bin`     | `postpone/{user_id}/encrypt/{basename}_encrypt.bin`    |
| Comment   | `comment/{YYYYMMDDHHMMSS}/{basename}_comments.json`   | `postpone/{user_id}/comment/{basename}_comments.json`  |

---

## 세션 복구

세션 파일: `{processing_dir}/{basename}_session.json`

```json
{
  "image_filename": "example.jpg",
  "load_time": "2026-02-27T10:00:00",
  "mode": "labeling",
  "user_id": "user@example.com",
  "doc_id": "example.jpg",
  "task_status": "processing"
}
```

앱 시작 시:
1. 로그인 → `user_id` 획득
2. `processing_dir`에서 `*_session.json` 확인 (최신 mtime 기준)
3. 발견 & 사용자 일치 → `mode`, `doc_id`, `task_status` 복원, 이미지 로드
4. 없으면 → 모드 선택 다이얼로그 표시

---

## 데드라인 타이머

- 데드라인 = 로드 시각 + **48시간**
- 로드 시각은 `{basename}_load_time.txt`에 영속화
- 1초 간격 QTimer로 남은 시간 갱신
- `TaskInfoWidget`에 표시: 초록 → 노랑(6h 이하) → 빨강(2h 이하) → "Expired"

---

## 코멘트 시스템

코멘트 파일: `{basename}_comments.json`

```json
[
  {"user": "reviewer@example.com", "text": "Fix the bounding box on object #3"}
]
```

- Labeling 모드: 읽기 전용 (입력/버튼 숨김)
- Review / Final Review 모드: 입력 가능
- 우클릭 메뉴: 자기 코멘트만 삭제 가능
- 자기 코멘트는 `darkBlue`로 강조 표시

---

## 암호화 캐시 (`EncryptCache`)

- Fernet 대칭 암호화로 shape 정보(label, points) 암호화
- 작업자 변경 감지: `prev_worker` ≠ 현재 `worker_name` → shape 정보 갱신
- `{basename}_encrypt.bin`이 Firebase 스토리지 업로드/다운로드 대상
- 암호화 흐름: JSON → YAML 추출 → encrypt.bin 생성 → YAML 삭제

---

## 에러 처리

모든 워커는 `error(str)` 시그널을 발생시켜 `_on_firebase_error(msg)`로 전달:
- 커서 복원
- `QMessageBox.critical`로 에러 다이얼로그 표시
- Firebase 상태는 자동 롤백되지 않음 (부분 업로드 가능)
- 사용자가 직접 재시도해야 함

---

## DB 업데이트

`update_document`는 `PATCH /annotation` API를 통해 직접 필드를 업데이트한다.
`update_user`는 `PATCH /user` API를 통해 사용자 데이터를 업데이트한다.

---

## 알려진 제한사항

| 항목                 | 상태              | 비고                                                     |
|----------------------|-------------------|----------------------------------------------------------|
| PATCH API            | 배포 완료         | `PATCH /annotation`, `PATCH /user` 정상 사용 중           |
| 이메일 유효성 검사   | TODO              | `login_dialog._validate_id`: 하드코딩 허용 목록 사용 중  |
| 레이스 컨디션        | 완화됨            | Claim & Verify (300ms 대기 + 재조회) + `reviewerId` 빈 문서만 후보 허용. 완전한 방지는 아님 |
| 네트워크 장애        | 부분 상태         | 업로드 성공 + 상태 업데이트 실패 → 불일치 발생            |
| ConfigLoader 경로    | 하드코딩          | 절대 경로 사용 중. 이식성 문제                            |
| Fernet 키            | 하드코딩          | encrypt_cache.py 내 키 노출. 보안 이슈                   |
| PostponedListDialog  | 미사용            | import만 되어 있고 app.py에서 호출되지 않음               |
| 로컬 postpone 헬퍼   | 미사용            | `_move_files_to_postpone`, `_restore_postponed_files` 미호출 |

---

## 파일 아키텍처

```
labelme/firebase/
├── __init__.py              # 패키지 exports (TaskStatus, StoragePath, DB/Image managers)
├── authority_checker.py     # 사용자 권한/데이터 관리 (DEFAULT_DATA, check_authority, update_user)
├── config/
│   └── config.yaml          # base_url, bucket_name, collection
├── constants.py             # TaskStatus(Enum 12개), StoragePath, 전환 맵, 필드 맵
├── database_manager.py      # Firestore REST CRUD + FIFO 필터 헬퍼
├── image_manager.py         # GCS signed URL 업로드/다운로드 (ImageUpload, ImageDownload)
├── utils.py                 # ConfigLoader, APIManager
└── workers.py               # QThread 워커 (7개 클래스)
                             #   LoadTaskWorker, SubmitTaskWorker,
                             #   PostponeTaskWorker, LoadPostponeWorker,
                             #   RestorePostponeWorker, DropTaskWorker,
                             #   DiscardTaskWorker

labelme/widgets/
├── login_dialog.py          # 로그인 다이얼로그 (하드코딩 허용 ID)
├── mode_selection_dialog.py # 모드 선택 (labeling/review/final_review)
├── comment_widget.py        # 코멘트 위젯 (JSON 파일 기반 CRUD)
├── discard_dialog.py        # Discard 사유 입력 다이얼로그
├── task_info_widget.py      # 모드 배지 + 데드라인 타이머 표시
├── postponed_list_dialog.py # (미사용) 로컬 기반 연기 목록 위젯
└── image_popup.py           # masked/overlayed/object 이미지 팝업

labelme/utils/
└── encrypt_cache.py         # Fernet 기반 작업 이력 암호화 캐시

labelme/
└── app.py                   # MainWindow: startup → 액션 → 워커 → 콜백 → 정리
```

## Document 구조 (Firestore)

```json
{
  "imageName": "example.jpg",
  "status": "ready",
  "workerId": "",
  "reviewerId": "",
  "finalReviewerId": "",
  "createdAt": "2026-03-01T10:00:00",
  "assignedAt": "",
  "updatedAt": "",
  "storageImagePath": "",
  "storageJsonPath": "",
  "storageEncryptPath": "",
  "storageCommentPath": "",
  "classType": "",
  "discardReason": "",
  "isGt": ""
}
```
