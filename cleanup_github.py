#!/usr/bin/env python3
"""
GitHub 저장소 일괄 삭제 도구
마이그레이션 전에 기존 GitHub 저장소들을 삭제합니다.
"""

import json
import sys
import io
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List
import time


# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


class Colors:
    """ANSI 색상 코드"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class GitLabScanner:
    """GitLab 그룹 스캔 클래스"""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.api_url = f"{self.url}/api/v4"

    def _make_request_list(self, endpoint: str, params: Dict = None) -> List[Dict]:
        """API 요청 수행 (페이지네이션)"""
        all_results = []
        page = 1
        per_page = 100

        while True:
            query_params = params.copy() if params else {}
            query_params['page'] = page
            query_params['per_page'] = per_page

            query_string = urllib.parse.urlencode(query_params)
            url = f"{self.api_url}/{endpoint.lstrip('/')}?{query_string}"

            headers = {
                'PRIVATE-TOKEN': self.token,
                'Content-Type': 'application/json'
            }

            request = urllib.request.Request(url, headers=headers)

            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    results = json.loads(response.read().decode('utf-8'))

                    if not results:
                        break

                    all_results.extend(results)

                    if len(results) < per_page:
                        break

                    page += 1

            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                raise Exception(f"GitLab API 오류 ({e.code}): {error_body}")

        return all_results

    def get_group_projects(self, group_id: str, include_subgroups: bool = True) -> List[Dict]:
        """그룹 내 모든 프로젝트 가져오기"""
        encoded_id = urllib.parse.quote(str(group_id), safe='')
        params = {
            'include_subgroups': 'true' if include_subgroups else 'false',
            'archived': 'false'
        }
        return self._make_request_list(f"groups/{encoded_id}/projects", params)


class GitHubCleaner:
    """GitHub 저장소 일괄 삭제 클래스"""

    def __init__(self, token: str, organization: str = None, verify_ssl: bool = True):
        self.token = token
        self.organization = organization
        self.verify_ssl = verify_ssl
        self.api_url = "https://api.github.com"
        self.user = self._get_authenticated_user()

    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None, retry_count: int = 0) -> Dict:
        """
        API 요청 수행 (Rate limit 처리 포함)

        Args:
            endpoint: API 엔드포인트
            method: HTTP 메서드
            data: 요청 데이터
            retry_count: 재시도 횟수 (내부 사용)
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        req_data = json.dumps(data).encode('utf-8') if data else None
        request = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        max_retries = 3
        base_delay = 2  # 기본 딜레이 (초)

        try:
            import ssl
            if not self.verify_ssl:
                context = ssl._create_unverified_context()
                with urllib.request.urlopen(request, context=context, timeout=10) as response:
                    response_data = response.read().decode('utf-8')
                    # API 요청 사이 기본 딜레이 (rate limit 방지)
                    time.sleep(0.5)
                    return json.loads(response_data) if response_data else {}
            else:
                with urllib.request.urlopen(request, timeout=10) as response:
                    response_data = response.read().decode('utf-8')
                    # API 요청 사이 기본 딜레이 (rate limit 방지)
                    time.sleep(0.5)
                    return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # 저장소 없음

            # 429 (Too Many Requests) 또는 403 (Secondary rate limit) 처리
            if e.code in [429, 403] and retry_count < max_retries:
                error_body = e.read().decode('utf-8')

                # Retry-After 헤더 확인
                retry_after = e.headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    # Exponential backoff
                    wait_time = base_delay * (2 ** retry_count)

                # Secondary rate limit 메시지 확인
                if 'secondary rate limit' in error_body.lower() or e.code == 403:
                    wait_time = max(wait_time, 60)  # 최소 60초 대기

                print(f"\n{Colors.YELLOW}⚠ Rate limit 도달. {wait_time}초 대기 후 재시도... (시도 {retry_count + 1}/{max_retries}){Colors.RESET}")
                time.sleep(wait_time)

                # 재시도
                return self._make_request(endpoint, method, data, retry_count + 1)

            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"연결 실패: {e.reason}")

    def _get_authenticated_user(self) -> Dict:
        """인증된 사용자 정보"""
        return self._make_request('user')

    def check_repo_exists(self, repo_name: str) -> bool:
        """저장소 존재 여부 확인"""
        owner = self.organization if self.organization else self.user['login']
        repo_info = self._make_request(f"repos/{owner}/{repo_name}")
        return repo_info is not None

    def delete_repo(self, repo_name: str, dry_run: bool = False) -> bool:
        """저장소 삭제"""
        owner = self.organization if self.organization else self.user['login']

        if dry_run:
            print(f"{Colors.YELLOW}[DRY RUN] {repo_name} 삭제 예정{Colors.RESET}")
            return True

        try:
            self._make_request(f"repos/{owner}/{repo_name}", method='DELETE')
            print(f"{Colors.GREEN}✓ {repo_name} 삭제 완료{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.RED}✗ {repo_name} 삭제 실패: {e}{Colors.RESET}")
            return False

    def list_target_repos(self, repo_names: List[str]) -> List[Dict]:
        """삭제 대상 저장소 목록"""
        owner = self.organization if self.organization else self.user['login']
        existing_repos = []

        print(f"\n{Colors.CYAN}GitHub 저장소 확인 중...{Colors.RESET}")

        for repo_name in repo_names:
            repo_info = self._make_request(f"repos/{owner}/{repo_name}")
            if repo_info:
                existing_repos.append({
                    'name': repo_name,
                    'full_name': repo_info['full_name'],
                    'url': repo_info['html_url'],
                    'private': repo_info['private']
                })

        return existing_repos


