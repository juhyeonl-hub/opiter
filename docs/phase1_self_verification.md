# Phase 1 Self-Verification Report

> CLAUDE_en.md "Mandatory Self-Verification Report" 규정에 따라 작성.
> 본 보고서는 Phase 1 (기본 뷰어) 완료를 선언하기 위한 자기 검증.
> Phase 2/3 + 최종 통합 SVR은 별도 문서로 작성될 예정.

**Phase 1 범위 (PROJECT_BRIEF.md 발췌)**:
- 기본 뷰어 (PDF 열기, 렌더링, 페이지 네비)
- 줌 컨트롤
- 썸네일 사이드바
- 텍스트 검색
- 다크/라이트 모드

**Sub-step 진행**:
- Step 1: 프로젝트 셋업
- Step 2: 핵심 문서
- Step 3: 기본 앱 프레임 (윈도우 + 첫 페이지 렌더링)
- Step 4-1: 페이지 네비게이션 (+ 휠 edge-trigger)
- Step 4-2: 줌 컨트롤
- Step 4-3: 썸네일 사이드바
- Step 4-4: 텍스트 검색 (+ 4건 버그 수정)
- Step 4-5: 다크/라이트 모드 토글

---

## 1. 테스트 방법

### 1.1 자동화 테스트 (pytest)

**총 58개 테스트, 100% 통과** (1.24s, 2026-04-23 최종 실행)

| 모듈 | 케이스 수 | 검증 영역 |
|------|----------|-----------|
| `test_document.py` | 5 | open / 손상 PDF / 페이지 인덱스 경계 / page_size |
| `test_renderer.py` | 3 | 줌 스케일 차원 일치 / 잘못된 인덱스 |
| `test_viewer.py` | 23 | 네비게이션 / 휠 edge-trigger / 줌 / Ctrl+휠 |
| `test_thumbnail_panel.py` | 7 | populate / 클릭 시그널 / 선택 동기화 |
| `test_search.py` | 5 | 검색 정확성 / 대소문자 / 빈 쿼리 |
| `test_search_bar.py` | 8 | UI 동작 / 단축키 배선 / 카운터 포맷 |
| `test_main_window.py` | 2 | 회귀 (단축키 컨텍스트 / 재오픈 시 검색) |
| `test_theme.py` | 5 | 팔레트 전환 / QSS / 라운드트립 |

- **실행 환경**: `QT_QPA_PLATFORM=offscreen` (headless), Python 3.11.15, PySide6 6.11.0, PyMuPDF 1.27.2.2
- **명령**: `uv run pytest tests/`

### 1.2 End-to-End 스모크 테스트

각 sub-step 완료 직후 offscreen 모드에서 `MainWindow`를 부팅하고 직접 메서드를 호출하여 실제 출력 값(인디케이터 텍스트, 액션 활성 상태, 줌 값, 페이지 인덱스, 팔레트 색상)을 stdout에 출력하여 확인.

### 1.3 수동 GUI 검증 (사용자, WSLg + Wayland)

각 sub-step 완료 후 사용자에게 specific 체크리스트를 제공하고, 사용자가 직접 `uv run opiter`로 GUI를 띄워 클릭/타이핑/단축키로 확인. **총 7회 검증 round**:

1. Step 3: 윈도우 + 메뉴/툴바 + Open + 첫 페이지 렌더링 (스크린샷 1장 첨부)
2. Step 4-1: 페이지 네비게이션 (전부 정상)
3. Step 4-1 follow-up: 휠 edge-trigger (정상)
4. Step 4-2: 줌 (스크린샷 3장 첨부, 100/125/150% 확인)
5. Step 4-3: 썸네일 도크 (정상, 도크 드래그 부드러움 부족 보고)
6. Step 4-4: 검색 (4건 버그 발견 → fix → 재검증 통과)
7. Step 4-5: 다크모드 + 누적 종합 (전부 정상)

---

## 2. 테스트한 입력과 검증한 출력

### 2.1 자동화 테스트의 대표 입출력

| 입력 | 출력 (실측) |
|------|-------------|
| 정상 5페이지 PDF | `Document.page_count == 5` |
| garbage 바이트 파일 | `CorruptedPDFError` raise |
| 612×792 pt page at zoom=1.0 | 612×792 px 이미지 |
| 612×792 pt page at zoom=2.0 | 1224×1584 px 이미지 |
| `next_page()` from page 0 | `page_changed.emit(1, 5)`, current_page == 1 |
| `set_zoom(0.001)` | clamped to 0.10 |
| `set_zoom(9999)` | clamped to 10.0 |
| `zoom_in()` from 1.0 | 1.25 (다음 프리셋) |
| 페이지 하단 + wheel down (delta=-120) | next page, scroll top |
| 페이지 상단 + wheel up (delta=+120) | prev page, scroll bottom (연속 읽기) |
| 5페이지 PDF + search("hello") | 5개 SearchMatch, 페이지 [0,1,2,3,4] |
| search("HELLO") | 동일 결과 (대소문자 무시) |
| search("") / search("   ") | 빈 list |
| `apply_dark(app)` | Window 색상 lightness == 40 |
| `apply_light(app)` | platform 기본 팔레트 복귀, QSS 빈 문자열 |

