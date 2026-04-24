# Phase 2 Self-Verification Report

> CLAUDE_en.md "Mandatory Self-Verification Report" 규정에 따라 작성.
> 본 보고서는 **Phase 2 (페이지 조작)** 완료 선언.
> Phase 3 + 최종 통합 SVR은 별도 문서로 작성 예정.

**Phase 2 범위 (PROJECT_BRIEF.md)**:
- 페이지 추가 / 삭제 / 순서 변경
- 페이지 회전 (90° 단위)
- PDF 합치기 (다중 입력 → 하나)
- PDF 나누기 (범위 / 낱장)
- PDF 추출 (특정 페이지 → 새 파일)

**Sub-step 진행**:
- 6-1: Save 인프라 + 페이지 회전
- 6-2: 페이지 삭제 + 빈 페이지 추가
- 6-3: 페이지 순서 변경 (썸네일 드래그)
- 6-4: PDF 추출 + 나누기 (by-range / per-page)
- 6-5: PDF 합치기

**범위 외 (의도적 deferral)**:
- Undo/Redo (`QUndoStack`) — Phase 2~3 종료 후 폴리싱 단계에서 일괄 도입
- 사용자 요청 누적 폴리싱 11종 (목록 §4.5)

---

## 1. 테스트 방법

### 1.1 자동화 테스트 (pytest)
**총 108개 테스트, 100% 통과** (1.55s, 2026-04-24 최종)

| 모듈 | 케이스 | Phase 2 신규 |
|------|--------|--------------|
| `test_document.py` | 22 | +14 (rotate, delete, insert, move, reorder, save 페이즈) |
| `test_renderer.py` | 3 | 0 |
| `test_viewer.py` | 23 | 0 |
| `test_thumbnail_panel.py` | 9 | +2 (drag mode, relabel) |
| `test_search.py` / `test_search_bar.py` | 5/8 | 0 |
| `test_main_window.py` | 3 | +1 (output dir 자동 mkdir) |
| `test_theme.py` | 5 | 0 |
| **`test_page_ops.py`** (신규) | **22** | **+22** (parser, extract, split, merge) |

### 1.2 End-to-End 스모크 테스트
각 sub-step + 모든 버그 fix 후 offscreen Qt 모드에서 직접 호출:
- Save/Save-As/회전 누적 + reload
- Insert/Delete + 1페이지 가드
- 드래그 시그널 → 모델 sync → relabel
- Extract/Split (per-page, by-range)
- Merge (3개 PDF, 페이지 순서 검증)

### 1.3 수동 GUI 검증 (사용자, WSLg)
- Step 6-1: rotate / save / save-as / `*` 마커 / close confirmation 전부 통과
- Step 6-2: insert / delete / 1페이지 가드 / 영속화 전부 통과
- Step 6-3: 드래그-드롭 반복 안정, save-reopen 영속화
- Step 6-4: extract OK, split per-page OK, split by-range는 dir 생성 버그 → fix 후 자체 검증
- Step 6-5: 사용자 미검증 (배치 모드 합의)

---

## 2. 테스트한 입력과 검증한 출력

### 2.1 자동화 (대표)

| 입력 | 검증된 출력 |
|------|-------------|
| 3p PDF + `delete_page(1)` | page_count=2, modified=True |
| 1p PDF + `delete_page(0)` | ValueError, 문서 무손상 |
| 2p PDF + `insert_blank_page(0)` | new_idx=1, page_count=3 |
| 200×300pt 페이지 + `insert_blank_page(0)` | 새 페이지 (200, 300) 상속 |
| 5p PDF + `move_page(1, 3)` | 텍스트 순서 [P1,P3,P4,P2,P5] |
| 5p PDF + `reorder_pages([3,1,2,0,4])` | 텍스트 [P4,P2,P3,P1,P5] |
| `parse_page_range_spec("1-3,5,2", 5)` | `[0,1,2,4,1]` (중복 보존) |
| `parse_page_range_spec("5-2", 5)` | ValueError (역순) |
| `parse_multi_range_spec("1-2;3;4-5", 5)` | `[[0,1],[2],[3,4]]` |
| 5p PDF + `extract_pages([0,2,4])` | 3p 출력, 마커 P1/P3/P5 일치, source 무손상 |
| 5p PDF + `split_by_groups([[0,1],[2],[3,4]])` | 3개 파일 (2/1/2 pages), 파일명 `out_1..3.pdf` |
| `merge_pdfs([a(2p), b(3p), c(1p)])` | 6p, 순서 [A1,A2,B1,B2,B3,C1], source 무손상 |
| Rotate → Save As → Rotate → Save | (회귀) PyMuPDF "incremental needs original file" 미발생 |
| 비존재 dir 입력 + `_prompt_output_directory` | 자동 mkdir, path 반환 |

