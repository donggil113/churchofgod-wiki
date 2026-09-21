# 하나님의 교회 지식사전 정적 사이트

허가받은 원본 위키의 공개 문서를 GitHub Pages용 정적 사이트로 옮긴 프로젝트입니다. 기존 광명교회 사이트와 별도 저장소로 운영합니다.

## 문서 수정

1. [문서 편집 화면](https://app.pagescms.org/donggil113/churchofgod-wiki/main)에 GitHub 계정으로 로그인합니다. 이 저장소에만 Pages CMS 앱이 연결되어 있습니다.
2. **문서**에서 기존 문서 목록을 열거나 **새 문서**를 선택해 제목, 요약, 분류, 본문을 편집하고 저장합니다. 기존 문서는 편집 화면의 처리 속도를 위해 12개 목록으로 나뉘어 있습니다.
3. GitHub 저장소의 `main` 브랜치에 변경이 저장되면 게시 작업이 자동 실행됩니다.

GitHub 웹 화면에서 `content/pages/`의 문서 파일을 직접 수정할 수도 있습니다. 대문 역시 이 폴더의 문서 중 하나입니다. 사진을 새로 올릴 때는 `media/` 폴더를 사용하세요. 첫 화면의 사진은 이 저장소에 보관했습니다. 다른 문서의 사진은 대부분 원본 서버 주소를 사용하므로, 독립 보관이 필요하면 별도 자산 이전 작업이 필요합니다.

## 로컬 확인

```sh
python -m pip install -r requirements.txt
python scripts/build.py
python -m http.server 4173 --directory dist
```

`http://localhost:4173/`에서 확인할 수 있습니다.

## GitHub Pages 게시

새 GitHub 저장소에 올린 뒤 **Settings → Pages → Build and deployment → Source**에서 **GitHub Actions**를 선택합니다. `main`에 올리면 `.github/workflows/pages.yml`이 사이트를 만듭니다. 도메인 구매 후 같은 Pages 설정의 **Custom domain**에 도메인을 등록하고 DNS를 연결합니다. 사이트는 서버 프로그램 없이 동작하므로 방문자 계정, 실시간 위키 편집, MediaWiki 개정 이력은 제공하지 않습니다. 편집자는 GitHub/Pages CMS를 사용합니다.

## 원본 업데이트

`python scripts/import_wiki.py`는 원본에서 새 문서를 가져오되 기존 JSON을 덮어쓰지 않습니다. `--overwrite`는 현지 수정 내용을 덮어쓰므로 신중하게 사용하세요.
