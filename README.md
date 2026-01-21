# GitLab to GitHub Migration Tool

GitLab 저장소를 GitHub로 일괄 이관하는 Python 도구입니다. **표준 라이브러리만 사용**하여 외부 의존성이 없습니다.

## 특징

- ✅ **외부 의존성 없음**: Python 표준 라이브러리만 사용
- 🔄 **일괄 이관**: 여러 저장소를 한 번에 이관
- 📁 **그룹 자동 스캔**: GitLab 그룹을 스캔하여 모든 프로젝트 자동 검색
- 📋 **프로젝트 목록 조회**: 그룹 내 모든 프로젝트 정보를 터미널과 로그로 출력
- 🌿 **완전한 히스토리 보존**: 모든 커밋, 브랜치, 태그 유지
- 🏷️ **GitLab namespace 추적**: GitLab subgroup/namespace ID를 GitHub topic으로 자동 등록
- 🔒 **안전한 인증**: 설정 파일로 토큰 관리
- 🎯 **Organization 지원**: 개인/조직 계정 모두 지원
- 👥 **권한 자동 부여**: Collaborators와 Teams에게 자동으로 저장소 권한 부여
- 🧪 **Dry Run 모드**: 실제 이관 전 시뮬레이션
- 🔍 **동기화 상태 확인**: GitLab vs GitHub 브랜치/태그/커밋 비교
- ⚡ **Rate Limit 자동 관리**: API 호출 제한 실시간 모니터링 및 적응형 딜레이

## 제공 도구

이 프로젝트는 7개의 독립 실행 도구를 제공합니다:

1. **list_projects.py** - GitLab 그룹 프로젝트 목록 조회
   - 그룹 하위의 모든 프로젝트 정보를 터미널에 출력
   - 로그 파일로 저장 (타임스탬프 포함)
   - 프로젝트 상세 정보 표시 (경로, URL, 가시성, 통계 등)

2. **test_connection.py** - 연결 테스트
   - GitLab/GitHub 연결 확인
   - 이관 대상 프로젝트 미리보기
   - 실제 마이그레이션 없음

3. **migrate.py** - 실제 마이그레이션
   - GitLab → GitHub 저장소 이관
   - Dry run 모드 지원
   - 성능 최적화 (저장소 간 대기 시간 단축)

4. **check_sync.py** - 동기화 상태 확인
   - GitLab vs GitHub 브랜치/태그 개수 비교
   - 각 브랜치별 커밋 상태 확인
   - Behind 상세정보 (커밋 차이, 커밋 목록)

5. **dashboard.py** - 이관 대시보드
   - 이관 상태를 HTML 대시보드로 시각화
   - 브랜치별 상태 확인 (completed, not created, sync needed)
   - 통계 요약 및 필터링 기능
   - GitLab 그룹 정보 표시

6. **dashboard_server.py** - 대시보드 웹 서버 ✨ NEW
   - 웹에서 refresh/migrate 버튼으로 실행 가능
   - 백그라운드 마이그레이션 지원
   - 자동 상태 확인 및 업데이트
   - 표준 라이브러리만 사용 (http.server)

7. **cleanup_github.py** - GitHub 저장소 일괄 삭제 ⚠️
   - 기존 GitHub 저장소들을 일괄 삭제
   - 재이관 전 정리 작업
   - 안전 확인 절차 포함

## 요구사항

- Python 3.7 이상
- Git 명령어 (시스템에 설치되어 있어야 함)
- GitLab Personal Access Token
- GitHub Personal Access Token

## 설치

저장소를 클론하거나 파일을 다운로드합니다:

```bash
git clone <repository-url>
cd github_mig
```

외부 패키지 설치가 필요 없습니다!

## 설정

### 1. 설정 파일 생성

`config.example.json`을 복사하여 `config.json`을 생성합니다:

```bash
cp config.example.json config.json
```

### 2. GitLab Personal Access Token 생성

1. GitLab에 로그인
2. Settings → Access Tokens
3. 다음 권한 선택:
   - `read_api`
   - `read_repository`
4. 토큰 생성 후 복사

### 3. GitHub Personal Access Token 생성

1. GitHub에 로그인
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. **필요한 권한(Scopes) 선택:**

#### 필수 권한

**기본 마이그레이션용:**
- ✅ `repo` (전체 저장소 접근)
  - `repo:status` - 저장소 상태 확인
  - `repo_deployment` - 배포 상태 접근
  - `public_repo` - 공개 저장소 접근
  - `repo:invite` - 저장소 초대
  - `security_events` - 보안 이벤트 읽기

**GitLab namespace를 GitHub topic으로 추가하려면:**
- ✅ `repo` scope 필요 (위 권한에 포함됨)
  - Topics API는 `repo` scope가 있어야 사용 가능
  - **주의**: `public_repo`만으로는 부족하며 전체 `repo` scope 필요

#### 선택적 권한

**저장소 삭제 기능 사용 시 (cleanup_github.py):**
- ☑️ `delete_repo` - 저장소 삭제 권한
  - 이 권한이 없으면 cleanup_github.py 실행 불가
  - 재이관이 필요한 경우에만 활성화 권장

