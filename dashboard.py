#!/usr/bin/env python3
"""
GitLab to GitHub Migration Dashboard
이관 상태를 확인하고 HTML 대시보드를 생성하는 도구 (표준 라이브러리만 사용)
"""

import json
import os
import sys
import io
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Optional, Tuple
import datetime
import html


# Windows 콘솔 UTF-8 인코딩 설정 (UnicodeEncodeError 방지)
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # 이미 재설정된 경우 무시


class GitLabAPI:
    """GitLab API 클라이언트"""

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
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
            except:
                error_body = "Unable to read error response"
            raise Exception(f"GitLab API 오류 ({e.code}): {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"GitLab 연결 실패: {e.reason}")

    def _make_request_list(self, endpoint: str, params: Dict = None) -> List[Dict]:
        """API 요청 수행 (페이지네이션 처리)"""
        all_results = []
        page = 1
        per_page = 100

        while True:
            query_params = params.copy() if params else {}
            query_params['page'] = page
            query_params['per_page'] = per_page
            query_string = urllib.parse.urlencode(query_params)
            url = f"{self.api_url}/{endpoint.lstrip('/')}?{query_string}"

            headers = {'PRIVATE-TOKEN': self.token, 'Content-Type': 'application/json'}
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
                try:
                    error_body = e.read().decode('utf-8')
                except:
                    error_body = "Unable to read error response"
                raise Exception(f"GitLab API 오류 ({e.code}): {error_body}")

        return all_results

    def get_project(self, project_id: str) -> Dict:
        """프로젝트 정보 가져오기"""
        encoded_id = urllib.parse.quote(str(project_id), safe='')
        return self._make_request(f"projects/{encoded_id}")

    def get_branches(self, project_id: str) -> List[Dict]:
        """프로젝트의 모든 브랜치 가져오기"""
        encoded_id = urllib.parse.quote(str(project_id), safe='')
        return self._make_request_list(f"projects/{encoded_id}/repository/branches")

    def get_group_projects(self, group_id: str, include_subgroups: bool = True) -> List[Dict]:
        """그룹 내 모든 프로젝트 가져오기"""
        encoded_id = urllib.parse.quote(str(group_id), safe='')
        params = {
            'include_subgroups': 'true' if include_subgroups else 'false',
            'archived': 'false'
        }
        return self._make_request_list(f"groups/{encoded_id}/projects", params)


class GitHubAPI:
    """GitHub API 클라이언트"""

    def __init__(self, token: str):
        self.token = token
        self.api_url = "https://api.github.com"

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
            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # 저장소 없음
            try:
                error_body = e.read().decode('utf-8')
            except:
                error_body = "Unable to read error response"
            raise Exception(f"GitHub API 오류 ({e.code}): {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"GitHub 연결 실패: {e.reason}")

    def _make_request_list(self, endpoint: str) -> List[Dict]:
        """API 요청 수행 (페이지네이션 처리)"""
        all_results = []
        page = 1
        per_page = 100

        while True:
            url = f"{self.api_url}/{endpoint.lstrip('/')}?page={page}&per_page={per_page}"
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
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
                if e.code == 404:
                    return []
                raise

        return all_results

    def get_user(self) -> Dict:
        """인증된 사용자 정보 가져오기"""
        return self._make_request('user')

    def get_repo(self, owner: str, name: str) -> Optional[Dict]:
        """저장소 정보 가져오기 (없으면 None 반환)"""
        return self._make_request(f"repos/{owner}/{name}")

    def get_branches(self, owner: str, repo: str) -> List[Dict]:
        """저장소의 모든 브랜치 가져오기"""
        return self._make_request_list(f"repos/{owner}/{repo}/branches")


class MigrationDashboard:
    """마이그레이션 대시보드 생성 클래스"""

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.gitlab = GitLabAPI(
            self.config['gitlab']['url'],
            self.config['gitlab']['token']
        )
        self.github = GitHubAPI(self.config['github']['token'])
        self.github_user = self.github.get_user()
        self.github_owner = self.config['github'].get('organization') or self.github_user['login']

    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_all_repositories(self) -> List[Dict]:
        """config에서 모든 이관 대상 저장소 목록 가져오기"""
        repositories = self.config.get('repositories', []).copy()
        scan_groups = self.config.get('scan_groups', [])

        if scan_groups:
            print("그룹 스캔 중...")
            for group_config in scan_groups:
                group_id = group_config.get('group_id') or group_config.get('group_path')
                if not group_id:
                    continue

                try:
                    include_subgroups = group_config.get('include_subgroups', True)
                    projects = self.gitlab.get_group_projects(group_id, include_subgroups)
                    print(f"  그룹 '{group_id}': {len(projects)}개 프로젝트 발견")

                    naming_rule = group_config.get('naming_rule', 'project_name')
                    default_private = group_config.get('default_private', True)

                    for project in projects:
                        if naming_rule == 'project_name':
                            github_name = project['name']
                        elif naming_rule == 'path_with_namespace':
                            github_name = project['path_with_namespace'].replace('/', '-')
                        else:
                            github_name = project['name']

                        repo_config = {
                            'gitlab_project_id': project['id'],
                            'gitlab_project_path': project['path_with_namespace'],
                            'github_repo_name': github_name,
                            'description': project.get('description', ''),
                            'private': default_private
                        }
                        repositories.append(repo_config)
                except Exception as e:
                    print(f"  그룹 스캔 실패: {e}")

        return repositories

    def check_migration_status(self) -> Tuple[List[Dict], Dict]:
        """
        이관 상태 확인

        Returns:
            (상세 리스트, 통계 정보)
        """
        repositories = self._get_all_repositories()
        print(f"\n총 {len(repositories)}개 저장소 상태 확인 중...\n")

        details = []
        total_count = len(repositories)
        completed_count = 0
        not_created_count = 0
        sync_needed_count = 0

        for idx, repo_config in enumerate(repositories, 1):
            gitlab_project_id = repo_config.get('gitlab_project_id')
            gitlab_project_path = repo_config.get('gitlab_project_path')
            github_repo_name = repo_config['github_repo_name']

            print(f"[{idx}/{total_count}] {github_repo_name} 확인 중...")

            try:
                # GitLab 프로젝트 정보 가져오기
                project_identifier = gitlab_project_id or gitlab_project_path
                gl_project = self.gitlab.get_project(project_identifier)
                gl_branches = self.gitlab.get_branches(project_identifier)

                # GitHub 저장소 확인
                gh_repo = self.github.get_repo(self.github_owner, github_repo_name)

                if gh_repo is None:
                    # GitHub 저장소가 없음
                    not_created_count += 1
                    for branch in gl_branches:
                        details.append({
                            'gitlab_project': gl_project['path_with_namespace'],
                            'github_repository': f"{self.github_owner}/{github_repo_name}",
                            'branch': branch['name'],
                            'gitlab_commit': branch['commit']['short_id'],
                            'github_commit': '-',
                            'status': 'not created'
                        })
                else:
                    # GitHub 저장소가 존재 - 브랜치별로 비교
                    gh_branches = self.github.get_branches(self.github_owner, github_repo_name)
                    gh_branch_dict = {b['name']: b for b in gh_branches}

                    repo_status = 'completed'  # 초기값

                    for gl_branch in gl_branches:
                        branch_name = gl_branch['name']
                        gl_commit = gl_branch['commit']['short_id']

                        gh_branch = gh_branch_dict.get(branch_name)
                        if gh_branch:
                            gh_commit = gh_branch['commit']['sha'][:7]
                            # 커밋 비교 (short_id 기준)
                            if gl_commit != gh_commit:
                                status = 'sync needed'
                                repo_status = 'sync needed'
                            else:
                                status = 'completed'
                        else:
                            # GitHub에 브랜치가 없음
                            gh_commit = '-'
                            status = 'sync needed'
                            repo_status = 'sync needed'

                        details.append({
                            'gitlab_project': gl_project['path_with_namespace'],
                            'github_repository': f"{self.github_owner}/{github_repo_name}",
                            'branch': branch_name,
                            'gitlab_commit': gl_commit,
                            'github_commit': gh_commit,
                            'status': status
                        })

                    if repo_status == 'completed':
                        completed_count += 1
                    else:
                        sync_needed_count += 1

            except Exception as e:
                print(f"  오류: {e}")
                details.append({
                    'gitlab_project': gitlab_project_path or str(gitlab_project_id),
                    'github_repository': f"{self.github_owner}/{github_repo_name}",
                    'branch': '-',
                    'gitlab_commit': '-',
                    'github_commit': '-',
                    'status': 'error'
                })

        statistics = {
            'total': total_count,
            'completed': completed_count,
            'not_created': not_created_count,
            'sync_needed': sync_needed_count
        }

        return details, statistics

    def generate_html_dashboard(self, details: List[Dict], statistics: Dict, output_path: str = "dashboard.html"):
        """HTML 대시보드 생성"""
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitLab to GitHub Migration Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}

        .header h1 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }}

        .header .subtitle {{
            color: #666;
            font-size: 14px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}

        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 4px solid;
        }}

        .stat-card.total {{ border-left-color: #667eea; }}
        .stat-card.completed {{ border-left-color: #48bb78; }}
        .stat-card.not-created {{ border-left-color: #ed8936; }}
        .stat-card.sync-needed {{ border-left-color: #f6ad55; }}

        .stat-card .label {{
            color: #666;
            font-size: 14px;
            margin-bottom: 8px;
        }}

        .stat-card .value {{
            font-size: 36px;
            font-weight: bold;
        }}

        .stat-card.total .value {{ color: #667eea; }}
        .stat-card.completed .value {{ color: #48bb78; }}
        .stat-card.not-created .value {{ color: #ed8936; }}
        .stat-card.sync-needed .value {{ color: #f6ad55; }}

        .table-container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
        }}

        tr:hover {{
            background: #f7fafc;
        }}

        .status-badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
        }}

        .status-completed {{
            background: #c6f6d5;
            color: #22543d;
        }}

        .status-not-created {{
            background: #fed7d7;
            color: #742a2a;
        }}

        .status-sync-needed {{
            background: #feebc8;
            color: #7c2d12;
        }}

        .status-error {{
            background: #fed7d7;
            color: #742a2a;
        }}

        .commit-hash {{
            font-family: 'Courier New', monospace;
            background: #edf2f7;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }}

        .project-path {{
            color: #4a5568;
            font-weight: 500;
        }}

        .repo-link {{
            color: #667eea;
            text-decoration: none;
        }}

        .repo-link:hover {{
            text-decoration: underline;
        }}

        .filter-controls {{
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
        }}

        .filter-btn.active {{
            background: #667eea;
            color: white;
        }}

        .filter-btn:not(.active) {{
            background: #e2e8f0;
            color: #4a5568;
        }}

        .filter-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}

            table {{
                font-size: 12px;
            }}

            th, td {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GitLab to GitHub Migration Dashboard</h1>
            <div class="subtitle">마지막 업데이트: {html.escape(now)}</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card total">
                <div class="label">전체 대상</div>
                <div class="value">{statistics['total']}</div>
            </div>
            <div class="stat-card completed">
                <div class="label">이관 완료</div>
                <div class="value">{statistics['completed']}</div>
            </div>
            <div class="stat-card not-created">
                <div class="label">이관 대상 미완료</div>
                <div class="value">{statistics['not_created']}</div>
            </div>
            <div class="stat-card sync-needed">
                <div class="label">동기화 필요</div>
                <div class="value">{statistics['sync_needed']}</div>
            </div>
        </div>

        <div class="table-container">
            <div class="filter-controls">
                <button class="filter-btn active" onclick="filterTable('all')">전체 보기</button>
                <button class="filter-btn" onclick="filterTable('completed')">이관 완료</button>
                <button class="filter-btn" onclick="filterTable('not created')">미완료</button>
                <button class="filter-btn" onclick="filterTable('sync needed')">동기화 필요</button>
            </div>

            <table id="migrationTable">
                <thead>
                    <tr>
                        <th>GitLab Project</th>
                        <th>GitHub Repository</th>
                        <th>Branch</th>
                        <th>GitLab Commit</th>
                        <th>GitHub Commit</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""

        # 테이블 행 추가
        for item in details:
            gitlab_project = html.escape(item['gitlab_project'])
            github_repo = html.escape(item['github_repository'])
            branch = html.escape(item['branch'])
            gitlab_commit = html.escape(item['gitlab_commit'])
            github_commit = html.escape(item['github_commit'])
            status = item['status']

            status_class = status.replace(' ', '-')

            html_content += f"""                    <tr data-status="{html.escape(status)}">
                        <td class="project-path">{gitlab_project}</td>
                        <td><a href="https://github.com/{github_repo}" class="repo-link" target="_blank">{github_repo}</a></td>
                        <td>{branch}</td>
                        <td><span class="commit-hash">{gitlab_commit}</span></td>
                        <td><span class="commit-hash">{github_commit}</span></td>
                        <td><span class="status-badge status-{status_class}">{html.escape(status)}</span></td>
                    </tr>
"""

        html_content += """                </tbody>
            </table>
        </div>
    </div>

    <script>
        function filterTable(status) {
            const table = document.getElementById('migrationTable');
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            const buttons = document.querySelectorAll('.filter-btn');

            // 버튼 활성화 상태 업데이트
            buttons.forEach(btn => {
                btn.classList.remove('active');
                if ((status === 'all' && btn.textContent === '전체 보기') ||
                    (status === 'completed' && btn.textContent === '이관 완료') ||
                    (status === 'not created' && btn.textContent === '미완료') ||
                    (status === 'sync needed' && btn.textContent === '동기화 필요')) {
                    btn.classList.add('active');
                }
            });

            // 행 필터링
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const rowStatus = row.getAttribute('data-status');

                if (status === 'all' || rowStatus === status) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            }
        }
    </script>
</body>
</html>
"""

        # HTML 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\n대시보드 생성 완료: {output_path}")


def main():
    """메인 함수"""
    print("""
╔══════════════════════════════════════════════════════════╗
║     GitLab to GitHub Migration Dashboard                ║
║     이관 상태 확인 및 대시보드 생성                      ║
╚══════════════════════════════════════════════════════════╝
""")

    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'dashboard.html'

    try:
        dashboard = MigrationDashboard(config_path)
        details, statistics = dashboard.check_migration_status()

        print("\n=== 통계 요약 ===")
        print(f"전체 대상: {statistics['total']}")
        print(f"이관 완료: {statistics['completed']}")
        print(f"이관 대상 미완료: {statistics['not_created']}")
        print(f"동기화 필요: {statistics['sync_needed']}")

        dashboard.generate_html_dashboard(details, statistics, output_path)

    except FileNotFoundError as e:
        print(f"\n오류: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
