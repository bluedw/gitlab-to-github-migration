#!/usr/bin/env python3
"""
GitLab/GitHub 연결 및 그룹 스캔 테스트 도구
실제 마이그레이션 없이 연결성과 프로젝트 목록만 확인합니다.
"""

import json
import sys
import io
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List


# Windows 콘솔 UTF-8 인코딩 설정 (UnicodeEncodeError 방지)
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # 이미 재설정된 경우 무시


class Colors:
    """ANSI 색상 코드"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """헤더 출력"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.RESET}\n")


def print_success(text: str):
    """성공 메시지 출력"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """에러 메시지 출력"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    """정보 메시지 출력"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def print_warning(text: str):
    """경고 메시지 출력"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


class GitLabTester:
    """GitLab 연결 및 그룹 스캔 테스터"""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.api_url = f"{self.url}/api/v4"

    def _make_request(self, endpoint: str) -> Dict:
        """API 요청 수행"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {
            'PRIVATE-TOKEN': self.token,
            'Content-Type': 'application/json'
        }

        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response_text = response.read().decode('utf-8')

                # 디버깅: 응답이 비어있는지 확인
                if not response_text or not response_text.strip():
                    raise Exception(f"빈 응답을 받았습니다. URL: {url}")

                # JSON 파싱 시도
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as je:
                    # JSON이 아닌 응답인 경우 (HTML 등)
                    preview = response_text[:200] if len(response_text) > 200 else response_text
                    raise Exception(
                        f"JSON 파싱 실패. API 응답이 JSON이 아닙니다.\n"
                        f"요청 URL: {url}\n"
                        f"응답 미리보기: {preview}\n"
                        f"오류: {je}"
                    )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(
                f"HTTP {e.code} 오류\n"
                f"요청 URL: {url}\n"
                f"응답: {error_body[:200] if len(error_body) > 200 else error_body}"
            )
        except urllib.error.URLError as e:
            raise Exception(
                f"연결 실패\n"
                f"요청 URL: {url}\n"
                f"원인: {e.reason}"
            )

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
                raise Exception(f"HTTP {e.code}: {error_body}")
            except urllib.error.URLError as e:
                raise Exception(f"연결 실패: {e.reason}")

        return all_results

    def test_connection(self) -> bool:
        """GitLab 연결 테스트"""
        print_header("1. GitLab 연결 테스트")

        try:
            print_info(f"GitLab URL: {self.url}")
            print_info("인증 정보로 연결 중...")

            user = self._make_request('user')

            print_success("GitLab 연결 성공!")
            print(f"  - 사용자: {Colors.BOLD}{user['username']}{Colors.RESET} ({user['name']})")
            print(f"  - 이메일: {user.get('email', 'N/A')}")
            print(f"  - ID: {user['id']}")

            return True

        except Exception as e:
            print_error(f"GitLab 연결 실패: {e}")
            return False

    def scan_group(self, group_id: str, include_subgroups: bool = True) -> List[Dict]:
        """그룹 스캔"""
        print_header("2. GitLab 그룹 스캔")

        try:
            print_info(f"그룹: {group_id}")
            print_info(f"서브그룹 포함: {include_subgroups}")

            # 그룹 정보 가져오기
            encoded_id = urllib.parse.quote(str(group_id), safe='')
            group = self._make_request(f"groups/{encoded_id}")

            print_success("그룹 정보 조회 성공!")
            print(f"  - 그룹 이름: {Colors.BOLD}{group['name']}{Colors.RESET}")
            print(f"  - 전체 경로: {group['full_path']}")
            print(f"  - ID: {group['id']}")

            # 프로젝트 목록 가져오기
            print_info("\n프로젝트 목록 조회 중...")

            params = {
                'include_subgroups': 'true' if include_subgroups else 'false',
                'archived': 'false'
            }

            projects = self._make_request_list(f"groups/{encoded_id}/projects", params)

            print_success(f"총 {len(projects)}개의 프로젝트 발견\n")

            return projects

        except Exception as e:
            print_error(f"그룹 스캔 실패: {e}")
            return []


