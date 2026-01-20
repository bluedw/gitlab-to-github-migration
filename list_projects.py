#!/usr/bin/env python3
"""
GitLab 그룹 프로젝트 목록 조회 도구
그룹 하위의 모든 프로젝트를 조회하여 터미널에 출력하고 로그 파일로 저장합니다.
"""

import json
import sys
import io
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List
from datetime import datetime
import os


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
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


class GitLabProjectLister:
    """GitLab 프로젝트 목록 조회 클래스"""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.api_url = f"{self.url}/api/v4"
        self.log_lines = []  # 로그 파일에 저장할 내용

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

                # 빈 응답 확인
                if not response_text or not response_text.strip():
                    raise Exception(f"빈 응답을 받았습니다. URL: {url}")

                # JSON 파싱
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as je:
                    preview = response_text[:200] if len(response_text) > 200 else response_text
                    raise Exception(
                        f"JSON 파싱 실패. API 응답이 JSON이 아닙니다.\n"
                        f"URL: {url}\n"
                        f"응답: {preview}"
                    )

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"연결 실패. URL: {url}, 원인: {e.reason}")

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

    def _print_and_log(self, message: str, color: str = Colors.RESET, log_only: bool = False):
        """터미널 출력 및 로그에 추가"""
        # 로그에는 색상 코드 없이 저장
        clean_message = message
        self.log_lines.append(clean_message)

        # 터미널에는 색상과 함께 출력
        if not log_only:
            print(f"{color}{message}{Colors.RESET}")

    def _format_date(self, date_str: str) -> str:
        """날짜 포맷 변환"""
        if not date_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return date_str

    def get_group_info(self, group_id: str) -> Dict:
        """그룹 정보 조회"""
        encoded_id = urllib.parse.quote(str(group_id), safe='')
        return self._make_request(f"groups/{encoded_id}")

    def list_projects(self, group_id: str, include_subgroups: bool = True,
                     show_details: bool = True) -> List[Dict]:
        """
        그룹의 모든 프로젝트 조회 및 출력

        Args:
            group_id: 그룹 ID 또는 경로
            include_subgroups: 서브그룹 포함 여부
            show_details: 상세 정보 표시 여부

        Returns:
            프로젝트 목록
        """
        # 헤더 출력
        self._print_and_log("=" * 100, Colors.CYAN)
        self._print_and_log("GitLab 그룹 프로젝트 목록 조회", Colors.CYAN + Colors.BOLD)
        self._print_and_log(f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.CYAN)
        self._print_and_log("=" * 100, Colors.CYAN)
        self._print_and_log("")

        # 그룹 정보 조회
        try:
            self._print_and_log(f"그룹 정보를 조회하는 중: {group_id}", Colors.BLUE)
            group = self.get_group_info(group_id)

            self._print_and_log("")
            self._print_and_log("[ 그룹 정보 ]", Colors.GREEN + Colors.BOLD)
            self._print_and_log(f"  이름: {group['name']}", Colors.WHITE)
            self._print_and_log(f"  경로: {group['full_path']}", Colors.WHITE)
            self._print_and_log(f"  ID: {group['id']}", Colors.WHITE)
            self._print_and_log(f"  설명: {group.get('description', 'N/A')}", Colors.WHITE)
            self._print_and_log(f"  가시성: {group.get('visibility', 'N/A')}", Colors.WHITE)
            self._print_and_log(f"  웹 URL: {group.get('web_url', 'N/A')}", Colors.WHITE)
            self._print_and_log("")

        except Exception as e:
            self._print_and_log(f"✗ 그룹 정보 조회 실패: {e}", Colors.RED)
            return []

        # 프로젝트 목록 조회
        try:
            self._print_and_log(f"프로젝트 목록을 조회하는 중...", Colors.BLUE)
            self._print_and_log(f"서브그룹 포함: {'예' if include_subgroups else '아니오'}", Colors.BLUE)
            self._print_and_log("")

            params = {
                'include_subgroups': 'true' if include_subgroups else 'false',
                'archived': 'false',
                'order_by': 'path',
                'sort': 'asc'
            }

            encoded_id = urllib.parse.quote(str(group_id), safe='')
            projects = self._make_request_list(f"groups/{encoded_id}/projects", params)

            self._print_and_log("=" * 100, Colors.GREEN)
            self._print_and_log(f"총 {len(projects)}개의 프로젝트 발견", Colors.GREEN + Colors.BOLD)
            self._print_and_log("=" * 100, Colors.GREEN)
            self._print_and_log("")

            # 프로젝트 목록 출력
            if show_details:
                self._print_detailed_list(projects)
            else:
                self._print_simple_list(projects)

            return projects

        except Exception as e:
            self._print_and_log(f"✗ 프로젝트 조회 실패: {e}", Colors.RED)
            return []

    def _print_simple_list(self, projects: List[Dict]):
        """간단한 프로젝트 목록 출력"""
        self._print_and_log("[ 프로젝트 목록 (간단 보기) ]", Colors.CYAN + Colors.BOLD)
        self._print_and_log("")

        # 테이블 헤더
        header = f"{'No.':<6} {'프로젝트 경로':<60} {'가시성':<10}"
        self._print_and_log(header, Colors.BOLD)
        self._print_and_log("-" * 100, Colors.DIM)

        # 프로젝트 목록
        for idx, project in enumerate(projects, 1):
            path = project['path_with_namespace']
            visibility = project.get('visibility', 'N/A')

            # 가시성에 따라 색상 변경
            if visibility == 'private':
                vis_color = Colors.RED
            elif visibility == 'internal':
                vis_color = Colors.YELLOW
            else:
                vis_color = Colors.GREEN

            line = f"{idx:<6} {path:<60} {visibility:<10}"
            color = Colors.WHITE if idx % 2 == 0 else Colors.BLUE

            self._print_and_log(line, color)

        self._print_and_log("")

    def _print_detailed_list(self, projects: List[Dict]):
        """상세한 프로젝트 목록 출력"""
        self._print_and_log("[ 프로젝트 목록 (상세 보기) ]", Colors.CYAN + Colors.BOLD)
        self._print_and_log("")

        for idx, project in enumerate(projects, 1):
            # 프로젝트 번호 헤더
            self._print_and_log(f"━━━ [{idx}/{len(projects)}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", Colors.CYAN)

            # 기본 정보
            self._print_and_log(f"프로젝트: {project['name']}", Colors.BOLD + Colors.WHITE)
            self._print_and_log(f"경로: {project['path_with_namespace']}", Colors.WHITE)
            self._print_and_log(f"ID: {project['id']}", Colors.DIM)

            # 설명
            description = project.get('description', '')
            if description:
                self._print_and_log(f"설명: {description}", Colors.WHITE)
            else:
                self._print_and_log(f"설명: (없음)", Colors.DIM)

            # URL 정보
            self._print_and_log(f"웹 URL: {project.get('web_url', 'N/A')}", Colors.BLUE)
            self._print_and_log(f"HTTP URL: {project.get('http_url_to_repo', 'N/A')}", Colors.BLUE)
            self._print_and_log(f"SSH URL: {project.get('ssh_url_to_repo', 'N/A')}", Colors.BLUE)

            # 상태 정보
            visibility = project.get('visibility', 'N/A')
            if visibility == 'private':
                vis_text = f"가시성: 🔒 {visibility} (비공개)"
                vis_color = Colors.RED
            elif visibility == 'internal':
                vis_text = f"가시성: 🔓 {visibility} (내부)"
                vis_color = Colors.YELLOW
            else:
                vis_text = f"가시성: 🌍 {visibility} (공개)"
                vis_color = Colors.GREEN

            self._print_and_log(vis_text, vis_color)
            self._print_and_log(f"아카이브: {'예' if project.get('archived', False) else '아니오'}", Colors.WHITE)

            # 통계
            self._print_and_log(f"Star: ⭐ {project.get('star_count', 0)} | Fork: 🍴 {project.get('forks_count', 0)}", Colors.YELLOW)

            # 날짜 정보
            created_at = self._format_date(project.get('created_at', ''))
            last_activity = self._format_date(project.get('last_activity_at', ''))

            self._print_and_log(f"생성일: {created_at}", Colors.DIM)
            self._print_and_log(f"최종 활동: {last_activity}", Colors.DIM)

            # 기본 브랜치
            default_branch = project.get('default_branch', 'N/A')
            self._print_and_log(f"기본 브랜치: {default_branch}", Colors.WHITE)

            self._print_and_log("")

        # 요약
        self._print_and_log("=" * 100, Colors.GREEN)
        self._print_and_log(f"총 {len(projects)}개 프로젝트", Colors.GREEN + Colors.BOLD)

        # 가시성별 통계
        visibility_count = {}
        for project in projects:
            vis = project.get('visibility', 'unknown')
            visibility_count[vis] = visibility_count.get(vis, 0) + 1

        self._print_and_log("", Colors.WHITE)
        self._print_and_log("[ 가시성별 통계 ]", Colors.CYAN)
        for vis, count in sorted(visibility_count.items()):
            self._print_and_log(f"  {vis}: {count}개", Colors.WHITE)

        self._print_and_log("=" * 100, Colors.GREEN)
        self._print_and_log("")

    def save_to_file(self, filename: str = None):
        """로그를 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"gitlab_projects_{timestamp}.log"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.log_lines))

            print(f"{Colors.GREEN}✓ 로그 파일 저장: {filename}{Colors.RESET}")
            return filename

        except Exception as e:
            print(f"{Colors.RED}✗ 로그 파일 저장 실패: {e}{Colors.RESET}")
            return None


def load_config(config_path: str = "config.json") -> Dict:
    """설정 파일 로드"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{Colors.RED}✗ 설정 파일을 찾을 수 없습니다: {config_path}{Colors.RESET}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}✗ 설정 파일 파싱 오류: {e}{Colors.RESET}")
        sys.exit(1)