**Organization 저장소 이관 시:**
- ☑️ `read:org` - Organization 정보 읽기
  - Organization 저장소 생성 시 필요
  - Teams에 권한 부여 시 필요

#### 권한 부족 시 발생하는 오류

- **"OAuth token does not meet scope requirement"**
  - Topics API 호출 시: `repo` scope 필요
  - 해결: 전체 `repo` scope로 새 토큰 생성

- **"Not Found" or "403 Forbidden"**
  - Organization 접근 시: `read:org` scope 필요
  - 저장소 삭제 시: `delete_repo` scope 필요

4. 토큰 생성 후 복사 및 안전하게 보관

### 4. config.json 편집

#### 방법 1: 그룹 자동 스캔 (권장)

GitLab 그룹 전체를 자동으로 스캔하여 이관:

```json
{
  "gitlab": {
    "url": "https://gitlab.com",
    "token": "YOUR_GITLAB_TOKEN"
  },
  "github": {
    "token": "YOUR_GITHUB_TOKEN",
    "organization": "YOUR_GITHUB_ORG"
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

#### 방법 2: 수동으로 저장소 지정

각 저장소를 개별적으로 지정:

```json
{
  "gitlab": {
    "url": "https://gitlab.com",
    "token": "YOUR_GITLAB_TOKEN"
  },
  "github": {
    "token": "YOUR_GITHUB_TOKEN",
    "organization": ""
  },
  "scan_groups": [],
  "repositories": [
    {
      "gitlab_project_id": "12345678",
      "gitlab_project_path": "group/project-name",
      "github_repo_name": "new-repo-name",
      "description": "Repository description",
      "private": true
    }
  ],
  "options": {
    "clone_method": "https",
    "preserve_branches": true,
    "preserve_tags": true,
    "dry_run": false
  }
}
```

#### 설정 항목 설명

**gitlab**
- `url`: GitLab 인스턴스 URL (기본: https://gitlab.com)
- `token`: GitLab Personal Access Token

**github**
- `token`: GitHub Personal Access Token
- `organization`: GitHub Organization 이름 (개인 계정은 빈 문자열)

**scan_groups** (배열) - 자동 스캔할 GitLab 그룹 목록
- `group_id`: GitLab 그룹 ID (숫자, 선택사항)
- `group_path`: GitLab 그룹 경로 (예: `icis/rater`, group_id 대신 사용 가능)
- `include_subgroups`: 서브그룹 포함 여부 (true/false)
- `naming_rule`: GitHub 저장소 이름 규칙
  - `project_name`: 프로젝트 이름만 사용 (예: `my-project`)
  - `path_with_namespace`: 전체 경로 사용 (예: `icis-rater-my-project`)
- `default_private`: 생성할 저장소의 기본 공개 여부 (true/false)
- `default_collaborators`: 모든 저장소에 기본으로 추가할 collaborators (선택사항)
  - `username`: GitHub 사용자 이름
  - `permission`: 권한 (`pull`, `push`, `admin`, `maintain`, `triage`)
- `default_teams`: 모든 저장소에 기본으로 추가할 teams (Organization 전용, 선택사항)
  - `team_slug`: GitHub 팀 슬러그 (팀 이름)
  - `permission`: 권한 (`pull`, `push`, `admin`, `maintain`, `triage`)

**repositories** (배열)
- `gitlab_project_id`: GitLab 프로젝트 ID (숫자)
- `gitlab_project_path`: GitLab 프로젝트 경로 (예: `group/project`)
  - `gitlab_project_id` 또는 `gitlab_project_path` 중 하나 필수
- `github_repo_name`: 생성할 GitHub 저장소 이름
- `description`: 저장소 설명 (선택사항, 비우면 GitLab 설명 사용)
- `private`: 비공개 저장소 여부 (true/false)
- `collaborators`: 이 저장소에 추가할 collaborators (선택사항)
  - `username`: GitHub 사용자 이름
  - `permission`: 권한 (`pull`, `push`, `admin`, `maintain`, `triage`)
- `teams`: 이 저장소에 추가할 teams (Organization 전용, 선택사항)
  - `team_slug`: GitHub 팀 슬러그
  - `permission`: 권한 (`pull`, `push`, `admin`, `maintain`, `triage`)

**options**
- `clone_method`: 클론 방식 (`https` 또는 `ssh`)
- `preserve_branches`: 모든 브랜치 보존 여부
- `preserve_tags`: 모든 태그 보존 여부
- `dry_run`: 시뮬레이션 모드 (실제 이관 안 함)
- `verify_ssl`: SSL 인증서 검증 여부 (true/false)
  - `true` (기본값): SSL 인증서를 검증 (권장)
  - `false`: SSL 검증 비활성화 (회사 방화벽/프록시 환경에서 필요)

## 사용법

### 1단계: 연결 테스트 (권장)

실제 마이그레이션 전에 연결성과 프로젝트 목록을 확인합니다:

```bash
python test_connection.py
```

이 명령은:
- ✓ GitLab 연결 및 인증 확인
- ✓ GitLab 그룹 스캔 및 프로젝트 목록 조회
- ✓ GitHub 연결 및 Organization 접근 확인
- ✓ 이관 대상 프로젝트를 표 형식으로 출력
- ✗ **실제 저장소 생성이나 푸시는 하지 않음**

출력 예시:
```
╔══════════════════════════════════════════════════════════╗
║     GitLab/GitHub 연결 테스트 도구                      ║
╚══════════════════════════════════════════════════════════╝

