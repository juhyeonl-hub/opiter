# Project Brief — Phase 4 (Advanced PDF)

> Phase 1~3 MVP + Polish 완료 후 진행. Phase 5 (다중 포맷) → 통합 테스트 → 멀티 OS 패키징 → GitHub 공개 순.

## Project Name
Opiter — Phase 4: Advanced PDF Features

## Final Goal
MVP에서 제외됐던 **고급 PDF 편집/변환** 기능 구현:
이미지 ↔ PDF 변환, 압축, 워터마크, 메타데이터 편집, 북마크/TOC 편집.

## Tech Stack & Environment
Phase 1~3 + Polish 동일. 추가로 Pillow (이미지 I/O 보조, 이미 PyMuPDF 의존).

## Main Features (6 sub-steps)

- **9-1**: PDF → Image 내보내기 (PNG/JPG, 페이지 범위 지정)
- **9-2**: Image → PDF 생성 (여러 이미지 파일 → 한 PDF)
- **9-3**: PDF 압축 (품질 프리셋: Low/Medium/High)
- **9-4**: 워터마크 (텍스트 또는 이미지, 페이지 범위, 투명도)
- **9-5**: 메타데이터 편집 다이얼로그 (title/author/subject/keywords/creator)
- **9-6**: 북마크/TOC 편집 (트리 위젯 도크, add/rename/remove/reorder)

## Directory Structure
Phase 1~3/Polish 구조 유지. 신규:
```
src/opiter/
├── core/
│   ├── image_export.py   (9-1)
│   ├── image_to_pdf.py   (9-2)
│   ├── compression.py    (9-3)
│   ├── watermark.py      (9-4)
│   ├── metadata.py       (9-5)
│   └── toc.py            (9-6)
└── ui/
    ├── metadata_dialog.py
    ├── watermark_dialog.py
    └── bookmarks_panel.py (9-6, dock)
```

## Completion Criteria

- [ ] 9-1: 5페이지 PDF를 PNG 5개 + JPG 5개로 내보내기 성공, 각 이미지가 페이지와 시각적으로 일치
- [ ] 9-2: 3개 이미지 (다양한 크기)를 하나의 PDF로 합치기 → 페이지 3개, 각 페이지가 이미지 비율 유지
- [ ] 9-3: 10페이지 PDF를 Low 프리셋으로 압축 → 파일 크기 감소 확인
- [ ] 9-4: 텍스트 "CONFIDENTIAL" 워터마크를 모든 페이지에 추가 → 각 페이지에 표시 확인
- [ ] 9-5: Title/Author 등 편집 후 저장 → 재열기 시 유지
- [ ] 9-6: 새 북마크 추가, 기존 북마크 rename/delete → 저장 후 재열기 시 유지, 클릭 시 해당 페이지로 점프
- [ ] 모든 기능 pytest 커버 (신규 테스트 ≥ 20개)
- [ ] 기존 161 테스트 무회귀

## Notes
- **사용자 manual GUI**: 배치 모드 유지 — Phase 4 끝에 통합 체크리스트
- **UI 무거운 항목** (Watermark dialog, Bookmarks dock): custom dialog 불가피. 나머지는 QInputDialog 재활용
- **Undo/Redo 연동**: 문서 mutating ops (watermark, metadata, toc edit)는 기존 `SnapshotCommand` 경로로 래핑

## Task Progress
- [x] **9-1**: PDF → Image (PNG/JPG, page range, 150dpi default)
- [x] **9-2**: Image → PDF (multi-image picker, order preserved)
- [x] **9-3**: PDF compression (low/medium/high presets, source unchanged)
- [x] **9-4**: Watermark (text, 45° default, opacity + fontsize + rotation dialog)
- [x] **9-5**: Metadata editor (title/author/subject/keywords/creator dialog)
- [x] **9-6**: Bookmarks / TOC (right-docked tree, add/rename/remove, double-click to jump, F5 toggle)
- [x] **Phase 4 SVR** ([docs/phase4_self_verification.md](docs/phase4_self_verification.md))
