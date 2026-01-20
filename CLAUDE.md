# GitLab to GitHub Migration Tool - Claude 개발 가이드

## 프로젝트 개요

GitLab 저장소를 GitHub로 일괄 이관하는 Python 도구입니다.
**Python 표준 라이브러리만 사용**하여 외부 의존성 없이 동작하는 것이 핵심 특징입니다.

## 핵심 제약사항 ⚠️

### 1. **절대적 규칙: 표준 라이브러리만 사용**

다음 라이브러리는 **사용 금지**입니다:
- ❌ `requests`
- ❌ `python-gitlab`
- ❌ `PyGithub`
- ❌ `GitPython`
- ❌ `aiohttp`
- ❌ 기타 모든 외부 패키지

다음 표준 라이브러리만 **사용 가능**합니다:
- ✅ `urllib.request` (HTTP 요청)
- ✅ `urllib.parse` (URL 인코딩)
- ✅ `urllib.error` (에러 처리)
- ✅ `subprocess` (Git 명령 실행)
- ✅ `json` (JSON 파싱)
- ✅ `os`, `sys`, `shutil`, `tempfile` (파일/시스템)
- ✅ `time` (딜레이)
- ✅ `typing` (타입 힌트)

### 2. HTTP 요청 처리

GitLab/GitHub API 호출 시:
```python
# ✅ 올바른 방법
import urllib.request
import urllib.parse
import json

url = "https://api.github.com/user"
headers = {'Authorization': f'token {token}'}
request = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(request) as response:
    data = json.loads(response.read().decode('utf-8'))

# ❌ 잘못된 방법
import requests  # 외부 라이브러리!
response = requests.get(url, headers=headers)
```

### 3. Git 명령 실행

Git 작업 시:
```python
# ✅ 올바른 방법
import subprocess

subprocess.run(['git', 'clone', '--mirror', url, path], check=True)

# ❌ 잘못된 방법
from git import Repo  # GitPython 외부 라이브러리!
Repo.clone_from(url, path)
```

## 프로젝트 구조

```
github_mig/
├── migrate.py           # 메인 마이그레이션 스크립트
├── test_connection.py   # 연결 테스트 전용 스크립트
├── config.json          # 사용자 설정 (gitignore)
├── config.example.json  # 설정 템플릿
├── requirements.txt     # 비어있음 (표준 라이브러리만 사용)
├── README.md           # 사용 설명서
├── CLAUDE.md           # 이 파일
└── .gitignore          # config.json 제외
```

## 주요 컴포넌트

### 1. `migrate.py`
- `GitLabAPI`: GitLab API 클라이언트 (urllib 사용)
- `GitHubAPI`: GitHub API 클라이언트 (urllib 사용)
- `GitLabToGitHubMigrator`: 메인 마이그레이션 로직
- `MigrationLogger`: 색상 로그 출력

### 2. `test_connection.py`
- `GitLabTester`: GitLab 연결 및 그룹 스캔 테스트
- `GitHubTester`: GitHub 연결 테스트
- 실제 마이그레이션 없이 연결성만 확인

## 개발 시 주의사항

### API 페이지네이션
GitLab/GitHub API는 페이지네이션을 사용합니다:
```python
def _make_request_list(self, endpoint: str, params: Dict = None) -> List[Dict]:
    all_results = []
    page = 1
    per_page = 100

    while True:
        query_params = params.copy() if params else {}
        query_params['page'] = page
        query_params['per_page'] = per_page

        # ... API 요청 ...

        if len(results) < per_page:
            break
        page += 1

    return all_results
```

### 에러 처리
```python
try:
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    error_body = e.read().decode('utf-8')
    raise Exception(f"API 오류 ({e.code}): {error_body}")
except urllib.error.URLError as e:
    raise Exception(f"연결 실패: {e.reason}")
```

### Git 명령어 실행
```python
def _run_git_command(self, command: List[str], cwd: str = None):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        # 에러 처리
        raise
```

## 기능 요구사항