1. GitLab 연결 테스트
✓ GitLab 연결 성공!
  - 사용자: myuser (My Name)

2. GitLab 그룹 스캔
✓ 총 15개의 프로젝트 발견

발견된 프로젝트 목록
No.   GitLab 프로젝트                    →   GitHub 저장소 이름
--------------------------------------------------------------------
1     icis/rater/airflow/dag-manager     →   dag-manager
2     icis/rater/batch/data-processor    →   data-processor
...

3. GitHub 연결 테스트
✓ GitHub 연결 성공!
✓ Organization 접근 가능!
```

### 2단계: Dry Run (시뮬레이션)

연결 테스트 후, dry run으로 실제 마이그레이션 과정을 시뮬레이션합니다:

```json
{
  "options": {
    "dry_run": true
  }
}
```

```bash
python migrate.py
```

### 3단계: 실제 이관

테스트와 dry run으로 확인 후 `dry_run`을 `false`로 변경:

```json
{
  "options": {
    "dry_run": false
  }
}
```

```bash
python migrate.py
```

마이그레이션이 완료되면:
- `migration_results.json` - 이관 결과가 자동 저장됨
- `dashboard.html` - 대시보드가 자동 생성됨 (dry_run이 아닌 경우)

### 마이그레이션 시 자동 수행 작업

마이그레이션 도구는 각 저장소를 이관할 때 다음 작업을 자동으로 수행합니다:

1. **GitLab 저장소 클론** - 모든 브랜치와 태그 포함
2. **GitHub 저장소 생성** - 지정된 이름과 설정으로 생성
3. **권한 부여** - Collaborators 및 Teams 권한 자동 설정
4. **GitLab 서브그룹 topic 추가** - GitLab 서브그룹 경로를 GitHub topic으로 등록
   - 형식: `gitlab-{namespace_path}` (예: `gitlab-icis-rater`)
   - 목적: GitLab 원본 그룹별로 저장소 그룹화 및 추적
   - **필수 권한**: GitHub 토큰에 `repo` scope 필요
   - 권한 부족 시: topic 추가는 실패하지만 마이그레이션은 계속 진행
   - 50자 제한 초과 시 자동 트리밍
5. **Git 히스토리 푸시** - 모든 커밋, 브랜치, 태그 푸시
6. **결과 저장** - `migration_results.json`에 이관 결과 저장
7. **대시보드 자동 생성** - 이관 완료 후 `dashboard.html` 자동 생성 (dry_run 제외)

#### GitLab 서브그룹 topic 활용 예시

- **원본 그룹별 필터링**: GitHub에서 `gitlab-icis-rater`로 검색하여 동일 GitLab 그룹에서 온 저장소 찾기
- **자동화 스크립트**: topic을 기반으로 특정 GitLab 그룹 출신 저장소에 일괄 작업 수행
- **문서화**: 각 저장소의 GitLab 원본 그룹 위치를 명확하게 기록
- **팀별 관리**: 서브그룹 경로로 팀별 저장소를 쉽게 식별하고 관리

## 프로젝트 목록 조회 (list_projects.py)

마이그레이션 전에 그룹 내 모든 프로젝트 정보를 확인하고 싶다면 `list_projects.py`를 사용하세요.

### 기본 사용법

```bash
# config.json의 scan_groups 사용
python list_projects.py

# 특정 그룹 지정
python list_projects.py -g icis/rater

# 간단한 목록만 보기
python list_projects.py -g icis/rater -s

# 로그 파일 이름 지정
python list_projects.py -g icis/rater -o my_projects.log