def print_usage():
    """사용법 출력"""
    print(f"""
{Colors.CYAN}{Colors.BOLD}사용법:{Colors.RESET}
  python list_projects.py [OPTIONS]

{Colors.CYAN}{Colors.BOLD}옵션:{Colors.RESET}
  -c, --config FILE      설정 파일 경로 (기본: config.json)
  -g, --group GROUP      그룹 ID 또는 경로 (config.json의 scan_groups 대신 사용)
  -s, --simple           간단한 목록만 표시
  -n, --no-subgroups     서브그룹 제외
  -o, --output FILE      로그 파일 이름 지정
  -h, --help             도움말 표시

{Colors.CYAN}{Colors.BOLD}예제:{Colors.RESET}
  python list_projects.py
  python list_projects.py -g icis/rater
  python list_projects.py -g icis/rater -s
  python list_projects.py -g icis/rater -o my_projects.log
  python list_projects.py -c my-config.json -n
""")


def main():
    """메인 함수"""
    import sys

    # 인자 파싱 (간단한 수동 파싱)
    config_path = "config.json"
    group_id = None
    show_details = True
    include_subgroups = True
    output_file = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg in ['-h', '--help']:
            print_usage()
            sys.exit(0)
        elif arg in ['-c', '--config']:
            if i + 1 < len(sys.argv):
                config_path = sys.argv[i + 1]
                i += 2
            else:
                print(f"{Colors.RED}✗ -c/--config 옵션에 파일 경로가 필요합니다{Colors.RESET}")
                sys.exit(1)
        elif arg in ['-g', '--group']:
            if i + 1 < len(sys.argv):
                group_id = sys.argv[i + 1]
                i += 2
            else:
                print(f"{Colors.RED}✗ -g/--group 옵션에 그룹 ID가 필요합니다{Colors.RESET}")
                sys.exit(1)
        elif arg in ['-s', '--simple']:
            show_details = False
            i += 1
        elif arg in ['-n', '--no-subgroups']:
            include_subgroups = False
            i += 1
        elif arg in ['-o', '--output']:
            if i + 1 < len(sys.argv):
                output_file = sys.argv[i + 1]
                i += 2
            else:
                print(f"{Colors.RED}✗ -o/--output 옵션에 파일 이름이 필요합니다{Colors.RESET}")
                sys.exit(1)
        else:
            print(f"{Colors.RED}✗ 알 수 없는 옵션: {arg}{Colors.RESET}")
            print_usage()
            sys.exit(1)

    # 설정 파일 로드
    config = load_config(config_path)

    # 그룹 ID 결정
    if not group_id:
        # config.json의 scan_groups에서 첫 번째 그룹 사용
        scan_groups = config.get('scan_groups', [])
        if scan_groups:
            group_config = scan_groups[0]
            group_id = group_config.get('group_id') or group_config.get('group_path')
        else:
            print(f"{Colors.RED}✗ 그룹 ID를 지정하거나 config.json에 scan_groups를 설정하세요{Colors.RESET}")
            print_usage()
            sys.exit(1)

    # 프로젝트 목록 조회
    try:
        lister = GitLabProjectLister(
            config['gitlab']['url'],
            config['gitlab']['token']
        )

        projects = lister.list_projects(group_id, include_subgroups, show_details)

        # 로그 파일 저장
        saved_file = lister.save_to_file(output_file)

        if projects:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 완료!{Colors.RESET}")
            print(f"{Colors.CYAN}총 {len(projects)}개의 프로젝트를 조회했습니다.{Colors.RESET}")
            if saved_file:
                print(f"{Colors.CYAN}로그 파일: {saved_file}{Colors.RESET}\n")

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}사용자에 의해 중단되었습니다.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}✗ 오류: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