### 필수 기능
- [x] GitLab 그룹 자동 스캔 (서브그룹 포함)
- [x] 여러 저장소 일괄 이관
- [x] 모든 브랜치/태그 보존
- [x] GitHub Organization 지원
- [x] Dry run 모드
- [x] 연결 테스트 도구

### 네이밍 규칙
- `project_name`: 프로젝트 이름만 (예: `my-project`)
- `path_with_namespace`: 전체 경로 (예: `icis-rater-my-project`)

## 설정 파일 구조

```json
{
  "gitlab": {
    "url": "https://gitlab.com",
    "token": "TOKEN"
  },
  "github": {
    "token": "TOKEN",
    "organization": "ORG_NAME"
  },
  "scan_groups": [
    {
      "group_path": "icis/rater",
      "include_subgroups": true,
      "naming_rule": "project_name",
      "default_private": true
    }
  ],
  "repositories": [],
  "options": {
    "clone_method": "https",
    "preserve_branches": true,
    "preserve_tags": true,
    "dry_run": true
  }
}
```

## 코드 수정 시 체크리스트

새로운 기능을 추가하거나 코드를 수정할 때:

- [ ] **표준 라이브러리만 사용했는가?**
- [ ] `import` 문에 외부 패키지가 없는가?
- [ ] `requirements.txt`에 새 패키지를 추가하지 않았는가?
- [ ] API 요청에 `urllib`을 사용했는가?
- [ ] Git 작업에 `subprocess`를 사용했는가?
- [ ] 에러 처리가 적절한가?
- [ ] 페이지네이션을 고려했는가? (목록 조회 시)
- [ ] 색상 코드를 ANSI 이스케이프 시퀀스로 직접 작성했는가?

## 색상 출력

외부 라이브러리(`colorama`) 대신 ANSI 코드 직접 사용:
```python
class MigrationLogger:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

    @staticmethod
    def success(message: str):
        print(f"{MigrationLogger.GREEN}✓ {message}{MigrationLogger.RESET}")
```

## 테스트 워크플로우

사용자가 따라야 할 순서:
1. `config.json` 작성 (토큰 입력)
2. `python test_connection.py` - 연결 테스트
3. `python migrate.py` (dry_run: true) - 시뮬레이션
4. `python migrate.py` (dry_run: false) - 실제 이관

## 보안 고려사항

- `config.json`은 `.gitignore`에 포함
- 토큰은 환경변수가 아닌 설정 파일에서 관리
- HTTPS URL에 토큰 포함 시: `https://TOKEN@github.com/...`

## 향후 확장 가능성

표준 라이브러리 제약 내에서 가능한 확장:
- [ ] 프로젝트별 필터링 (정규표현식)
- [ ] 이관 결과 로그 파일 저장
- [ ] 병렬 처리 (`concurrent.futures`)
- [ ] 재시도 로직 추가

표준 라이브러리 제약으로 **불가능한** 것:
- ❌ Issues/MR 이관 (복잡한 API 작업, 외부 라이브러리 필요)
- ❌ Wiki 이관
- ❌ CI/CD 설정 변환
- ❌ 비동기 처리 (`asyncio`는 표준이지만 복잡도 증가)

## 문제 해결

### ImportError 발생 시
```bash
# 잘못된 import가 있는지 확인
grep -r "^import\|^from" *.py | grep -v "urllib\|subprocess\|json\|os\|sys\|shutil\|tempfile\|time\|typing"
```

### 표준 라이브러리 확인
Python 3.7+ 표준 라이브러리 목록: https://docs.python.org/3/library/

## 마지막 당부

**이 프로젝트의 가장 중요한 특징은 "외부 의존성 없음"입니다.**

코드를 수정할 때는 항상 다음을 확인하세요:
```bash
# requirements.txt가 비어있는지 확인
cat requirements.txt

# 실제로 외부 패키지 없이 실행되는지 확인
python -c "import sys; import migrate; import test_connection"
```

모든 기능은 Python 표준 라이브러리만으로 구현되어야 합니다! 🚫📦