# 서브그룹 제외
python list_projects.py -g icis/rater -n
```

### 옵션

- `-c, --config FILE` : 설정 파일 경로 (기본: config.json)
- `-g, --group GROUP` : 그룹 ID 또는 경로
- `-s, --simple` : 간단한 목록만 표시
- `-n, --no-subgroups` : 서브그룹 제외
- `-o, --output FILE` : 로그 파일 이름 지정
- `-h, --help` : 도움말 표시

### 출력 내용

**상세 보기 (기본):**
```
━━━ [1/15] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
프로젝트: my-project
경로: icis/rater/airflow/my-project
ID: 12345
설명: Project description here
웹 URL: https://gitlab.com/icis/rater/airflow/my-project
HTTP URL: https://gitlab.com/icis/rater/airflow/my-project.git
SSH URL: git@gitlab.com:icis/rater/airflow/my-project.git
가시성: 🔒 private (비공개)
아카이브: 아니오
Star: ⭐ 5 | Fork: 🍴 2
생성일: 2023-01-15 10:30:00
최종 활동: 2024-01-07 15:45:30
기본 브랜치: main
```

**간단 보기 (-s 옵션):**
```
No.   프로젝트 경로                               가시성
----------------------------------------------------------------
1     icis/rater/airflow/dag-manager            private
2     icis/rater/batch/data-processor           private
3     icis/rater/engine/rule-engine             internal
```

### 로그 파일

자동으로 타임스탬프가 포함된 로그 파일이 생성됩니다:
```
gitlab_projects_20240107_153045.log
```

로그 파일에는 색상 코드 없이 순수 텍스트만 저장되어 나중에 검색하거나 분석하기 좋습니다.

## GitHub 저장소 일괄 삭제 (cleanup_github.py)

마이그레이션 후 문제가 발생했거나 다시 이관하고 싶을 때, 기존 GitHub 저장소들을 일괄 삭제할 수 있습니다.

⚠️ **경고: 이 작업은 되돌릴 수 없습니다! 신중하게 사용하세요.**

### 기본 사용법

```bash
# 1단계: Dry run으로 삭제 대상 확인 (권장)
python cleanup_github.py -d

# 2단계: 특정 저장소만 삭제
python cleanup_github.py -r "project1,project2,project3"

# 3단계: config.json의 모든 저장소 삭제
python cleanup_github.py
```

### 옵션

- `-c, --config FILE` : 설정 파일 경로 (기본: config.json)
- `-d, --dry-run` : 시뮬레이션 (실제 삭제 안 함)
- `-r, --repos NAMES` : 삭제할 저장소 이름 (쉼표로 구분)
- `-h, --help` : 도움말 표시

### 사용 시나리오

#### 시나리오 1: 전체 재이관

```bash
# 1. 기존 저장소 확인 (dry run)
python cleanup_github.py -d

# 2. 저장소 삭제
python cleanup_github.py
# "DELETE" 입력하여 확인

# 3. 다시 마이그레이션
python migrate.py
```

#### 시나리오 2: 특정 프로젝트만 재이관

```bash
# 1. 문제가 있는 저장소만 삭제
python cleanup_github.py -r "problematic-repo1,problematic-repo2"

# 2. 해당 저장소만 다시 마이그레이션
# (config.json에서 해당 저장소만 설정 후)
python migrate.py
```

### 실행 예시

```
╔══════════════════════════════════════════════════════════╗
║     GitHub 저장소 일괄 삭제 도구                         ║
║     ⚠ 경고: 이 작업은 되돌릴 수 없습니다!                ║
╚══════════════════════════════════════════════════════════╝

GitHub 계정: myusername
Organization: my-company

GitHub 저장소 확인 중...
발견된 저장소: 5개

======================================================================
경고: 다음 저장소들이 영구적으로 삭제됩니다!
======================================================================

1. my-company/project1 (🔒 비공개)
   URL: https://github.com/my-company/project1
2. my-company/project2 (🔒 비공개)
   URL: https://github.com/my-company/project2
...

총 5개의 저장소가 삭제됩니다.
이 작업은 되돌릴 수 없습니다!

계속하려면 'DELETE'를 정확히 입력하세요: DELETE

삭제를 시작합니다...

[1/5] project1 삭제 중... ✓ project1 삭제 완료
[2/5] project2 삭제 중... ✓ project2 삭제 완료
...

======================================================================
삭제 완료
======================================================================
성공: 5개

이제 마이그레이션을 실행할 수 있습니다:
  python migrate.py
```

### 안전 기능

1. **Dry Run 모드** - 실제 삭제 없이 시뮬레이션
2. **삭제 확인** - "DELETE" 정확히 입력해야 실행
3. **개별 진행 표시** - 각 저장소 삭제 상태 표시
4. **자동 존재 확인** - 이미 없는 저장소는 건너뜀

### 주의사항

- ⚠️ **Organization 저장소 삭제는 admin 권한 필요**
- ⚠️ **삭제된 저장소는 복구 불가**
- ⚠️ **먼저 dry run으로 확인 필수**
- ⚠️ **중요 저장소는 백업 후 삭제**

## 동기화 상태 확인 (check_sync.py)

마이그레이션 후 GitLab과 GitHub 저장소가 제대로 동기화되었는지 확인합니다.

### 기능

- ✅ **브랜치/태그 개수 비교** - GitLab vs GitHub 개수 차이 확인
- ✅ **브랜치별 커밋 비교** - 각 브랜치의 최신 커밋 SHA 비교
- ✅ **Behind 상세정보** - GitHub가 뒤처진 경우 커밋 차이와 목록 표시
- ✅ **동기화 요약** - 전체 저장소의 동기화 상태 한눈에 확인

### 기본 사용법

```bash
# config.json의 모든 저장소 동기화 상태 확인
python check_sync.py

# 특정 설정 파일 사용
python check_sync.py my_config.json
```

### 출력 예시

```
╔══════════════════════════════════════════════════════════╗
║     GitLab ↔ GitHub Sync Status Checker                 ║
║     저장소 동기화 상태 확인 도구                         ║
╚══════════════════════════════════════════════════════════╝

