# AGENTS.md — Autonomous Agent Operating Manual

> **SEVERITY: CRITICAL** — Every rule in this document is **NON-NEGOTIABLE**.
> Violation of any Hard Constraint is grounds for immediate rollback.
> Read this file **IN FULL** before touching a single line of code.

---

## 1. Project Overview

Custom enterprise annotation platform built on [wkentaro/labelme](https://github.com/wkentaro/labelme) v5.0.1.
Integrates a **Firebase-backed cloud-native workflow** (Worker → Reviewer → Final Reviewer → Supervisor) with multi-role authentication, task state machine, working-time tracking, and encrypted audit trails.
AI auto-labeling infrastructure exists via `probability` fields on shapes; direct ML model integration is planned.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| **GUI Framework** | PyQt5 / PySide2 via `qtpy` abstraction layer |
| **Language** | Python 3.8+ |
| **Image Processing** | OpenCV (`cv2` ≥ 4.6.0), Pillow, imgviz |
| **Data Format** | JSON (Labelme schema), YAML (config) |
| **Networking** | `requests` (HTTP REST to Firebase) |
| **Encryption** | `cryptography.Fernet` (symmetric) |
| **Threading** | `QThread` + Signal/Slot (NEVER `threading.Thread`) |
| **Config** | PyYAML, `default_config.yaml` |
| **AI (planned)** | PyTorch 2.x (device-agnostic, AMP) |

---

## 3. Directory Structure & Architecture

```
labelme/                          # Root package
├── __init__.py                   # Version: 5.0.1
├── __main__.py                   # Entry point
├── app.py                        # ★ MainWindow — THE core file (~4000 LOC)
├── label_file.py                 # ★ JSON I/O — schema-critical
├── shape.py                      # ★ Shape geometry + rendering
├── logger.py                     # Logging config
├── testing.py                    # Test helpers
│
├── config/
│   ├── __init__.py
│   └── default_config.yaml       # ★ Labels, shortcuts, shape colors, dock visibility
│
├── widgets/                      # UI components ONLY — no business logic here
│   ├── canvas.py                 # ★ Drawing canvas — signals: zoomRequest, newShape, etc.
│   ├── label_dialog.py           # Label input/selection
│   ├── label_list_widget.py      # Shape list dock
│   ├── comment_widget.py         # Multi-user comment system
│   ├── task_info_widget.py       # Mode badge + deadline timer
│   ├── image_popup.py            # Masked/overlay image viewer
│   ├── login_dialog.py           # Authentication dialog
│   ├── mode_selection_dialog.py  # Labeling/Review/Final Review selector
│   ├── loading_dialog.py         # Animated loading indicator
│   ├── discard_dialog.py         # Task rejection with reason
│   ├── postponed_list_dialog.py  # Postponed task restoration (dual mode: dir-scan / list-based)
│   ├── work_history_dialog.py    # Work analytics by round/mode
│   └── ...                       # Other standard Labelme widgets
│
├── utils/                        # Pure utility functions — stateless, no Qt imports preferred
│   ├── image.py                  # EXIF, base64, image conversion
│   ├── shape.py                  # Mask ↔ polygon conversion
│   ├── draw.py                   # Rendering helpers
│   ├── qt.py                     # Qt helper functions
│   ├── version_checker.py        # GitHub release version check
│   ├── path_utils.py             # Path manipulation
│   ├── measure_working_time.py   # Work time tracking + encryption
│   └── encrypt_cache.py          # Fernet encrypt/decrypt + YAML cache
│
├── firebase/                     # Cloud integration layer — network I/O lives here
│   ├── constants.py              # ★ TaskStatus enum, state transitions, role maps
│   ├── database_manager.py       # REST API calls (CRUD)
│   ├── image_manager.py          # Image upload/download (signed URLs)
│   ├── authority_checker.py      # User auth/role validation
│   ├── workers.py                # ★ QThread workers — async Firebase operations
│   ├── utils.py                  # ConfigLoader (YAML)
│   └── config/
│       └── config.yaml           # ★ Firebase API endpoints — NEVER commit secrets
│
├── cli/                          # Command-line utilities
│   └── ...                       # draw_json, json_to_dataset, etc.
│
└── icons/                        # Icon resources
```

### 3.1 Separation of Concerns — ABSOLUTE LAW

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FORBIDDEN ZONES                             │
│                                                                     │
│  widgets/*.py  →  NEVER contains: HTTP calls, DB queries,          │
│                   file encryption, model inference, state machine   │
│                                                                     │
│  firebase/*.py →  NEVER contains: QPainter, QWidget subclassing,   │
│                   direct UI manipulation, canvas drawing            │
│                                                                     │
│  utils/*.py    →  NEVER contains: QThread, Signal/Slot definitions,│
│                   Firebase API calls, widget instantiation          │
└─────────────────────────────────────────────────────────────────────┘
```

| Layer | Allowed Imports | Forbidden Imports |
|---|---|---|
| `widgets/` | `qtpy`, `labelme.shape`, `labelme.utils.*` | `labelme.firebase.*`, `requests` |
| `firebase/` | `qtpy.QtCore` (QThread/Signal only), `requests`, `labelme.firebase.*` | `qtpy.QtWidgets`, `qtpy.QtGui`, `labelme.widgets.*` |
| `utils/` | Standard lib, `numpy`, `PIL`, `cv2`, `yaml`, `cryptography` | `qtpy.QtWidgets`, `labelme.firebase.*` |
| `app.py` | Everything (orchestrator) | — (but see Hard Constraint #8) |

> **⚠ Known Technical Debt (DO NOT EXPAND):**
> The following files violate separation of concerns and are scheduled for refactoring.
> Do NOT use these as reference patterns. Do NOT add new violations following these precedents.
>
> | File | Violation | Correct Approach |
> |---|---|---|
> | `widgets/login_dialog.py` | Imports `firebase.authority_checker`, makes sync HTTP call in UI thread | Should delegate to a `QThread` worker |
> | `widgets/mode_selection_dialog.py` | Imports `firebase.constants`, `firebase.database_manager`, makes sync DB call | Should delegate to a `QThread` worker |
>
> **Resolved Technical Debt:**
>
> | Date | File | Resolution |
> |---|---|---|
> | 2026-04-07 | `app.py` → `submitTaskAction` | Moved `EncryptCache.run_single()` from main GUI thread to `SubmitTaskWorker.execute()` (HC-01 compliance). Worker creates its own `EncryptCache` instance to avoid shared mutable state across threads. |
> | 2026-04-07 | `app.py` → `_on_load_postpone_list_finished` | Replaced 25-line inline `QDialog` with `PostponedListDialog` widget. Dialog now supports dual mode: directory-scan (`postpone_dir` + `user_id`) and list-based (`image_names` param from Firebase). |

### 3.2 Application Architecture Pattern

**ALL asynchronous operations MUST follow this exact flow:**

```
User Action (click/shortcut)
    │
    ▼
MainWindow method (app.py)
    │
    ├─ (1) Validate input / show confirmation dialog
    │
    ├─ (2) Show LoadingDialog
    │
    ├─ (3) Instantiate Worker(QThread)
    │       ├─ worker.finished.connect(self._on_<action>_finished)
    │       ├─ worker.error.connect(self._on_firebase_error)
    │       └─ worker.start()
    │
    ▼
Worker.execute() — runs in BACKGROUND THREAD
    │
    ├─ Network I/O, file I/O, heavy computation
    │
    ├─ NEVER touch: self.canvas, self.labelList, any QWidget
    │
    └─ Emit: self.finished.emit(result_dict) or self.error.emit(msg)
         │
         ▼
    Slot in MainWindow (MAIN THREAD)
         │
         ├─ Update UI (canvas, docks, status bar)
         ├─ Hide LoadingDialog
         └─ Handle errors gracefully
```

### 3.3 Adding New Features — Mandatory Steps

When adding a new feature (widget, tool, or integration), you **MUST** follow these steps **in order**:

| Step | Action | Verify |
|---|---|---|
| 1 | Read target directory `CONTEXT.md` | Understand existing components |
| 2 | Find a **Reference Implementation** (see HC #10) | Never invent patterns from scratch |
| 3 | Impact Scope Assessment (see HC #9) | Report blast radius to user |
| 4 | Write the code following Separation of Concerns | Layer violations = instant FAIL |
| 5 | Wire Signal/Slot in `app.py` | Follow lifecycle rules (HC #3) |
| 6 | Run Code Review Agent (HC #7) | PASS required before proceeding |
| 7 | Run tests + lint | All green |
| 8 | Update `CONTEXT.md` + `CONTEXT_KO.md` | Keep docs synchronized |
| 9 | Request user approval if core files touched | HC #8 |

---

## 4. Hard Constraints

> **These are ABSOLUTE. There are no exceptions. There are no "just this once" scenarios.**

---

### HC-01: No Main Thread Blocking

**Rule:** The main GUI thread (where `QApplication.exec_()` runs) **MUST NEVER** execute:
- AI/ML model inference (any duration)
- HTTP requests (`requests.get/post/put/delete`)
- File operations > 1MB (read/write)
- Image encoding/decoding of large files
- `time.sleep()` > 100ms
- Any loop whose iteration count depends on external data

**Enforcement:**
```python
# CORRECT — background thread
worker = LoadTaskWorker(mode, user_id, processing_dir)
worker.finished.connect(self._on_load_task_finished)
worker.error.connect(self._on_firebase_error)
worker.start()

# FATAL VIOLATION — blocks UI
response = requests.get(url)  # IN MAIN THREAD
result = model.predict(image)  # IN MAIN THREAD
```

**If you need to run heavy computation:**
1. Create a `QThread` subclass in the appropriate module (`firebase/workers.py` for network, new `workers.py` in target module for computation)
2. Emit results via `Signal`
3. Update UI only in the connected `Slot` (main thread)

**Thread-Safety for Shared Objects:**
When passing utility objects (e.g., `EncryptCache`) to a `QThread` worker, **NEVER** share a mutable instance across threads. Instead, create a new instance inside `execute()` using lazy import to avoid state corruption:
```python
# CORRECT — isolated instance per worker
def execute(self):
    from labelme.utils.encrypt_cache import EncryptCache
    encrypt = EncryptCache()
    encrypt.run_single(path, json_path, worker_name=self.user_id)

# WRONG — shared mutable instance, race condition risk
def execute(self):
    self.shared_encrypt.run_single(...)  # main thread may also use this
```

---

### HC-02: Strict JSON Format Compatibility

**Rule:** The Labelme JSON schema **MUST** remain backward-compatible with ALL existing annotation files.

**Protected Schema (label_file.py):**
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

**You MUST NOT:**
- Remove or rename any existing key
- Change the type of any existing value
- Change the order of keys in `save()` output (tools downstream may depend on it)
- Add required keys (new keys MUST default to `null` or be omitted for backward compat)

**You MAY:**
- Add new **optional** keys with `null` default
- Add new values to `shape_type` enum (but register in `shape.py` and `canvas.py`)

**Auxiliary Schema — Comment File (`{image_stem}_comments.json`):**
```json
[
  { "user": "string (display name or user ID)", "text": "string" },
  ...
]
```
- Stored alongside annotation JSON by `widgets/comment_widget.py`
- Array of objects, each with `user` and `text` keys — do NOT add required keys

**Validation:** After ANY change to `label_file.py`, `shape.py`, or `comment_widget.py`, you MUST:
1. Load an existing annotation JSON and verify it parses without error
2. Save it back and verify the output is identical (round-trip test)

---

### HC-03: Qt Signal & Slot Lifecycle

**Rule:** Signal/Slot connections must be managed to prevent memory leaks, duplicate fires, and crash-on-deleted-object.

**3a. No Duplicate Connections:**
```python
# WRONG — if called twice, slot fires twice per signal
self.canvas.newShape.connect(self.newShape)
self.canvas.newShape.connect(self.newShape)  # DUPLICATE!

# CORRECT — disconnect before reconnecting, or connect only once in __init__
try:
    self.canvas.newShape.disconnect(self.newShape)
except (TypeError, RuntimeError):
    pass
self.canvas.newShape.connect(self.newShape)
```

**3b. Safe Thread Termination:**
```python
# CORRECT — always wait for thread to finish before destroying
if self.worker is not None:
    self.worker.quit()
    self.worker.wait(5000)  # 5s timeout
    if self.worker.isRunning():
        self.worker.terminate()  # last resort
    self.worker.deleteLater()
    self.worker = None
```

**3c. Lambda Slots — Prefer Named Methods or `functools.partial`:**

> **Note:** The current codebase (`app.py` lines ~496-536) uses lambdas for action connections.
> This is existing code — do NOT refactor it without explicit user request.
> For **NEW** connections, prefer named methods or `functools.partial` for disconnectability.

```python
# EXISTING (tolerated) — do not refactor unprompted
action.triggered.connect(lambda: self.toggleDrawMode(False, createMode="polygon"))

# PREFERRED for NEW code — disconnectable, no memory leak risk
from functools import partial
action.triggered.connect(partial(self.toggleDrawMode, False, createMode="polygon"))

# BEST for NEW code — named method
action.triggered.connect(self._on_create_polygon)
```

**3d. Cross-Thread Signal Safety:**
- Signals emitted from `QThread` to main thread slots are auto-queued (safe)
- NEVER use `Qt.DirectConnection` for cross-thread signals
- NEVER call `QWidget` methods from within `QThread.run()`

---

### HC-04: State Management — No Background UI Updates

**Rule:** Background threads **MUST NOT** directly read or write ANY UI state.

**Forbidden in QThread.run() / execute():**
```python
# ALL OF THESE ARE FATAL VIOLATIONS IN A BACKGROUND THREAD:
self.parent().canvas.shapes.append(shape)     # Modifying canvas
self.parent().labelList.addItem(item)          # Modifying widget
self.parent().setWindowTitle("...")            # Modifying window
self.parent().statusBar().showMessage("...")   # Modifying status bar
QMessageBox.warning(None, "Error", msg)        # Creating widget
QPixmap(path)                                  # QPixmap in non-GUI thread
```

**Correct Pattern:**
```python
# In QThread subclass:
class MyWorker(QThread):
    progress = Signal(int)         # Emit progress updates
    result_ready = Signal(dict)    # Emit final result
    error = Signal(str)            # Emit errors

    def run(self):
        # Only emit signals — NEVER touch widgets
        for i, item in enumerate(self.items):
            processed = self.process(item)
            self.progress.emit(i)
        self.result_ready.emit({'data': processed})

# In MainWindow (main thread):
self.worker.result_ready.connect(self._update_canvas_with_result)
```

---

### HC-05: CONTEXT.md Management

**Rule:** Every directory that contains functional code MUST have a `CONTEXT.md` (English) AND `CONTEXT_KO.md` (Korean mirror).

**Before starting work:**
1. Read `CONTEXT.md` in the target directory
2. If it does not exist, **create it** with the template below before writing any code
3. If it exists, verify it is up-to-date with the current code

**After completing work:**
1. Update `CONTEXT.md` to reflect your changes
2. Synchronize `CONTEXT_KO.md` with identical content translated to Korean
3. Both files MUST have identical structure and section headers

**Template:**
```markdown
# <Directory Name> — Context

## Purpose
<One paragraph: what this directory/module does>

## Key Files
| File | Responsibility | Signals/Slots | Dependencies |
|---|---|---|---|

## Architecture Notes
<Patterns, constraints, gotchas>

## Recent Changes
| Date | Change | Author/Agent |
|---|---|---|
```

---

### HC-06: AGENTS_GUIDE_KO.md Synchronization

**Rule:** A Korean-language mirror of this document MUST exist at `AGENTS_GUIDE_KO.md` in the project root.

- When `AGENTS.md` is created or modified, `AGENTS_GUIDE_KO.md` MUST be updated in the **same commit**
- Content must be semantically identical — translate all prose to Korean, keep code blocks and tables in English
- Section numbering and structure MUST match exactly
- If you cannot translate in the same operation, create a TODO item and flag the user

---

### HC-07: Mandatory Code Review Agent

**Rule:** Before presenting ANY code change to the user, you MUST spawn a self-review using the **"Strict Senior Code Reviewer"** persona.

**Review Checklist (ALL items must be evaluated):**

| # | Check | Category |
|---|---|---|
| 1 | No main-thread blocking (HC-01) | Threading |
| 2 | JSON schema compatibility (HC-02) | Data |
| 3 | Signal/Slot lifecycle correct (HC-03) | Memory |
| 4 | No background UI mutation (HC-04) | Threading |
| 5 | Separation of Concerns respected | Architecture |
| 6 | No hardcoded paths, secrets, or credentials | Security |
| 7 | Error handling present (no silent swallows) | Reliability |
| 8 | Follows existing code patterns/style | Consistency |
| 9 | `ament_flake8` compliant | Style |
| 10 | No unused imports or dead code | Cleanliness |

**Output Format (MANDATORY):**

```markdown
## Code Review Report

| Status | File | Line | Issue |
|---|---|---|---|
| PASS | widgets/my_widget.py | — | All checks passed |
| FAIL | firebase/workers.py | 42 | HC-01: requests.get() called in main thread |
| FAIL | app.py | 1337 | HC-03: Duplicate signal connection |
```

**On FAIL:**
1. Fix ALL failures
2. Re-run the review
3. Repeat until ALL rows show PASS
4. Only then present to user

---

### HC-08: User Approval Required — Protected Files

**Rule:** The following files require **explicit user approval** before ANY modification:

| File | Reason |
|---|---|
| `app.py` | Core application — single change can break entire tool |
| `label_file.py` | JSON schema — affects all saved/loaded annotations |
| `config/default_config.yaml` | User-facing configuration — affects all users |
| `firebase/config/config.yaml` | API endpoints — affects cloud connectivity |
| `firebase/constants.py` | State machine — incorrect transitions corrupt workflow |
| `shape.py` (root) | Shape geometry — affects rendering, saving, all tools |
| `setup.py` | Dependencies — affects installation for all users |
| `*.yaml` / `*.json` (config) | Configuration — affects runtime behavior |
| `AGENTS.md` | This file — affects all future agent behavior |
| `labelme/__init__.py` | Version — affects update checks |

**Workflow:**
1. Describe the intended change and its rationale
2. Show the exact diff (old → new)
3. List all files that import/depend on the modified file
4. **WAIT** for user to type approval
5. Only then apply the change

**NEVER** batch a protected file change with unprotected files in a single operation.

---

### HC-09: Impact Scope Assessment (Blast Radius)

**Rule:** Before modifying ANY file in the table below, you MUST perform a dependency analysis and present it to the user.

| Module | Typical Dependents |
|---|---|
| `widgets/canvas.py` | `app.py`, `shape.py`, all drawing operations |
| `shape.py` | `canvas.py`, `label_file.py`, `utils/shape.py`, `app.py` |
| `label_file.py` | `app.py`, all save/load operations, `firebase/workers.py` |
| `firebase/constants.py` | `firebase/workers.py`, `firebase/database_manager.py`, `app.py` |
| `firebase/workers.py` | `app.py` (all async operations) |
| `utils/image.py` | `label_file.py`, `app.py`, `cli/*` |

**Assessment Format:**
```markdown
## Impact Scope Assessment

**Target:** `widgets/canvas.py` — adding `newSignalName` signal
**Direct dependents:** app.py (connects signal on line 202)
**Transitive dependents:** None
**Risk:** LOW — additive change, no existing behavior modified
**Backward compatible:** YES
```

If risk is **MEDIUM** or **HIGH**, the change MUST be presented as a plan first (no code) and await user approval.

---

### HC-10: Reference Template — No Inventing Patterns

**Rule:** When adding new functionality, you MUST first identify and study an existing reference implementation.

| New Feature Type | Reference Implementation |
|---|---|
| New QThread Worker | `firebase/workers.py` → `LoadTaskWorker` |
| New Dialog Widget | `widgets/mode_selection_dialog.py`, `widgets/discard_dialog.py`, or `widgets/postponed_list_dialog.py` (dual-mode pattern) |
| New Dock Widget | `widgets/comment_widget.py` or `widgets/task_info_widget.py` |
| New Canvas Tool/Mode | `widgets/canvas.py` → `createMode` / `editMode` patterns |
| New Firebase API call | `firebase/database_manager.py` → existing methods |
| New CLI command | `cli/draw_json.py` |
| New Shape Type | `shape.py` → existing shape type handling in `paint()` |
| New Config Option | `config/default_config.yaml` → existing entries |
| New Signal/Slot | `app.py` lines 176-246 → existing connection patterns |

**Process:**
1. Read the reference implementation in full
2. Note its patterns: error handling, signal names, parameter conventions
3. Follow the same patterns in your new code
4. In your Code Review (HC-07), verify pattern consistency with the reference

---

## 5. Task Status State Machine

> Modifications to this state machine require user approval (HC-08).

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
               └───►│ POSTPONE  │ (any active state)
                    └───────────┘
                    ┌───────────┐
                    │  DISCARD  │ (reviewer rejection)
                    └───────────┘
```

---

## 6. Commands

### 6.1 Application

```bash
# Run the application
python -m labelme

# Run with specific image directory
python -m labelme /path/to/images

# Run with output directory
python -m labelme /path/to/images --output /path/to/output
```

### 6.2 Resource Compilation

> **Note:** This project currently loads icons directly from `labelme/icons/` directory
> without a `.qrc` resource file. The command below is only needed if a `.qrc` is introduced in the future.

```bash
# Compile Qt resources (only if a .qrc file exists)
pyrcc5 labelme/icons/resources.qrc -o labelme/icons/resources_rc.py
```

### 6.3 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/labelme_tests/test_app.py -v
python -m pytest tests/labelme_tests/utils_tests/ -v
python -m pytest tests/labelme_tests/widgets_tests/ -v

# Run with coverage
python -m pytest tests/ --cov=labelme --cov-report=term-missing
```

### 6.4 Linting

```bash
# ament_flake8 (primary linter for this project)
python -m flake8 labelme/ --max-line-length=120

# Type checking (if mypy is available)
python -m mypy labelme/ --ignore-missing-imports
```

### 6.5 Build & Install

```bash
# Development install
pip install -e .

# Build distribution
python setup.py sdist bdist_wheel
```

---

## 7. Workflow / Definition of Done

### 7.1 Pre-Work Checklist

Before writing ANY code, complete ALL of the following:

- [ ] **Read CONTEXT.md** in target directory (create if missing — HC-05)
- [ ] **Identify Reference Implementation** for the pattern you'll use (HC-10)
- [ ] **Impact Scope Assessment** if modifying shared modules (HC-09)
- [ ] **Check protected file list** — will you need user approval? (HC-08)
- [ ] **Plan threading model** — does this operation need a QThread? (HC-01)
- [ ] **Check JSON compatibility** — does this affect save/load? (HC-02)

### 7.2 Post-Work Checklist

After writing code, ALL of the following must be verified:

- [ ] **Thread Safety**: No blocking calls in main thread; no UI access from worker threads
- [ ] **JSON Round-Trip**: If `label_file.py` or `shape.py` was modified, load → save → load produces identical output
- [ ] **Signal/Slot Audit**: No duplicate connections; all workers have safe termination paths
- [ ] **Separation of Concerns**: No cross-layer imports violating Section 3.1
- [ ] **Code Review Agent**: Spawned reviewer, all rows PASS (HC-07)
- [ ] **Lint Clean**: `flake8` passes with zero warnings
- [ ] **Tests Pass**: `pytest tests/ -v` all green
- [ ] **CONTEXT.md Updated**: Both English and Korean versions (HC-05)
- [ ] **AGENTS_GUIDE_KO.md Synced**: If AGENTS.md was modified (HC-06)
- [ ] **User Approval Obtained**: For any protected file changes (HC-08)

### 7.3 Commit Rules

```
<type>(<scope>): <description>

Refs: #<issue_number>
```

- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Scope: module name (e.g., `widgets`, `firebase`, `canvas`, `label-file`)
- Atomic commits: one logical change per commit
- Commit messages in **English**

---

## 8. Emergency Procedures

### If you accidentally break JSON compatibility:
1. **STOP** immediately
2. `git diff label_file.py shape.py` — identify the breaking change
3. Revert the specific change
4. Verify with existing test annotation files in `tests/labelme_tests/data/`
5. Report to user

### If you cause a UI freeze:
1. Identify the blocking operation (likely an HTTP call or heavy computation in main thread)
2. Move it to a `QThread` worker following the pattern in `firebase/workers.py`
3. Wire with Signal/Slot per Section 3.2

### If you corrupt the task state machine:
1. Check `firebase/constants.py` — `STATUS_TRANSITIONS` and `LOAD_SOURCE_STATUSES`
2. Verify the transition is valid per the state diagram in Section 5
3. Invalid transitions can strand tasks — escalate to user immediately

---

## 9. Forbidden Actions — Zero Tolerance

| Action | Why | Consequence |
|---|---|---|
| `import threading` in any GUI code | Qt has its own threading; mixing causes undefined behavior | Immediate revert |
| `QPixmap` or `QImage` creation in `QThread` | Crashes — Qt GUI objects are main-thread-only | Immediate revert |
| Modifying `STATUS_TRANSITIONS` without approval | Can corrupt entire workflow pipeline | Immediate revert |
| Hardcoding Firebase URLs/tokens in source | Security violation | Immediate revert |
| Adding `imageData` as required field | Breaks all files saved with `store_data: false` | Immediate revert |
| `git push --force` to `main` | Destroys shared history | NEVER |
| Deleting test data in `tests/` | Breaks CI validation | NEVER |
| Adding `sleep()` in main thread for "timing" | UI freeze; use `QTimer` instead | Immediate revert |
| Catching `Exception` and passing silently | Hides bugs, corrupts state | Immediate revert |
| Writing print() for debugging (leave in code) | Use `logging.getLogger(__name__)` | Must remove before commit |

---

> **Final Warning:** This document is your operating contract.
> If a rule seems inconvenient, that means it's working.
> When in doubt, **ASK THE USER**. Silence is not consent.