### 2.2 사용자 인지 가능 동작 (수동 검증, samples/hello.pdf 사용)

- 윈도우 1024×768, 타이틀 "Opiter — hello.pdf"
- 메뉴바: File · **Edit** · View · Help (표준 순서로 재배치됨)
- 툴바: `Open │ Prev Next "1/5" │ ZoomOut "100%" ZoomIn`
- 좌측 도크 "Pages" — 5개 썸네일, 첫 번째 하이라이트
- 하단 검색바 (Ctrl+F 시 등장)
- 상태바 "Loaded 5 page(s)"
- About 다이얼로그: "Opiter v0.1.0"

### 2.3 단축키 동작 검증 (사용자 manual)

| 단축키 | 동작 | 결과 |
|--------|------|------|
| Ctrl+O | 파일 열기 | ✅ |
| PgDn / PgUp | 다음/이전 페이지 | ✅ |
| Home / End | 첫/마지막 페이지 | ✅ |
| Ctrl+G | Go to Page 다이얼로그 | ✅ |
| Ctrl++ / Ctrl+= | 줌 인 | ✅ |
| Ctrl+- | 줌 아웃 | ✅ |
| Ctrl+0 | Fit Page | ✅ |
| Ctrl+1 | Actual Size 100% | ✅ |
| Ctrl+2 | Fit Width | ✅ |
| Ctrl+휠 | 줌 인/아웃 (페이지 전환 차단) | ✅ |
| F4 | 썸네일 도크 토글 | ✅ |
| Ctrl+F | 검색바 열기 + 포커스 | ✅ |
| F3 / Shift+F3 | 다음/이전 매치 | ✅ (4-4 fix 후) |
| Esc | 검색바 닫기 | ✅ (4-4 fix 후) |
| Ctrl+Shift+D | 다크모드 토글 | ✅ |

---

## 3. 검증된 실패/엣지 케이스

### 3.1 코드 레벨 (자동 테스트)

- 손상된 PDF (garbage bytes) → `CorruptedPDFError` + 에러 다이얼로그
- 존재하지 않는 파일 → `CorruptedPDFError` + 다이얼로그
- 페이지 인덱스 음수 / 초과 → `IndexError`
- 빈 검색어 / 공백만 → 빈 결과 list
- 매칭 없는 검색어 → 빈 결과 + UI "Not found"
- 첫 페이지에서 `prev_page()` → no-op (시그널 미발화)
- 마지막 페이지에서 `next_page()` → no-op
- 마지막 페이지 하단 + 휠 down → 페이지 전환 안 함 (경계)
- 첫 페이지 상단 + 휠 up → 페이지 전환 안 함 (경계)
- `set_zoom(현재값과 동일)` → no signal
- 검색 종료 후 동일 쿼리 재시도 → 재검색 (회귀 테스트)
- Esc 키 위젯-with-children 컨텍스트 (offscreen 한계로 wiring만 검증)

### 3.2 수동 검증으로 확인된 엣지 케이스

- 도크 좌→우 이동 가능 (드래그 부드러움 부족 → 폴리싱 deferral)
- 검색 wrap-around: 마지막 매치(5/5) + F3 → 1/5
- 검색 wrap-around: 첫 매치(1/5) + Shift+F3 → 5/5
- 다크모드에서 검색 하이라이트 (PDF 페이지는 항상 흰색이므로 노랑/주황 가독성 유지)

---

## 4. 미검증 / 불충분 영역 (정직한 보고)

### 4.1 PROJECT_BRIEF.md 검증 예시 중 부분적 커버

| Brief 명시 | 실제 커버 |
|-----------|-----------|
| ✅ "10페이지 PDF로 끝까지 네비게이션" | 5페이지 PDF로 동등 검증 |
| ⚠️ "줌 50% / 200%" | 100/125/150% UI 시각 확인. 50/200%는 자동 테스트 (코드 동작) only |
| ⚠️ "the 같은 단어 검색 시 모든 매칭 위치 하이라이트" | "hello"로 검증. 다중 페이지 분포 OK. 단일 페이지 내 다중 매치는 자동 테스트만 |
| ✅ "다크모드 토글 시 UI 색상 즉시 전환" | 사용자 시각 확인 |