======================================================================
동기화 상태 확인
GitLab: mygroup/my-project
GitHub: my-org/my-project
======================================================================

📊 브랜치 비교 중...

======================================================================
📊 브랜치 비교 결과
======================================================================
GitLab: 5개 | GitHub: 5개
----------------------------------------------------------------------
브랜치명                          상태                 GitLab       GitHub
----------------------------------------------------------------------
main                             ✓ Synced             a1b2c3d4     a1b2c3d4
develop                          ✓ Synced             e5f6g7h8     e5f6g7h8
feature/new-api                  ⚠ Different          i9j0k1l2     m3n4o5p6
  └─ GitHub가 3개 커밋 뒤처짐 (GitLab이 3개 앞섬)
     • i9j0k1l2 - Add new API endpoint for user management
       John Doe (2024-01-10T10:30:00Z)
     • a1b2c3d4 - Update API documentation
       Jane Smith (2024-01-10T09:15:00Z)
     • e5f6g7h8 - Fix API validation bug
       Bob Johnson (2024-01-09T16:45:00Z)
hotfix/security                  ✗ Missing in GitHub  q7r8s9t0     -
release/v2.0                     ✓ Synced             u1v2w3x4     u1v2w3x4

🏷️  태그 비교 중...

======================================================================
🏷️  태그 비교 결과
======================================================================
GitLab: 3개 | GitHub: 3개
----------------------------------------------------------------------
태그명                            상태                 GitLab       GitHub
----------------------------------------------------------------------
v1.0.0                           ✓ Synced             y5z6a7b8     y5z6a7b8
v1.1.0                           ✓ Synced             c9d0e1f2     c9d0e1f2
v2.0.0-beta                      ✗ Missing in GitHub  g3h4i5j6     -

======================================================================
📝 동기화 요약
======================================================================
⚠ 동기화 문제가 발견되었습니다.

브랜치:
  - 동기화됨: 3개
  - 커밋 차이: 1개
  - GitHub 누락: 1개

태그:
  - 동기화됨: 2개
  - GitHub 누락: 1개

======================================================================
🎯 전체 요약
======================================================================
ℹ 완전 동기화: 2개
⚠ 동기화 문제: 1개
```

### 출력 항목 설명

#### 브랜치 상태
- `✓ Synced` - 완전히 동기화됨 (커밋 SHA 일치)
- `⚠ Different` - 브랜치가 존재하지만 커밋이 다름
- `✗ Missing in GitHub` - GitLab에만 존재
- `✗ Extra in GitHub` - GitHub에만 존재

#### Behind 상세정보
GitHub가 GitLab보다 뒤처진 경우 다음 정보를 표시:
- **커밋 개수 차이** - "GitHub가 N개 커밋 뒤처짐"
- **커밋 목록** (최대 10개)
  - 커밋 SHA (8자리)
  - 커밋 메시지 (첫 줄, 최대 60자)
  - 작성자 이름
  - 커밋 날짜/시간

### 사용 시나리오

#### 시나리오 1: 마이그레이션 후 검증
```bash
# 1. 마이그레이션 실행
python migrate.py

# 2. 동기화 상태 확인
python check_sync.py

# 3. 문제가 있다면 해당 저장소만 재이관
```

#### 시나리오 2: 정기적인 동기화 확인
```bash
# 주기적으로 실행하여 GitLab과 GitHub가 계속 동기화되는지 확인
python check_sync.py
```

#### 시나리오 3: 특정 저장소만 확인
config.json의 `repositories` 섹션을 편집하여 확인하고 싶은 저장소만 남기고:
```bash
python check_sync.py
```

### 주의사항

- 📊 **API 호출 비용** - 브랜치/태그가 많으면 API 호출이 많아집니다
- ⏱️ **실행 시간** - 저장소와 브랜치 개수에 따라 시간이 소요됩니다
- 🔄 **Rate Limit** - 적응형 딜레이가 적용되어 자동으로 조절됩니다
- 🔐 **권한 필요** - GitLab read_repository, GitHub repo 권한 필요

### 동기화 문제 해결

동기화 문제가 발견된 경우:

1. **브랜치 누락** (`Missing in GitHub`)
   - 해당 브랜치를 수동으로 푸시
   - 또는 저장소 전체 재이관

2. **커밋 차이** (`Different`)
   - Behind 상세정보로 어떤 커밋이 누락되었는지 확인
   - `git push --force`로 강제 동기화 (주의 필요)
   - 또는 저장소 재이관

3. **태그 누락**
   - `git push --tags`로 태그만 푸시
   - 또는 저장소 재이관

## 이관 대시보드 (dashboard.py)

마이그레이션 상태를 시각적으로 확인할 수 있는 HTML 대시보드를 생성합니다.

### 기능

- 📊 **통계 요약** - 전체 대상, 이관 완료, 미완료, 동기화 필요 개수 표시
- 📋 **브랜치별 상세 정보** - GitLab/GitHub 브랜치별 커밋 비교
- 🎨 **시각적 대시보드** - 컬러풀하고 직관적인 HTML 인터페이스
- 🔍 **필터링 기능** - 상태별로 결과 필터링 (전체/완료/미완료/동기화 필요)
- 🔄 **자동 스캔** - config.json의 scan_groups 자동 처리

### 기본 사용법

```bash
# config.json의 모든 저장소 상태 확인하고 대시보드 생성
python dashboard.py

