# Opiter

[English](./README.md) | **한국어**

> 무료·오픈소스 데스크톱 문서 워크벤치 — PDF 편집, DOCX·HWP 보기, 포맷 간 변환을 모두 로컬에서. 광고·구독·클라우드 업로드 없음.

**상태**: v0.1 — 첫 공개 릴리스. PDF 편집 완성, DOCX·HWP는 뷰어. Linux (WSL2 포함)에서 빌드·검증.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Built with PySide6](https://img.shields.io/badge/GUI-PySide6-41cd52.svg)](https://doc.qt.io/qtforpython-6/)

---

## 왜 Opiter?

상용 PDF 편집기는 비싸고 폐쇄적입니다. 무료 웹 기반 대안은 파일을 외부 서버에 업로드합니다. HWP 파일을 받는 한국 직장인에게는 무료 네이티브 뷰어가 사실상 없습니다. Opiter는 다른 전제 위에 있습니다:

- **100% 무료** — 광고도, 구독도, 프리미엄 등급도 없음
- **프라이버시 우선** — 모든 처리는 로컬에서. 파일은 절대 외부로 나가지 않음
- **세 포맷, 한 앱** — PDF (전체 편집), DOCX (뷰어), HWP (뷰어)
- **포맷 간 변환** — PDF → DOCX 원클릭, LibreOffice + h2orestart가 있으면 PDF → HWP 변환도 가능

## 기능

### PDF (전체 편집기)
- 열기, 페이지 이동, 줌, 너비 맞춤, 다크 모드
- 페이지 추가 / 삭제 / 순서 변경 / 회전
- 여러 PDF 병합, 분할 (범위·페이지별), 추출
- 주석: 하이라이트, 밑줄, 취소선, 스티키 노트, 자유 펜, 사각형, 타원, 화살표, 텍스트 박스
- 워터마크 (텍스트, 4방향 회전 지원)
- 압축 (3단계 품질 프리셋)
- 문서 속성 (제목·저자·키워드)
- 북마크 / 목차 편집
- 이미지 내보내기 (페이지별 PNG/JPG), 이미지 → PDF
- 회전된 페이지에서도 정확한 검색·하이라이트
- 멀티 PDF 탭 — 각 문서별 독립 undo 스택

### DOCX (뷰어)
- 읽기 전용 리치텍스트 렌더: 제목, 굵게/기울임/밑줄, 표, 목록
- CJK 폰트 자동 폴백 (Malgun Gothic / Noto CJK / NanumGothic) — 시스템에 한글 폰트가 없어도 정상 표시

### HWP (뷰어)
- pyhwp 기반 텍스트 추출
- 한글·한자 정상 렌더

### 포맷 간 변환
- **PDF → DOCX**: pdf2docx 기반, 텍스트·이미지·간단한 표 보존
- **PDF → HWP**: LibreOffice + h2orestart 확장 자동 감지 시 best-effort 변환

전체 기능 목록과 v0.1 이후 로드맵 (DOCX 편집, 배치 처리)은 [FEATURES.md](./FEATURES.md) 참고.

## 설치

### 빠른 설치 (릴리스 다운로드)

[최신 릴리스](https://github.com/juhyeonl-hub/opiter/releases/latest)에서 OS에 맞는 파일을 받으세요:

#### Windows
파일: `opiter-windows-x86_64.exe`. 더블클릭으로 실행.

> **첫 실행 시 보안 경고가 떠요.** "Windows에서 PC를 보호했습니다" 라는 파란 창이 뜨는데, 코드 서명 인증서를 아직 받지 못해서 그래요. 작은 글씨의 **"추가 정보"** 링크를 클릭한 뒤 **"실행"** 버튼을 누르면 정상 실행됩니다. ([SignPath Foundation](https://signpath.org/) 무료 OSS 서명을 신청 중이며, 통과되면 이 경고는 자동으로 사라집니다.)
>
> **창 자체가 안 뜨고 아무 일도 일어나지 않는 경우:** Smart App Control 기능이 켜져 있어서 무서명 앱을 조용히 차단한 거예요. 서명된 빌드가 나올 때까지 기다리거나, 아래 "소스에서 빌드" 방법으로 직접 빌드하면 됩니다.

#### macOS (Apple Silicon)
파일: `opiter-macos-arm64.dmg`. DMG를 열고 `Opiter.app`을 Applications 폴더로 드래그.

> **첫 실행 시 보안 경고.** 앱을 우클릭 → **"열기"** → 다이얼로그에서 다시 **"열기"** 클릭. 한 번 통과시키면 그 다음부터는 일반 더블클릭으로 열립니다. (아직 Apple notarization을 받지 않아 첫 실행에만 필요한 단계입니다.)

#### Linux (Debian / Ubuntu)
파일: `opiter-linux-amd64.deb`.

```bash
sudo apt install ./opiter-linux-amd64.deb
```

설치 후 애플리케이션 메뉴에서 실행하거나 터미널에서 `opiter` 입력.

### 소스에서 빌드

세 OS 모두에서 동작 — 미리 빌드된 바이너리가 막혀 있거나 코드를 직접 수정하려면 이 방법을 쓰세요.

**필수 환경**:
- **Python 3.11** 이상 (uv가 자동 설치)
- [**uv**](https://github.com/astral-sh/uv) 패키지 매니저:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Qt6 디스플레이 환경 (Linux X11/Wayland, WSL2 + WSLg, macOS, Windows 데스크톱)
- 선택 사항: PDF → HWP 변환을 쓰려면 `libreoffice` + [`h2orestart`](https://github.com/ebandal/H2Orestart) 확장

**빌드 & 실행**:
```bash
git clone https://github.com/juhyeonl-hub/opiter
cd opiter
uv sync
uv run opiter
```

## 개발

```bash
# 런타임 + 개발 의존성 모두 설치
uv sync --all-groups

# 소스에서 실행
uv run python -m opiter

# 테스트 (186개)
uv run pytest
```

[CONTRIBUTING.md](./CONTRIBUTING.md)에 기여 가이드, [ARCHITECTURE.md](./ARCHITECTURE.md)에 코드 구조 설명이 있습니다.

## 문서

| 파일 | 내용 |
|------|------|
| [PROJECT.md](./PROJECT.md) | 프로젝트 비전·철학·범위 |
| [FEATURES.md](./FEATURES.md) | 전체 기능 로드맵 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 모듈 구조, 데이터 흐름, 설계 결정 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 기여 방법 |

## 라이선스

[GNU Affero General Public License v3.0 (AGPL-3.0)](./LICENSE) © 2026 juhyeonl

Opiter는 AGPL 라이선스 라이브러리(PyMuPDF, pyhwp)에 의존하기 때문에 프로젝트 전체가 AGPL-3.0으로 배포됩니다. 즉, 자유롭게 사용·수정·재배포할 수 있지만 **파생 저작물(네트워크 서비스 포함)은 동일 라이선스로 전체 소스를 공개해야** 합니다.

## 고마운 프로젝트들

Opiter는 다음 오픈소스 프로젝트들 위에서 만들어졌습니다:

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) (fitz) — PDF 렌더링·주석·편집 코어 (AGPL-3.0)
- [pdf2docx](https://github.com/dothinking/pdf2docx) — PDF → DOCX 변환 (MIT)
- [python-docx](https://github.com/python-openxml/python-docx) — DOCX 읽기/쓰기 (MIT)
- [pyhwp](https://github.com/mete0r/pyhwp) — HWP 텍스트 추출 (AGPL-3.0)
- [pypdf](https://github.com/py-pdf/pypdf) — PDF 페이지 단위 조작 (BSD)
- [pdfplumber](https://github.com/jsvine/pdfplumber) — 텍스트·표 추출 (MIT)
- [PySide6](https://doc.qt.io/qtforpython-6/) — 크로스플랫폼 GUI 툴킷 (LGPL-3.0)
- [uv](https://github.com/astral-sh/uv) — Python 패키징

PDF → HWP 변환 시 [LibreOffice](https://www.libreoffice.org/)와 [h2orestart](https://github.com/ebandal/H2Orestart) 확장을 사용합니다.

## 코드 서명

Windows 바이너리는 [SignPath Foundation](https://signpath.org/)이 오픈소스 프로젝트에 무료로 제공하는 인증서 프로그램으로 서명됩니다. macOS `.app` 번들과 Linux `.deb`는 현재 무서명으로 배포됩니다.
