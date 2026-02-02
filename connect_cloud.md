# Labelme Cloud-Native 고도화 설계 보고서 (Final Design Report)

본 문서는 Robotis 'Gaemi' 데이터 라벨링 효율화를 위해, 기존 로컬 기반 Labelme를 **Firebase 연동형(Cloud-Native)** 시스템으로 전환하기 위한 최종 기능 명세 및 고려 사항을 정의합니다.

---

## 1. 시스템 아키텍처 (System Architecture)

- **Core:** Firebase Storage (이미지/JSON 파일 저장소) + Firestore Database (상태 관리, 할당, 메타데이터)
- **Client:** Custom Labelme (Python/Qt)
- **Server-Side:** Admin Scheduler (마감 기한 관리, 좀비 데이터 정리)

## 2. 주요 고려 사항 및 정책 (Key Considerations)

### 2.1 데이터 무결성 및 동시성 (Data Integrity)
- **FIFO 할당:** 파일 선택창을 제거하고, DB 생성일(`created_at`) 기준 가장 오래된 작업을 자동 할당.
- **Locking:** Firestore Transaction을 사용하여 중복 할당 원천 차단.
- **Metadata 주입:** JSON 생성 시 DB에 저장된 `serviceArea`, `classType` 정보를 자동으로 주입하여 데이터 분류 보장.
- **경로 일치:** 로컬 저장 시 DB 파일명과 동일하게 저장하며, JSON 내 `imagePath`는 경로 없이 파일명만 기입.
- **데이터 경량화:** 저장 시 `imageData` 필드를 강제 `null` 처리하여 용량 최적화.

### 2.2 네트워크 및 로컬 자원 관리
- **Blocking Policy:** 인터넷 미연결 시 프로그램 진입 및 작업 제출 불가.
- **Clean-up:** 제출(Submit) 성공 시, 로컬의 원본 이미지, JSON, 오버레이 파일 즉시 삭제.
- **Zombie Task 방지:**
    - **Server:** 48시간 초과 작업의 상태를 강제 초기화(`ready`).
    - **Client:** 실행 시 만료된 작업이 로컬에 있다면 자동 삭제 및 접근 차단.

### 2.3 예외 처리 정책
- **빈 데이터 탐지:** 폴리곤(`shapes`)이 없는 상태로 제출 시도 시 경고 팝업 (실수 방지 vs Negative Sample 확인).
- **파일명 중복:** 배포 단계에서 유니크 파일명 보장 (별도 UUID 변환 없음).
- **Config 관리:** `labels.txt` 및 `yaml` 설정은 실행 파일 배포 버전을 따름 (서버 동기화 X).

---

## 3. Labelme 클라이언트 기능 명세 (Feature Specifications)

### 3.1 시작 및 진입 (Startup)
1.  **로그인 (Login):** 작업자 ID 입력 (Firestore `users` 컬렉션 매핑).
2.  **모드 선택 (Mode Selection):**
    * **Labeling:** 일반 작업 (`status: ready` → `processing`)
    * **Review:** 1차 검토 (`status: review_ready` → `processing`, 본인 작업 제외)
    * **Final Review:** 최종 검토 (`status: final_review_ready` → `processing`, 관리자 코드 필요)
3.  **자동 복구/정리 (Resume/Cleanup):**
    * 로컬 캐시 확인 → DB 상태 대조.
    * 유효한 작업이면 **자동 열기**, 만료되었으면 **삭제 후 모드 선택창 유지**.
4.  **버전 체크:** DB의 `min_version`보다 낮으면 실행 차단.

### 3.2 작업 공간 (Workspace UI)
1.  **커뮤니케이션 패널 (Comments):** 우측 사이드바에 채팅 형태의 메모창 추가 (DB 실시간 연동).
2.  **스마트 타이머:** 하단 상태바에 `마감까지 00시간 00분` 표시 (임박 시 붉은색 강조).

### 3.3 액션 로직 (Actions)
1.  **제출 및 다음 (Submit & Next):**
    * **Valid check:** 빈 JSON 여부 확인.
    * **Upload:** JSON 업로드 (Mask/Overlay 이미지 제외).
    * **Transition:** 현재 모드에 따라 상태 변경 (Labeling → `review_ready` → `final_review_ready` → `Done`).
        * *Note:* `Done` 상태 전환 시 `is_gt: true` 플래그 추가.
    * **Auto Load:** 로컬 파일 삭제 후 다음 작업 자동 다운로드.
2.  **작업 포기 (Drop Task):**
    * 개인 사정 등으로 작업 반납.
    * DB `status`를 `ready`로 원복.
    * 1일 반납 횟수 제한 (매일 자정 초기화).
3.  **작업 폐기 (Discard Task):**
    * 작업 불가능 이미지 (어두움, 가림 등).
    * **사유 입력 필수** (Dropdown + Text).
    * DB `status`를 `discarded`로 변경 (추후 관리자 확인용).

---

## 4. 데이터베이스 스키마 (Firestore Schema)

### `tasks` Collection
```json
{
  "document_id": "unique_filename.jpg",
  "status": "ready",  // ready, processing, review_ready, final_review_ready, done, discarded
  "worker_id": "user_id",
  "created_at": "Timestamp",
  "assigned_at": "Timestamp", // 마감 기한 계산용
  "storage_image_path": "raw_images/filename.jpg",
  "storage_json_path": "annotations/filename.json",
  "meta_service_area": "gangnam",
  "meta_class_type": "FrontView",
  "discard_reason": "string", // 폐기 시
  "is_gt": false, // 최종 완료 시 true
  "comments": [
    {"user": "reviewer1", "msg": "Modify mask", "time": "Timestamp"}
  ]
}
```

---

## 5. 작업 흐름도 (State Transition)

### Labeler: Ready → (Work) → Review Ready

### Reviewer: Review Ready → (Work) → Final Review Ready

### 반려 시: Review Ready → Ready (코멘트 첨부)

### Admin: Final Review Ready → (Work) → Done (GT Created)

### Common: 모든 단계에서 Discarded (폐기) 또는 Ready (포기/만료)로 이동 가능.