# 특정 설정 파일 사용
python dashboard.py my_config.json

# 출력 파일 이름 지정
python dashboard.py config.json my_dashboard.html

# API를 다시 조회하여 최신 상태 확인 (migration_results.json 무시)
python dashboard.py --refresh
```

**동작 방식:**
- `migration_results.json` 파일이 있으면 API 조회 없이 빠르게 대시보드 생성
- 파일이 없거나 `--refresh` 옵션 사용 시 GitLab/GitHub API를 조회
- `migrate.py` 실행 후 자동으로 대시보드가 생성됨 (dry_run 제외)

### 출력 내용

#### 터미널 출력
```
╔══════════════════════════════════════════════════════════╗
║     GitLab to GitHub Migration Dashboard                ║
║     이관 상태 확인 및 대시보드 생성                      ║
╚══════════════════════════════════════════════════════════╝

그룹 스캔 중...
  그룹 'icis/rater': 15개 프로젝트 발견

총 15개 저장소 상태 확인 중...

[1/15] dag-manager 확인 중...
[2/15] data-processor 확인 중...
...

=== 통계 요약 ===
전체 대상: 15
이관 완료: 10
이관 대상 미완료: 3
동기화 필요: 2

대시보드 생성 완료: dashboard.html
```

#### HTML 대시보드

생성된 `dashboard.html` 파일을 브라우저에서 열면:

**통계 카드 (4개)**
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 전체 대상    │ │ 이관 완료    │ │ 이관대상미완료│ │ 동기화 필요  │
│     15       │ │     10       │ │      3       │ │      2       │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

**필터 버튼**
- [전체 보기] [이관 완료] [미완료] [동기화 필요]

**상세 테이블**
| GitLab Project | GitHub Repository | Branch | GitLab Commit | GitHub Commit | Status |
|----------------|-------------------|--------|---------------|---------------|--------|
| icis/rater/dag-manager | my-org/dag-manager | main | a1b2c3d | a1b2c3d | completed |
| icis/rater/dag-manager | my-org/dag-manager | develop | e5f6g7h | e5f6g7h | completed |
| icis/rater/processor | my-org/processor | main | i9j0k1l | - | not created |
| icis/rater/engine | my-org/engine | feature/api | m3n4o5p | q7r8s9t | sync needed |

### 상태 설명

- **completed** (초록색) - GitHub 저장소가 존재하고 커밋이 일치
- **not created** (빨간색) - GitHub 저장소가 아직 생성되지 않음
- **sync needed** (주황색) - GitHub 저장소는 있지만 커밋이 다름

### 대시보드 특징

1. **반응형 디자인** - 모바일/태블릿/데스크톱 모두 지원
2. **실시간 필터링** - JavaScript로 클라이언트 측 필터링
3. **링크 제공** - GitHub 저장소로 직접 이동 가능
4. **컬러 코딩** - 상태별로 다른 색상 표시
5. **자동 새로고침 시간** - 마지막 업데이트 시간 표시

### 사용 시나리오

#### 시나리오 1: 마이그레이션 진행 상황 모니터링
```bash
# 1. 마이그레이션 시작
python migrate.py

# 2. 대시보드 생성하여 진행 상황 확인
python dashboard.py

# 3. 브라우저에서 dashboard.html 열기
# 4. 주기적으로 재실행하여 진행 상황 업데이트
```

#### 시나리오 2: 관리자에게 보고
```bash
# 대시보드 생성
python dashboard.py

# dashboard.html을 이메일에 첨부하거나 공유
# 또는 웹 서버에 호스팅하여 실시간 공유
```

#### 시나리오 3: 문제 있는 저장소 식별
```bash
# 대시보드 생성
python dashboard.py

# 브라우저에서 열어서 "미완료" 또는 "동기화 필요" 필터 클릭
# 문제가 있는 저장소만 확인하고 수정
```

### 주의사항

- 📊 **API 호출** - 모든 저장소와 브랜치 정보를 조회하므로 시간이 소요될 수 있습니다
- ⏱️ **실행 시간** - 저장소가 많을 경우 수 분 소요될 수 있습니다
- 🔄 **자동 갱신 없음** - 대시보드는 정적 HTML이므로 최신 상태를 보려면 재실행 필요
- 🔐 **권한 필요** - GitLab read_repository, GitHub repo 권한 필요

### 웹에서 Refresh/Migrate 실행 ✨ NEW

대시보드에서 직접 refresh와 migrate를 실행할 수 있습니다 (표준 라이브러리만 사용):

```bash
# 1. Dashboard 서버 시작
python dashboard_server.py

# 2. 브라우저에서 접속
# http://localhost:8080

