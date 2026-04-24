# Project Brief — Polish Phase

> 이전 PROJECT_BRIEF.md (Phase 1~3 MVP 프로토타입)는 완료. 본 문서는 **Polish 단계** 전용 brief.
> 최종 GitHub 공개 전까지 순서: **Polish → Phase 4 → Phase 5 → 통합 테스트 → 멀티 OS 패키징 → GitHub 공개**.

## Project Name
Opiter — Polish Phase

## Final Goal
Phase 1~3에서 누적된 **18개 deferred polish 항목 + ARCHITECTURE.md 미구현 항목**을 일괄 해소하여 Opiter를 **일상 사용 가능 수준**으로 완성도 향상.

## Tech Stack & Environment
Phase 1~3과 동일 (Python 3.11+, PySide6 6.11.0, PyMuPDF 1.27, uv, pytest).

추가:
- `QSettings` 또는 XDG 호환 JSON (preferences.json)
- `QUndoStack` / `QUndoCommand`
- `QThreadPool` / `QRunnable` (async 썸네일)
- Qt Linguist (`.ts`/`.qm` 파이프라인)

## Main Features (13 sub-steps)

### A. 사용성 즉시 영향 (1차)
- **A-1**: 설정 영속화 (XDG `~/.config/opiter/preferences.json`) — 윈도우 크기/위치, 다크모드, 도크 상태, 줌 선호
- **A-2**: 최근 파일 (MRU) — File > Open Recent 서브메뉴, 최대 10개
- **A-3**: 주석 편집/삭제 + Pointer 도구 — 기존 주석 선택, Delete 키, 드래그로 이동
- **A-4**: 사용자 키매핑 커스터마이징 — Settings 다이얼로그 + `keymapping.json`

### B. UX 개선 (2차)
- **B-1**: 주석 색상/스타일 옵션 — 도구별 색상 선택, 기본값 영속화
- **B-2**: 주석 도구 툴바 — 아이콘 기반 빠른 접근
- **B-3**: 썸네일 크기 조절 — Pages 도크 헤더 슬라이더

### C. 아키텍처 (3차)
- **C-1**: Undo/Redo (`QUndoStack`) — 모든 mutating op 래핑
- **C-2**: 비동기 썸네일 + 디스크 캐싱 — `~/.cache/opiter/thumbnails/` (hash-based)
- **C-3**: i18n (한국어/영어) — Qt Linguist, 런타임 locale 감지
- **C-4**: 암호 PDF 비밀번호 prompt → 시도 → 재시도

### D. 환경/호환성 (4차)
- **D-1**: HiDPI + 윈도우 매니저 통합 — Aero Snap 검증, XCB 경고 억제
- **D-2**: 외부 PDF 뷰어 호환성 매트릭스 — Adobe/Foxit/Chrome/evince/VS Code, 주석 렌더링 차이 문서화

## Directory Structure
Phase 1~3 구조 유지. 신규 모듈:
```
src/opiter/
├── core/
│   ├── preferences.py     (신규, A-1)
│   ├── undo.py            (신규, C-1)
│   └── thumbnail_cache.py (신규, C-2)
├── ui/
│   ├── preferences_dialog.py (신규, A-4, B-1)
│   └── password_dialog.py    (신규, C-4)
└── utils/
    ├── paths.py           (확장, XDG config/cache)
    └── i18n.py            (확장, C-3)
```

## Completion Criteria

### 기능 검증 (각 sub-step)
- [ ] A-1: 앱 재시작 후 윈도우 크기/위치, 다크모드, 도크 상태 복원됨
- [ ] A-2: File > Open Recent 메뉴에 최근 10개 파일. 클릭하면 열림. 없는 파일은 자동 제거
- [ ] A-3: Pointer 도구 선택 후 기존 주석 클릭 → 선택 표시, Delete → 삭제, 드래그 → 이동. 저장 후 유지
- [ ] A-4: Settings 다이얼로그에서 단축키 변경 → 저장 → 재시작 후에도 유지
- [ ] B-1: 주석 색상 변경 후 적용 → 영속화
- [ ] B-2: 툴바에서 도구 전환 (Annotate 메뉴와 동등)
- [ ] B-3: 썸네일 슬라이더로 크기 조절 → 영속화
- [ ] C-1: 모든 mutating op에 Ctrl+Z / Ctrl+Y 작동
- [ ] C-2: 1000+ 페이지 PDF 열 때 UI 블로킹 없음, 썸네일 캐시 재사용
- [ ] C-3: 한국어 locale에서 UI 한국어 표시
- [ ] C-4: 암호 PDF 열기 → 비밀번호 입력 → 정상 열림
- [ ] D-1: 4K 모니터에서 UI 정상, XCB 경고 억제됨
- [ ] D-2: 주석 5종 각각 5개 뷰어에서 렌더링 검증 표 작성

### 기술
- [ ] 모든 신규 기능 pytest 커버리지 ≥ 기존 수준
- [ ] 기존 129 테스트 무회귀
- [ ] `uv run opiter` 정상 시작

### 품질
- [ ] Phase 1~3 브리프의 `docs/final_completion.md`의 deferred list 전부 해소 또는 해결 불가 사유 문서화
- [ ] Polish Self-Verification Report 작성

## Notes
- **Phase 4/5 선행 개발 없음** — polish만 완료 후 Phase 4 새 brief 시작
- **GitHub 공개는 최종 단계** — polish 완료해도 바로 push 안 함
- **사용자 manual 검증**: sub-step별 배치 모드 유지 (ABCD 그룹 단위로 묶어 검증 요청)

## Task Progress
- [x] **A-1**: Settings persistence (XDG) — window size/pos/max, dock, dark mode; atomic JSON write
- [x] **A-2**: Recent files menu — File > Open Recent, max 10, auto-prune missing, Clear Recent
- [x] **A-3**: Annotation edit/delete + Pointer tool — click-to-select w/ dashed bbox, Delete key, drag inside box to move
- [ ] **A-4**: Custom keymapping
- [ ] **B-1**: Annotation color/style options
- [ ] **B-2**: Annotation toolbar
- [ ] **B-3**: Thumbnail size adjustment
- [ ] **C-1**: Undo/Redo
- [ ] **C-2**: Async thumbnails + disk caching
- [ ] **C-3**: i18n
- [ ] **C-4**: Encrypted PDF password prompt
- [ ] **D-1**: HiDPI + window manager
- [ ] **D-2**: External viewer compatibility matrix
- [ ] **Polish SVR** + final verification