class GitHubTester:
    """GitHub 연결 테스터"""

    def __init__(self, token: str, organization: str = None, verify_ssl: bool = True):
        self.token = token
        self.organization = organization
        self.api_url = "https://api.github.com"
        self.verify_ssl = verify_ssl

    def _make_request(self, endpoint: str) -> Dict:
        """API 요청 수행"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        request = urllib.request.Request(url, headers=headers)

        try:
            # SSL 검증 설정
            import ssl
            if not self.verify_ssl:
                context = ssl._create_unverified_context()
                with urllib.request.urlopen(request, timeout=10, context=context) as response:
                    response_data = response.read().decode('utf-8')
                    return json.loads(response_data) if response_data else {}
            else:
                with urllib.request.urlopen(request, timeout=10) as response:
                    response_data = response.read().decode('utf-8')
                    return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"연결 실패: {e.reason}")

    def test_connection(self) -> bool:
        """GitHub 연결 테스트"""
        print_header("3. GitHub 연결 테스트")

        try:
            print_info("GitHub에 연결 중...")

            user = self._make_request('user')

            print_success("GitHub 연결 성공!")
            print(f"  - 사용자: {Colors.BOLD}{user['login']}{Colors.RESET}")
            print(f"  - 이름: {user.get('name', 'N/A')}")
            print(f"  - 이메일: {user.get('email', 'N/A')}")

            # Organization 확인
            if self.organization:
                print_info(f"\nOrganization 확인 중: {self.organization}")
                try:
                    org = self._make_request(f"orgs/{self.organization}")
                    print_success(f"Organization 접근 가능!")
                    print(f"  - 이름: {Colors.BOLD}{org['login']}{Colors.RESET}")
                    print(f"  - 설명: {org.get('description', 'N/A')}")
                except Exception as e:
                    print_error(f"Organization 접근 실패: {e}")
                    print_warning("저장소는 개인 계정에 생성됩니다.")

            return True

        except Exception as e:
            print_error(f"GitHub 연결 실패: {e}")
            return False


def print_project_table(projects: List[Dict], naming_rule: str = 'project_name'):
    """프로젝트 목록을 표 형식으로 출력"""
    print_header("발견된 프로젝트 목록")

    if not projects:
        print_warning("프로젝트가 없습니다.")
        return

    # 테이블 헤더
    print(f"{Colors.BOLD}{'No.':<5} {'GitLab 프로젝트':<50} {'→':<3} {'GitHub 저장소 이름':<30}{Colors.RESET}")
    print("-" * 90)

    # 프로젝트 목록
    for idx, project in enumerate(projects, 1):
        gitlab_path = project['path_with_namespace']

        # GitHub 저장소 이름 결정
        if naming_rule == 'project_name':
            github_name = project['name']
        elif naming_rule == 'path_with_namespace':
            github_name = project['path_with_namespace'].replace('/', '-')
        else:
            github_name = project['path']

        # 색상 적용
        if idx % 2 == 0:
            color = Colors.RESET
        else:
            color = Colors.BLUE

        print(f"{color}{idx:<5} {gitlab_path:<50} {'→':<3} {github_name:<30}{Colors.RESET}")

    print("\n" + "=" * 90)
    print(f"{Colors.GREEN}총 {len(projects)}개 프로젝트가 이관 대상입니다.{Colors.RESET}")


def load_config(config_path: str = "config.json") -> Dict:
    """설정 파일 로드"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print_error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"설정 파일 파싱 오류: {e}")
        sys.exit(1)


def main():
    """메인 함수"""
    print(f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║     GitLab/GitHub 연결 테스트 도구                      ║
║     실제 마이그레이션 없이 연결성만 확인합니다           ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
""")

    # 설정 파일 경로
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    print_info(f"설정 파일: {config_path}\n")

    # 설정 로드
    config = load_config(config_path)

    # GitLab 테스트
    gitlab_tester = GitLabTester(
        config['gitlab']['url'],
        config['gitlab']['token']
    )

    if not gitlab_tester.test_connection():
        print_error("\nGitLab 연결에 실패했습니다. 토큰을 확인하세요.")
        sys.exit(1)

    # 그룹 스캔
    scan_groups = config.get('scan_groups', [])
    all_projects = []

    if scan_groups:
        for group_config in scan_groups:
            group_id = group_config.get('group_id') or group_config.get('group_path')
            if not group_id:
                continue

            include_subgroups = group_config.get('include_subgroups', True)
            naming_rule = group_config.get('naming_rule', 'project_name')

            projects = gitlab_tester.scan_group(group_id, include_subgroups)
            all_projects.extend(projects)

            # 프로젝트 목록 출력
            print_project_table(projects, naming_rule)
    else:
        print_warning("\nscan_groups가 설정되지 않았습니다.")
        print_info("config.json에서 scan_groups를 설정하세요.")

    # GitHub 테스트
    verify_ssl = config.get('options', {}).get('verify_ssl', True)
    if not verify_ssl:
        print_warning("\n⚠ SSL 검증이 비활성화되어 있습니다. (보안 위험)")

    github_tester = GitHubTester(
        config['github']['token'],
        config['github'].get('organization'),
        verify_ssl=verify_ssl
    )

    if not github_tester.test_connection():
        print_error("\nGitHub 연결에 실패했습니다. 토큰을 확인하세요.")
        sys.exit(1)

    # 최종 요약
    print_header("테스트 요약")
    print_success("✓ GitLab 연결 성공")
    if all_projects:
        print_success(f"✓ 총 {len(all_projects)}개 프로젝트 발견")
    print_success("✓ GitHub 연결 성공")

    print(f"\n{Colors.GREEN}{Colors.BOLD}모든 테스트가 성공적으로 완료되었습니다!{Colors.RESET}")
    print(f"{Colors.CYAN}실제 마이그레이션을 진행하려면 migrate.py를 실행하세요.{Colors.RESET}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}사용자에 의해 중단되었습니다.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}예상치 못한 오류: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
