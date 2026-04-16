# PR 요약: feature-connect-firebase

**총 72개 파일 변경** (+8,140 / -483), **100개 이상 커밋**

---

## 1. Firebase 연동 (핵심 신규 기능)

신규 모듈: `labelme/firebase/`

| 파일 | 설명 |
|------|------|
| `authority_checker.py` | 사용자 인증/권한 관리 (reviewer, supervisor 등) |
| `database_manager.py` | Firebase Realtime DB CRUD (태스크 상태, 유저 데이터) |
| `image_manager.py` | Firebase Storage 이미지 업로드/다운로드 |
| `workers.py` | QThread 기반 비동기 워커 (Load, Submit, Postpone, Drop, Discard) |
| `constants.py` | TaskStatus, StoragePath, 상태 전이 맵 정의 |

---

## 2. 신규 UI 위젯 (8개)

`labelme/widgets/` 에 추가:

- **LoginDialog** - Firebase 로그인 UI
- **ModeSelectionDialog** - 작업 모드 선택 (어노테이션/리뷰)
- **CommentWidget** - 리뷰 코멘트 위젯
- **DiscardDialog** - 태스크 폐기 확인 다이얼로그
- **LoadingDialog** - 비동기 작업 로딩 인디케이터
- **TaskInfoWidget** - 현재 태스크 정보 표시
- **PostponedListDialog** - 보류 태스크 목록
- **WorkHistoryDialog** - 작업 이력 조회

---

## 3. app.py 대규모 확장 (+1,500줄)

`labelme/app.py` 주요 변경:

- Firebase 기반 **태스크 라이프사이클** 관리 (load -> annotate -> submit/postpone/drop/discard)
- **역할 기반 접근 제어** (worker, reviewer, finalReviewer, supervisor)
- **동시 접근 차단** 로직
- **편집 모드(Edit Mode)** 지원
- Firebase 워커 스레드 연동

---

## 4. 유틸리티 변경

| 파일 | 설명 |
|------|------|
| `encrypt_cache.py` (신규) | Fernet 암호화 기반 어노테이션 캐시 (작업자 변경 추적/치팅 방지) |
| `path_utils.py` (신규) | PyInstaller / 개발환경 크로스 플랫폼 경로 해석 |
| `measure_working_time.py` | `sys.path[0]` → `~/.config/labelme/` 유저 데이터 디렉토리로 마이그레이션 |
| `draw.py` | 폴리곤 마스크 렌더링을 PIL → **OpenCV `cv2.fillPoly`**로 전환 |
| `version_checker.py` | PyInstaller `_MEIPASS` 경로 지원 |

---

## 5. 빌드/배포

- `exec/build_labelme_windows.py` - Windows PyInstaller 빌드 스크립트 신규
- `exec/pyi_rth_*.py` - PyInstaller 런타임 훅 7개 추가

---

## 6. 설정/기타

- `class.yaml` - 클래스 정의 확장 (+270줄)
- `default_config.yaml` - 설정 항목 대폭 확장
- 코드베이스 전반 **한국어 → 영어 번역** (주석, 변수명)
- `AGENTS.md` 문서 추가