# 3. 대시보드에서 버튼 클릭
# - 🔄 대시보드 새로고침: API를 다시 조회하여 최신 상태 업데이트
# - 🚀 마이그레이션 시작: 백그라운드에서 migrate.py 실행
```

**특징:**
- 웹 브라우저에서 버튼 클릭만으로 실행 가능
- 마이그레이션은 백그라운드에서 실행
- 완료 시 자동으로 대시보드 업데이트
- 서버 실행 여부 자동 감지 및 안내

**주의:**
- dashboard_server.py가 실행 중이어야 버튼 기능 사용 가능
- 서버가 없으면 안내 메시지 표시
- 마이그레이션은 30초마다 상태 확인 후 자동 새로고침

### 웹 서버로 호스팅 (선택사항)

대시보드를 팀과 공유하려면 위의 dashboard_server.py를 사용하거나, 단순 조회만 필요한 경우 정적 서버를 사용할 수 있습니다:

```bash
# 정적 파일만 제공 (버튼 기능 없음)
python -m http.server 8000

# 브라우저에서 열기
# http://localhost:8000/dashboard.html
```

### 정기적 업데이트 자동화 (선택사항)

cron job이나 스케줄러로 주기적으로 대시보드를 업데이트할 수 있습니다:

```bash
# Linux/macOS crontab 예시 (매 시간마다 실행)
0 * * * * cd /path/to/github_mig && python dashboard.py

# Windows Task Scheduler
# dashboard.py를 주기적으로 실행하도록 설정
```

## GitLab 프로젝트 ID/경로 찾기

### 방법 1: GitLab UI
1. 프로젝트 페이지 접속
2. 프로젝트 이름 아래에 "Project ID: 12345678" 표시

### 방법 2: GitLab API
```bash
curl --header "PRIVATE-TOKEN: YOUR_TOKEN" \
  "https://gitlab.com/api/v4/projects?search=project-name"
```

### 방법 3: 프로젝트 경로 사용
URL이 `https://gitlab.com/mygroup/myproject`라면:
```json
{
  "gitlab_project_path": "mygroup/myproject"
}
```

## 예제

### 예제 1: GitLab 그룹 전체 자동 스캔 및 이관

```json
{
  "gitlab": {
    "url": "https://gitlab.com",
    "token": "glpat-xxxxxxxxxxxx"
  },
  "github": {
    "token": "ghp_xxxxxxxxxxxx",
    "organization": "my-company"
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

이 설정은:
- `icis/rater` 그룹과 하위 모든 서브그룹(airflow, batch, engine, uq 등)의 프로젝트를 자동 검색
- GitHub 저장소 이름은 프로젝트 이름만 사용
- `my-company` Organization에 비공개 저장소로 생성
- dry_run 모드로 먼저 시뮬레이션

### 예제 2: 단일 저장소 이관

```json
{
  "gitlab": {
    "url": "https://gitlab.com",
    "token": "glpat-xxxxxxxxxxxx"
  },
  "github": {
    "token": "ghp_xxxxxxxxxxxx",
    "organization": ""
  },
  "scan_groups": [],
  "repositories": [
    {
      "gitlab_project_path": "myuser/awesome-project",
      "github_repo_name": "awesome-project",
      "description": "My awesome project",
      "private": true
    }
  ],
  "options": {
    "clone_method": "https",
    "preserve_branches": true,
    "preserve_tags": true,
    "dry_run": false
  }
}
```

### 예제 3: 여러 저장소를 Organization으로 이관

```json
{
  "gitlab": {
    "url": "https://gitlab.company.com",
    "token": "glpat-xxxxxxxxxxxx"
  },
  "github": {
    "token": "ghp_xxxxxxxxxxxx",
    "organization": "my-organization"
  },
  "scan_groups": [],
  "repositories": [
    {
      "gitlab_project_id": "123",
      "github_repo_name": "backend-api",
      "private": true
    },
    {
      "gitlab_project_id": "456",
      "github_repo_name": "frontend-app",
      "private": true
    },
    {
      "gitlab_project_path": "team/mobile-app",
      "github_repo_name": "mobile-app",
      "private": false
    }
  ],
  "options": {
    "clone_method": "https",
    "preserve_branches": true,
    "preserve_tags": true,
    "dry_run": false
  }
}
```

### 예제 4: Collaborators와 Teams 권한 부여 포함

특정 사용자와 팀에게 자동으로 저장소 권한을 부여:

```json
{
  "gitlab": {
    "url": "https://gitlab.com",
    "token": "glpat-xxxxxxxxxxxx"
  },
  "github": {
    "token": "ghp_xxxxxxxxxxxx",
    "organization": "my-company"
  },
  "scan_groups": [
    {
      "group_path": "icis/rater",
      "include_subgroups": true,
      "naming_rule": "project_name",
      "default_private": true,
      "default_collaborators": [
        {
          "username": "devops-user",
          "permission": "admin"
        },
        {
          "username": "qa-tester",
          "permission": "pull"
        }
      ],
      "default_teams": [
        {
          "team_slug": "backend-developers",
          "permission": "push"
        },
        {
          "team_slug": "platform-team",
          "permission": "admin"
        }
      ]
    }
  ],
  "repositories": [
    {
      "gitlab_project_path": "special/critical-service",
      "github_repo_name": "critical-service",
      "private": true,
      "collaborators": [
        {
          "username": "security-admin",
          "permission": "admin"
        },
        {
          "username": "external-contractor",
          "permission": "pull"
        }
      ],
      "teams": [
        {
          "team_slug": "core-team",
          "permission": "admin"
        },
        {
          "team_slug": "operations",
          "permission": "push"
        }
      ]
    }
  ],
  "options": {
    "clone_method": "https",
    "preserve_branches": true,
    "preserve_tags": true,
    "dry_run": false
  }
}
```

이 설정은:
- `icis/rater` 그룹의 모든 프로젝트에 `devops-user`, `qa-tester` 사용자와 `backend-developers`, `platform-team` 팀 권한 자동 부여
- `critical-service` 저장소에는 추가로 `security-admin`, `external-contractor` 사용자와 `core-team`, `operations` 팀 권한 부여
- Organization에서만 teams 기능 사용 가능
- 개인 계정에서는 collaborators만 사용 가능

## 문제 해결

### Git 명령을 찾을 수 없음
```bash
# Git이 설치되어 있는지 확인
git --version