def load_config(config_path: str = "config.json") -> Dict:
    """설정 파일 로드"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{Colors.RED}✗ 설정 파일을 찾을 수 없습니다: {config_path}{Colors.RESET}")
        sys.exit(1)


def get_repo_names_from_config(config: Dict) -> List[str]:
    """config.json에서 저장소 이름 추출"""
    repo_names = []

    # scan_groups에서 프로젝트 이름 추출 (GitLab 스캔)
    scan_groups = config.get('scan_groups', [])
    if scan_groups:
        print(f"\n{Colors.CYAN}GitLab 그룹 스캔 중...{Colors.RESET}")

        try:
            scanner = GitLabScanner(
                config['gitlab']['url'],
                config['gitlab']['token']
            )

            for group_config in scan_groups:
                group_id = group_config.get('group_id') or group_config.get('group_path')
                if not group_id:
                    continue

                include_subgroups = group_config.get('include_subgroups', True)
                naming_rule = group_config.get('naming_rule', 'project_name')

                print(f"{Colors.CYAN}  그룹: {group_id}{Colors.RESET}")

                projects = scanner.get_group_projects(group_id, include_subgroups)

                print(f"{Colors.GREEN}  {len(projects)}개의 프로젝트 발견{Colors.RESET}")

                for project in projects:
                    # GitHub 저장소 이름 결정 (migrate.py와 동일한 로직)
                    if naming_rule == 'project_name':
                        github_name = project['name']
                    elif naming_rule == 'path_with_namespace':
                        github_name = project['path_with_namespace'].replace('/', '-')
                    else:
                        github_name = project['name']

                    repo_names.append(github_name)

        except Exception as e:
            print(f"{Colors.RED}✗ GitLab 스캔 실패: {e}{Colors.RESET}")
            print(f"{Colors.YELLOW}  -r 옵션으로 수동으로 저장소 이름을 지정하세요.{Colors.RESET}")
            return []

    # repositories에서 저장소 이름 추가
    repositories = config.get('repositories', [])
    for repo in repositories:
        repo_names.append(repo['github_repo_name'])

    return repo_names


def confirm_deletion(repos: List[Dict]) -> bool:
    """삭제 확인"""
    print(f"\n{Colors.RED}{Colors.BOLD}{'='*70}")
    print(f"경고: 다음 저장소들이 영구적으로 삭제됩니다!")
    print(f"{'='*70}{Colors.RESET}\n")

    for idx, repo in enumerate(repos, 1):
        visibility = "🔒 비공개" if repo['private'] else "🌍 공개"
        print(f"{idx}. {repo['full_name']} ({visibility})")
        print(f"   URL: {repo['url']}")

    print(f"\n{Colors.RED}총 {len(repos)}개의 저장소가 삭제됩니다.{Colors.RESET}")
    print(f"{Colors.YELLOW}이 작업은 되돌릴 수 없습니다!{Colors.RESET}\n")

    # 확인 입력
    confirmation = input(f"계속하려면 '{Colors.BOLD}DELETE{Colors.RESET}'를 정확히 입력하세요: ")

    return confirmation == "DELETE"


def main():
    """메인 함수"""
    print(f"""
{Colors.RED}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║     GitHub 저장소 일괄 삭제 도구                         ║
║     ⚠ 경고: 이 작업은 되돌릴 수 없습니다!                ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
""")

    # 명령행 인자 파싱
    import sys
    config_path = "config.json"
    dry_run = False
    repo_names_manual = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['-c', '--config']:
            config_path = sys.argv[i + 1]
            i += 2
        elif arg in ['-d', '--dry-run']:
            dry_run = True
            i += 1
        elif arg in ['-r', '--repos']:
            # 쉼표로 구분된 저장소 이름
            repo_names_manual = sys.argv[i + 1].split(',')
            i += 2
        elif arg in ['-h', '--help']:
            print(f"""
{Colors.CYAN}사용법:{Colors.RESET}
  python cleanup_github.py [OPTIONS]

