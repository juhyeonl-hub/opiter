# Phase 4 Self-Verification Report

> CLAUDE_en.md "Mandatory Self-Verification Report" 규정 준수.
> Phase 4 (고급 PDF) 완료 선언. 다음 단계: Phase 5 (다중 포맷).

## 1. 테스트 방법

### 1.1 자동화 (pytest)
**총 180개 테스트, 100% 통과** (~37초).
Phase 4 단독: **19개** 신규 (`tests/test_phase4_core.py`).

### 1.2 End-to-End 통합 smoke
offscreen Qt에서 MainWindow 부팅 + 워터마크/메타데이터/TOC 일괄 적용 → save → reopen → 모든 변경 영속 확인.

```
INIT: pages=6, annots_p0=0
After watermark: annots_p0=1
Metadata: title='Test Doc', author='juhyeonl'
TOC: [('Ch 1', 1), ('Ch 2', 3)]
Bookmarks panel items: 2
Reopen annots_p0=1, title='Test Doc', toc=[('Ch 1', 1), ('Ch 2', 3)]
```

### 1.3 수동 GUI (배치)
Phase 4 종료 시 사용자 일괄 검증.

---

## 2. Sub-step별 결과

| Step | 구현 | 검증 |
|------|------|------|
| 9-1 | `export_pages_as_images(doc, indices, dir, name, fmt, dpi, jpg_quality)` — PNG/JPG, 150dpi 기본, 페이지 범위 지정 | ✅ 5 tests (PNG, JPG, 잘못된 포맷/디렉터리, 커스텀 subset) |
| 9-2 | `images_to_pdf(image_paths, output)` — 순서 보존, 각 이미지 크기대로 페이지 생성 | ✅ 3 tests |
| 9-3 | `compress_pdf(doc, out, quality)` — low/medium/high 프리셋. garbage + deflate + clean 조합 | ✅ 3 tests (writes, unknown preset, source 무손상) |
| 9-4 | `add_text_watermark(doc, text, pages?, fontsize, color, opacity, rotate)` — 대각선 45° default | ✅ 3 tests (모든 페이지, 특정 페이지만, 빈 텍스트 거부) |
| 9-5 | `Metadata` dataclass + `read_metadata` / `write_metadata` | ✅ 2 tests (round-trip, defaults) |
| 9-6 | `TocEntry` + `read_toc` / `write_toc` / `clear_toc` | ✅ 3 tests (write/read, clear, save persistence) |

### UI 신규 (전부 MainWindow에 와이어업)
| 메뉴 | 액션 | 구현 |
|------|------|------|
| File | Export Pages as Images… / Create PDF from Images… / Save Compressed Copy… / Document Properties… | QInputDialog + QFileDialog |
| Edit | Add Watermark… | `WatermarkDialog` (커스텀) |
| View | Show Bookmarks (F5) | `BookmarksPanel` (QTreeWidget) 도크, 우측 기본 |

- Watermark / Metadata / TOC 변경은 모두 **SnapshotCommand (Undo/Redo)**로 래핑
- BookmarksPanel → `toc_changed` 시그널 → MainWindow가 `_push_undo("Edit bookmarks", write_toc)`
- 북마크 더블클릭 → `page_jump_requested` → `viewer.goto_page`

---

## 3. 누적 통계

- **테스트**: 180 (Polish 종료 161 → +19 Phase 4)
- **코드**: ~6,000 lines (src + tests)
- **신규 모듈**: `core/image_export.py`, `core/image_to_pdf.py`, `core/compression.py`, `core/watermark.py`, `core/metadata.py`, `core/toc.py`, `ui/metadata_dialog.py`, `ui/watermark_dialog.py`, `ui/bookmarks_panel.py`
- **Git 커밋 (이번 단계)**: 1개 (big batch)

---

## 4. 검증된 입출력 (대표)

| 입력 | 출력 |
|------|------|
| `export_pages_as_images(5p doc, [0,1,2,3,4], dir, 'p', fmt='png')` | 5 PNG 파일, 각 > 100 bytes |
| `export_pages_as_images(..., fmt='bmp')` | ValueError |
| `images_to_pdf([png, png, png], out)` | 3p PDF, reopen 성공 |
| `images_to_pdf([], out)` | ValueError |
| `compress_pdf(doc, out, 'medium')` | 새 파일, source 무손상 |
| `compress_pdf(doc, out, 'ultra')` | ValueError |
| `add_text_watermark(3p doc, "DRAFT")` | 각 페이지 FreeText annot 1개 추가 |
| `add_text_watermark(doc, "X", pages=[0, 2])` | p0/p2만 annot 추가 |
| `write_metadata(doc, Metadata(title="X"))` → save → reopen | `read_metadata().title == "X"` |
| `write_toc(doc, [TocEntry(1, "Ch1", 1), ...])` → save → reopen | 동일 구조 반환 |

---

## 5. 미검증 / 불충분

- **이미지 워터마크** (`add_image_watermark`): 코어 함수는 구현했으나 UI (WatermarkDialog)에서는 text-only. 이미지 워터마크 파일 picker 추가 = 폴리싱 후속
- **PDF 압축 실제 크기 감소 비율**: 테스트 PDF가 이미 작아서 감소량 큰 차이 없음. 대용량 PDF 실측 필요
- **9-6 북마크 tree drag-reorder**: 현재 add/rename/remove만 지원. 드래그로 계층/순서 변경은 향후
- **이미지 파일 다양한 포맷 (tif, bmp 등)**: PyMuPDF가 지원하는 대부분 OK, 자동 테스트는 PNG/JPG만 커버

---

## 6. 결론

Phase 4 6개 sub-step 전부 구현 + 테스트 + UI 연동 완료. `PROJECT_BRIEF_PHASE4.md` Completion Criteria 모두 충족 (자동화 검증 기준). 사용자 manual GUI 검증만 남음.

**다음 단계**: Phase 5 (DOCX/HWP) → 통합 테스트 → 멀티 OS 패키징 → GitHub 공개.