# 없다면 설치
# Ubuntu/Debian
sudo apt-get install git

# macOS
brew install git

# Windows
# https://git-scm.com/download/win 에서 다운로드
```

### UnicodeEncodeError (Windows)

Windows 콘솔에서 유니코드 문자 출력 시 오류가 발생할 수 있습니다.

**해결 방법:**

**방법 1: 콘솔 코드 페이지 변경 (권장)**
```cmd
# CMD에서 실행 전
chcp 65001
python test_connection.py
```

**방법 2: PowerShell UTF-8 설정**
```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
python test_connection.py
```

**방법 3: Windows Terminal 사용**
- Windows Terminal (Microsoft Store에서 설치)을 사용하면 자동으로 UTF-8 지원

**참고:** 이 버전의 스크립트는 이미 Windows 환경을 자동 감지하여 UTF-8 인코딩을 적용합니다. 하지만 일부 구형 Windows 시스템에서는 위 방법이 필요할 수 있습니다.

### 인증 실패
- GitLab/GitHub 토큰이 올바른지 확인
- 토큰에 필요한 권한이 있는지 확인
- 토큰이 만료되지 않았는지 확인

### 저장소가 이미 존재함
프로그램이 기존 저장소를 사용하려고 시도합니다. 새로 만들려면:
1. GitHub에서 기존 저장소 삭제
2. 또는 다른 이름으로 이관

### SSL 인증서 검증 오류 (회사 방화벽/프록시)

회사 방화벽이나 프록시에서 HTTPS 트래픽을 검사하는 경우 `SSL: CERTIFICATE_VERIFY_FAILED` 오류가 발생할 수 있습니다.

**해결 방법: config.json에서 SSL 검증 비활성화**

```json
{
  "options": {
    "verify_ssl": false
  }
}
```

⚠️ **주의사항:**
- SSL 검증을 비활성화하면 중간자 공격(MITM)에 취약해집니다
- 신뢰할 수 있는 내부 네트워크에서만 사용하세요
- 가능하면 회사 SSL 인증서를 시스템에 설치하는 것이 더 안전합니다

**더 안전한 방법: 회사 SSL 인증서 설치**

회사 IT 부서에 문의하여 회사 루트 인증서를 받아 설치하세요:

```bash
# Windows: certmgr.msc에서 "신뢰할 수 있는 루트 인증 기관"에 추가
# macOS: Keychain Access에서 시스템 키체인에 추가
# Linux: /usr/local/share/ca-certificates/에 복사 후 update-ca-certificates
```

## 주의사항

1. **토큰 보안**: `config.json`을 절대 Git에 커밋하지 마세요
2. **백업**: 이관 전 중요한 데이터는 백업하세요
3. **Rate Limit**: API 호출 제한에 주의하세요 (저장소 간 2초 대기)
4. **대용량 저장소**: 매우 큰 저장소는 시간이 오래 걸릴 수 있습니다
5. **디스크 공간**: 임시 디렉토리에 저장소 크기만큼 여유 공간 필요

## 제한사항

이 도구는 **Git 저장소와 기본 권한**만 이관합니다. 다음은 이관되지 않습니다:

- ❌ GitLab Issues
- ❌ Merge Requests
- ❌ CI/CD 설정
- ❌ Wiki
- ❌ Snippets
- ❌ Labels, Milestones
- ⚠️ **멤버 및 권한**: GitLab 멤버는 자동 이관되지 않지만, config.json에서 Collaborators와 Teams를 지정하여 GitHub 저장소에 권한 부여 가능

이러한 데이터가 필요하면 GitLab/GitHub API를 사용하여 별도로 이관해야 합니다.

## 라이선스

MIT License

## 기여

버그 리포트나 기능 제안은 Issue로 등록해 주세요.