### 2.2 사용자 인지 가능 동작 (수동, WSLg)

| 액션 | 결과 |
|------|------|
| Ctrl+R | 페이지 시계방향 90° 회전 + 타이틀 `*` |
| Ctrl+S | 회전 영속, `*` 제거 |
| Ctrl+Shift+S → 새 경로 | 새 파일 생성, 타이틀 새 이름 + `*` 제거 |
| Edit > Insert Blank Page After | 빈 페이지 1개 추가 + 뷰어 점프 |
| Ctrl+Delete + Yes | 현재 페이지 삭제 + 다음 페이지 표시 |
| 1페이지에서 Delete | 메뉴 회색 (가드) |
| 썸네일 드래그 | 순서 변경, 썸네일 5개 모두 유지 (이전엔 사라짐) |
| Edit > Extract Pages... | 사용자 입력 범위로 새 PDF 생성 |
| Edit > Split PDF Per Page | N개 파일 생성 (사용자 미검증 마지막 단계는 SVR 후) |

### 2.3 단축키 / 메뉴 신규 (Phase 2)

| 단축키 / 메뉴 | 동작 |
|---------------|------|
| Ctrl+S | Save (incremental) |
| Ctrl+Shift+S | Save As |
| Ctrl+R | Rotate Page Right (90°) |
| Ctrl+Shift+R | Rotate Page Left (-90°) |
| Ctrl+Delete | Delete Page (확인 다이얼로그) |
| Edit > Insert Blank Page After | 현재 페이지 다음 빈 페이지 |
| Edit > Extract Pages… | 범위 → 1 파일 |
| Edit > Split PDF by Range… | 다중 범위 → N 파일 |
| Edit > Split PDF Per Page | 페이지당 1 파일 |
| Edit > Merge PDFs… | 다중 입력 → 1 파일 (open doc 불필요) |

---

## 3. 검증된 실패/엣지 케이스

### 3.1 코드 레벨 (자동)
- Rotate 90° 비배수 → ValueError
- Rotate 누적: 90×4 = 0 (mod 360)
- Rotate 음수 (-90 → 270)
- Delete 마지막 1페이지 → ValueError + 문서 보존
- Delete 잘못된 인덱스 → IndexError
- Insert/Delete 후 검색 state 자동 reset (페이지 인덱스 무효화)
- Move 동일 인덱스 → no-op + modified 미설정
- Reorder identity (`[0..N-1]`) → no-op
- Reorder permutation 검증 (중복/길이/범위)
- Parser 빈 문자열 / out-of-range / 역범위 / 비숫자 → ValueError
- Multi-range parser 한 그룹이라도 invalid → 전체 실패
- Extract 빈 인덱스 → ValueError
- Split 미존재 출력 dir (core API) → ValueError; UI는 `_prompt_output_directory`로 자동 mkdir
- Merge 빈 입력 → ValueError
- Merge 단일 파일 → 복사본 (의도된 동작)

### 3.2 회귀 테스트로 박힌 버그 3건
| 버그 | 회귀 테스트 |
|------|-------------|
| Save-after-SaveAs incremental 실패 | `test_save_after_save_as_does_not_raise` |
| 썸네일 드래그 후 패널 비어 보임 | `test_relabel_after_reorder_resets_text_and_userrole` (UI 회귀) + `test_reorder_pages_*` (모델) |
| Split 출력 dir 생성 불가 | `test_prompt_output_directory_creates_missing_path` |

---

## 4. 미검증 / 불충분 영역 (정직한 보고)

### 4.1 Brief의 "Verification target" 매트릭스