{Colors.CYAN}옵션:{Colors.RESET}
  -c, --config FILE       설정 파일 경로 (기본: config.json)
  -d, --dry-run          실제 삭제 안 함 (시뮬레이션)
  -r, --repos NAMES      삭제할 저장소 이름 (쉼표로 구분)
                         예: -r "repo1,repo2,repo3"
  -h, --help             도움말 표시

{Colors.CYAN}예제:{Colors.RESET}
  # config.json의 저장소 삭제 (dry run)
  python cleanup_github.py -d

  # 특정 저장소만 삭제
  python cleanup_github.py -r "project1,project2,project3"

  # 실제 삭제 실행
  python cleanup_github.py

{Colors.RED}주의사항:{Colors.RESET}
  - 삭제된 저장소는 복구할 수 없습니다
  - 먼저 -d 옵션으로 dry run을 실행하세요
  - Organization 저장소는 admin 권한이 필요합니다
""")
            sys.exit(0)
        else:
            print(f"{Colors.RED}✗ 알 수 없는 옵션: {arg}{Colors.RESET}")
            sys.exit(1)

    # 설정 로드
    config = load_config(config_path)

    # 저장소 이름 결정
    if repo_names_manual:
        repo_names = [name.strip() for name in repo_names_manual]
        print(f"{Colors.CYAN}수동 지정된 저장소: {len(repo_names)}개{Colors.RESET}")
    else:
        repo_names = get_repo_names_from_config(config)
        if not repo_names:
            print(f"{Colors.RED}✗ 삭제할 저장소가 없습니다.{Colors.RESET}")
            print(f"{Colors.YELLOW}  -r 옵션으로 저장소 이름을 지정하거나,{Colors.RESET}")
            print(f"{Colors.YELLOW}  config.json의 repositories를 설정하세요.{Colors.RESET}")
            sys.exit(1)

    # GitHub 클라이언트 초기화
    verify_ssl = config.get('options', {}).get('verify_ssl', True)
    cleaner = GitHubCleaner(
        config['github']['token'],
        config['github'].get('organization'),
        verify_ssl
    )

    print(f"{Colors.CYAN}GitHub 계정: {cleaner.user['login']}{Colors.RESET}")
    if cleaner.organization:
        print(f"{Colors.CYAN}Organization: {cleaner.organization}{Colors.RESET}")

    # 존재하는 저장소 확인
    existing_repos = cleaner.list_target_repos(repo_names)

    if not existing_repos:
        print(f"\n{Colors.GREEN}✓ 삭제할 저장소가 없습니다. (모두 없거나 이미 삭제됨){Colors.RESET}")
        sys.exit(0)

    print(f"\n{Colors.GREEN}발견된 저장소: {len(existing_repos)}개{Colors.RESET}")

    # Dry run 모드
    if dry_run:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}[DRY RUN 모드]{Colors.RESET}")
        print(f"{Colors.YELLOW}실제 삭제는 수행되지 않습니다.{Colors.RESET}\n")

        for idx, repo in enumerate(existing_repos, 1):
            visibility = "🔒 비공개" if repo['private'] else "🌍 공개"
            print(f"{idx}. {repo['full_name']} ({visibility})")

        print(f"\n{Colors.CYAN}실제 삭제하려면 -d 옵션 없이 실행하세요:{Colors.RESET}")
        print(f"{Colors.WHITE}  python cleanup_github.py{Colors.RESET}")
        sys.exit(0)

    # 삭제 확인
    if not confirm_deletion(existing_repos):
        print(f"\n{Colors.YELLOW}삭제가 취소되었습니다.{Colors.RESET}")
        sys.exit(0)

    # 삭제 실행
    print(f"\n{Colors.RED}삭제를 시작합니다...{Colors.RESET}\n")

    success_count = 0
    fail_count = 0

    for idx, repo in enumerate(existing_repos, 1):
        print(f"[{idx}/{len(existing_repos)}] {repo['name']} 삭제 중...", end=' ')

        if cleaner.delete_repo(repo['name'], dry_run=False):
            success_count += 1
        else:
            fail_count += 1

        # API rate limit 고려 (저장소 삭제 후 대기)
        if idx < len(existing_repos):
            time.sleep(2)

    # 최종 결과
    print(f"\n{Colors.CYAN}{'='*70}")
    print(f"삭제 완료")
    print(f"{'='*70}{Colors.RESET}")
    print(f"{Colors.GREEN}성공: {success_count}개{Colors.RESET}")
    if fail_count > 0:
        print(f"{Colors.RED}실패: {fail_count}개{Colors.RESET}")

    if success_count > 0:
        print(f"\n{Colors.CYAN}이제 마이그레이션을 실행할 수 있습니다:{Colors.RESET}")
        print(f"{Colors.WHITE}  python migrate.py{Colors.RESET}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}사용자에 의해 중단되었습니다.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}오류: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