### 4.2 ARCHITECTURE.md 명시 사항이지만 Phase 1 범위 외로 deferral

- **비동기 썸네일 렌더링**: 현재 동기. ARCHITECTURE.md 명시 사항이지만 5페이지 테스트에서 문제 없음. 1000+ 페이지 PDF에서 잠시 블로킹 가능
- **썸네일 캐싱 (디스크 hash-based)**: 미구현. 매 PDF 오픈 시 재렌더링
- **i18n (한국어/영어)**: 영어 하드코딩. Qt Linguist 파이프라인 미설치
- **XDG 경로 기반 설정 영속화**: 미구현. 매 실행 라이트 모드 시작, 윈도우 크기 기본값
- **암호 PDF graceful handling**: 비밀번호 prompt 미구현. 현재는 경고 다이얼로그만 표시 (크래시는 안 됨)

### 4.3 사용자 환경에서만 가능한 검증 (자동화 불가)

- 실제 키보드 포커스가 QLineEdit에 있을 때 Esc 동작 — **사용자 manual 통과** ✅
- F3/Shift+F3 ApplicationShortcut 라우팅 — **사용자 manual 통과** ✅
- 도크 드래그 매끄러움 — 사용자 보고: 거칠음 (폴리싱 deferral)
- HiDPI 스케일링 — **미테스트**
- 매우 큰 PDF (수백 MB) 메모리/응답성 — **미테스트**
- 한글 폰트 PDF 렌더링 — **미테스트**
- 스캔 PDF (이미지 위주) 렌더링 — **미테스트**

### 4.4 자동화로 검증 못 한 UI 디테일

- 다크모드 색상 가독성 (사용자 만족도)
- 검색 하이라이트 노랑/주황 색상 강도 적절성
- 도크/툴바 레이아웃 비율
- 메뉴/액션 영문 텍스트의 자연스러움

### 4.5 누적 deferred polish 항목 (Phase 1~3 종료 후 일괄 처리 예정)

1. XCB mouse grab 경고 (WSLg 메뉴바 hover)
2. 도크 드래그 부드러움
3. HiDPI 스케일링
4. 윈도우 크기 영속화
5. **최근 파일 (MRU) 메뉴**
6. 다크모드 영속화
7. UI/UX 일반 폴리싱 (레이아웃, 아이콘, 색상)

---

## 5. 결론 및 다음 단계

### 5.1 Phase 1 완료 선언 체크리스트 (CLAUDE_en.md "Final Completion Declaration Conditions" 적용)

본 SVR은 **Phase 1 sub-completion** 선언으로, 전체 프로젝트의 최종 완료 (Step 10)는 아직 남아 있음.

- [x] Phase 1 모든 sub-step (4-1 ~ 4-5) 코드 구현
- [x] Build successful (`uv sync` OK, 모든 import OK)
- [x] 실제 실행 결과 사용자 직접 확인 (5페이지 PDF로 모든 기능)
- [x] 결과가 PROJECT_BRIEF.md의 Phase 1 spec과 일치
- [x] 모든 `[ASSUMPTION]` 사용자에게 보고 (sub-step별로 분산 보고)
- [x] PROJECT_BRIEF.md의 Step 1 ~ 4-5 체크박스 모두 체크
- [x] 본 SVR 작성 (이 문서)

### 5.2 통계

- **총 코드 라인**: 1,804 (src + tests, 빈 줄/주석 포함)
- **테스트 케이스**: 58개, 100% 통과
- **Git 커밋**: 10개 (Step 1 ~ Step 4-5 + 1 follow-up fix)
- **소요 sub-step**: 8개 (Step 1, 2, 3, 4-1, 4-1f/u, 4-2, 4-3, 4-4, 4-4f/u, 4-5)
- **사용자 수동 검증 round**: 7회

### 5.3 다음 단계 옵션

1. **Phase 2 (페이지 조작) 시작 — Step 6** 권장
   - 이유: brief의 "Step 10: 최종 통합 테스트" 시점에 Phase 1~3 폴리싱 + 큰/스캔/한글 PDF 검증을 일괄 수행하는 것이 정합
2. **Phase 1 폴리싱 먼저** — 4.5의 deferred 7개 항목 중 일부 처리
3. **Phase 1 보강 검증** — 4.1/4.3의 미검증 항목 (대용량/한글/스캔 PDF, HiDPI) 추가 검증

**권장: 옵션 1 (Phase 2 진행)**.