| Brief 명시 | 실제 |
|-----------|------|
| "10페이지 PDF 5번 페이지 삭제 → 9페이지 결과" | ✅ 5p PDF로 동등 검증 (`test_delete_page_persists_after_save`) |
| "2개 PDF 합치기 → 페이지 수 합산 일치" | ✅ 3개 PDF 합치기로 동등 이상 검증 |
| "10페이지 PDF를 3+3+4로 나누기 → 3개 파일" | ✅ 5p PDF의 2+1+2 분할로 동등 검증 |
| "다른 뷰어로 결과 PDF 열어서 확인" | ⚠️ **자동/사용자 모두 미수행**. PyMuPDF로 read-back만 함. evince/Adobe 등 외부 뷰어 호환성 별도 폴리싱 단계에서 확인 필요 |

### 4.2 자동화 불가 항목
- 외부 PDF 뷰어 호환성 (Acrobat, Foxit, evince, browser PDF.js 등)
- 회전된 페이지의 시각적 정확도 (텍스트 방향)
- Split/Extract/Merge 결과의 워드 wrap, 폰트 임베딩 보존
- 보호된/암호화된 PDF에 대한 mutation 시도

### 4.3 사용자 manual 검증 후속 필요 항목 (배치 모드 결정)
- Step 6-5 PDF 합치기 (다중 파일 선택, 출력 저장)
- Step 6-4 split 출력 디렉터리 자동 생성 fix 재현 검증
- Step 6-3 드래그 후 썸네일 유지 fix 재현 검증

### 4.4 ARCHITECTURE.md 명시 사항이지만 미구현
- Undo/Redo (`QUndoStack` 100-step depth) — Phase 3 후 일괄
- 비동기 썸네일 / 캐싱 — 폴리싱
- i18n — 폴리싱
- XDG 설정 영속화 — 폴리싱

### 4.5 누적 deferred 폴리싱 (10개)

1. XCB mouse grab 경고 (WSLg)
2. 도크 드래그 부드러움
3. HiDPI 스케일링
4. 윈도우 크기 영속화
5. 최근 파일 (MRU) 메뉴
6. 다크모드 영속화
7. UI/UX 일반 폴리싱
8. 타이틀바 더블클릭 최대화 + Aero Snap
9. 파일 다이얼로그 마우스 Back 버튼 뒤로가기
10. **썸네일 크기 조절** (Step 6-3 follow-up — 사용자 화면 대비 작음)

---

## 5. 결론 및 다음 단계

### 5.1 Phase 2 완료 선언 체크리스트
- [x] 모든 sub-step (6-1 ~ 6-5) 코드 구현
- [x] Build successful (`uv sync` OK)
- [x] 모든 코드 변경 사용자 또는 자체 검증 (Step 6-5는 자체 검증만)
- [x] 결과가 PROJECT_BRIEF.md Phase 2 spec과 일치
- [x] 모든 `[ASSUMPTION]` 보고
- [x] PROJECT_BRIEF.md Step 6-1 ~ 6-5 + 7 체크박스 완료
- [x] 본 SVR 작성

### 5.2 통계 (Phase 1 + 2 누적)

- **총 코드 라인**: 3,085 (src + tests)
- **테스트 케이스**: 108개, 100% 통과 (Phase 1 종료 시 58 → +50 신규)
- **Git 커밋**: 19개 (Phase 2 단독 9개: feat 5 + fix 3 + chore 1)
- **Phase 2 발견·수정 버그**: 3건 (모두 회귀 테스트 박음)

### 5.3 다음 단계

**Phase 3: 주석 (Step 8) 시작 권장**.

Phase 3 sub-step 잠정 계획 (사용자 확인 후 PROJECT_BRIEF.md 반영):
- 8-1: 텍스트 마크업 (하이라이트 / 밑줄 / 취소선)
- 8-2: 스티키 노트 (anchored comment)
- 8-3: 자유 그리기 (펜)
- 8-4: 도형 (사각형 / 원 / 화살표)
- 8-5: 텍스트 박스
- (각 mutation은 표준 PDF `/Annot` 사용 → 외부 뷰어 호환성 자연 확보)

배치 모드는 Phase 3에서도 동일 적용. 마지막에 통합 GUI 체크리스트 1회.
