#!/usr/bin/env python3
"""
GitLab to GitHub Migration Tool
여러 GitLab 저장소를 GitHub로 일괄 이관하는 도구 (표준 라이브러리만 사용)
"""

import json
import os
import sys
import io
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Optional
import time
import stat
import datetime


# Windows 콘솔 UTF-8 인코딩 설정 (UnicodeEncodeError 방지)
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # 이미 재설정된 경우 무시


class MigrationLogger:
    """마이그레이션 로그를 관리하는 클래스"""

    # ANSI 색상 코드
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

    @staticmethod
    def info(message: str):
        print(f"{MigrationLogger.BLUE}ℹ {message}{MigrationLogger.RESET}")

    @staticmethod
    def success(message: str):
        print(f"{MigrationLogger.GREEN}✓ {message}{MigrationLogger.RESET}")

    @staticmethod
    def warning(message: str):
        print(f"{MigrationLogger.YELLOW}⚠ {message}{MigrationLogger.RESET}")

    @staticmethod
    def error(message: str):
        print(f"{MigrationLogger.RED}✗ {message}{MigrationLogger.RESET}")


class GitLabAPI:
    """GitLab API 클라이언트"""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.api_url = f"{self.url}/api/v4"

    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """API 요청 수행"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        headers = {
            'PRIVATE-TOKEN': self.token,
            'Content-Type': 'application/json'
        }

        req_data = json.dumps(data).encode('utf-8') if data else None
        request = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request) as response:
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
                        f"GitLab API 응답이 JSON이 아닙니다.\n"
                        f"URL: {url}\n"
                        f"응답: {preview}"
                    )

        except urllib.error.HTTPError as e:
            error_code = e.code
            try:
                error_body = e.read().decode('utf-8')
            except:
                error_body = "Unable to read error response"
            raise Exception(f"GitLab API 오류 ({error_code}): {error_body}") from None
        except urllib.error.URLError as e:
            error_reason = str(e.reason)
            raise Exception(f"GitLab 연결 실패. URL: {url}, 원인: {error_reason}") from None

    def _make_request_list(self, endpoint: str, params: Dict = None) -> List[Dict]:
        """API 요청 수행 (페이지네이션 처리하여 모든 결과 반환)"""
        all_results = []
        page = 1
        per_page = 100

        while True:
            # 쿼리 파라미터 구성
            query_params = params.copy() if params else {}
            query_params['page'] = page
            query_params['per_page'] = per_page

            # URL에 쿼리 파라미터 추가
            query_string = urllib.parse.urlencode(query_params)
            url = f"{self.api_url}/{endpoint.lstrip('/')}?{query_string}"

            headers = {
                'PRIVATE-TOKEN': self.token,
                'Content-Type': 'application/json'
            }

            request = urllib.request.Request(url, headers=headers)

            try:
                with urllib.request.urlopen(request) as response:
                    results = json.loads(response.read().decode('utf-8'))

                    if not results:  # 더 이상 결과가 없으면 종료
                        break

                    all_results.extend(results)

                    # 결과가 per_page보다 적으면 마지막 페이지
                    if len(results) < per_page:
                        break

                    page += 1

            except urllib.error.HTTPError as e:
                error_code = e.code
                try:
                    error_body = e.read().decode('utf-8')
                except:
                    error_body = "Unable to read error response"
                raise Exception(f"GitLab API 오류 ({error_code}): {error_body}") from None

        return all_results

    def get_project(self, project_id: str) -> Dict:
        """프로젝트 정보 가져오기"""
        # project_id는 숫자 ID 또는 'namespace/project' 형식
        encoded_id = urllib.parse.quote(str(project_id), safe='')
        return self._make_request(f"projects/{encoded_id}")

    def get_group_projects(self, group_id: str, include_subgroups: bool = True) -> List[Dict]:
        """
        그룹 내 모든 프로젝트 가져오기

        Args:
            group_id: 그룹 ID 또는 경로
            include_subgroups: 서브그룹 포함 여부

        Returns:
            프로젝트 목록
        """
        encoded_id = urllib.parse.quote(str(group_id), safe='')
        params = {
            'include_subgroups': 'true' if include_subgroups else 'false',
            'archived': 'false'  # 아카이브된 프로젝트 제외
        }
        return self._make_request_list(f"groups/{encoded_id}/projects", params)

    def get_branches(self, project_id: str) -> List[Dict]:
        """
        프로젝트의 모든 브랜치 가져오기

        Args:
            project_id: 프로젝트 ID 또는 경로

        Returns:
            브랜치 목록
        """
        encoded_id = urllib.parse.quote(str(project_id), safe='')
        return self._make_request_list(f"projects/{encoded_id}/repository/branches")

    def get_tags(self, project_id: str) -> List[Dict]:
        """
        프로젝트의 모든 태그 가져오기

        Args:
            project_id: 프로젝트 ID 또는 경로

        Returns:
            태그 목록
        """
        encoded_id = urllib.parse.quote(str(project_id), safe='')
        return self._make_request_list(f"projects/{encoded_id}/repository/tags")

    def get_commits(self, project_id: str, ref_name: str = None, per_page: int = 20) -> List[Dict]:
        """
        프로젝트의 커밋 목록 가져오기

        Args:
            project_id: 프로젝트 ID 또는 경로
            ref_name: 브랜치/태그 이름 (None이면 기본 브랜치)
            per_page: 페이지당 커밋 수

        Returns:
            커밋 목록
        """
        encoded_id = urllib.parse.quote(str(project_id), safe='')
        params = {}
        if ref_name:
            params['ref_name'] = ref_name
        params['per_page'] = per_page

        # 커밋은 페이지네이션을 제한적으로 사용 (너무 많은 커밋 방지)
        query_string = urllib.parse.urlencode(params)
        url = f"{self.api_url}/projects/{encoded_id}/repository/commits?{query_string}"

        headers = {
            'PRIVATE-TOKEN': self.token,
            'Content-Type': 'application/json'
        }

        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_code = e.code
            try:
                error_body = e.read().decode('utf-8')
            except:
                error_body = "Unable to read error response"
            raise Exception(f"GitLab API 오류 ({error_code}): {error_body}") from None
        except urllib.error.URLError as e:
            error_reason = str(e.reason)
            raise Exception(f"GitLab 연결 실패: {error_reason}") from None


class GitHubAPI:
    """GitHub API 클라이언트"""

    def __init__(self, token: str, verify_ssl: bool = True):
        self.token = token
        self.api_url = "https://api.github.com"
        self.verify_ssl = verify_ssl
        self.rate_limit_info = {
            'limit': None,
            'remaining': None,
            'reset': None
        }
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
            # SSL 검증 설정
            import ssl
            if not self.verify_ssl:
                context = ssl._create_unverified_context()
                with urllib.request.urlopen(request, context=context) as response:
                    response_data = response.read().decode('utf-8')
                    # Rate Limit 정보 파싱
                    self._parse_rate_limit_headers(response.headers)
                    # 적응형 딜레이
                    self._adaptive_delay()
                    return json.loads(response_data) if response_data else {}
            else:
                with urllib.request.urlopen(request) as response:
                    response_data = response.read().decode('utf-8')
                    # Rate Limit 정보 파싱
                    self._parse_rate_limit_headers(response.headers)
                    # 적응형 딜레이
                    self._adaptive_delay()
                    return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            # HTTPError 속성을 먼저 변수에 저장 (객체 참조 방지)
            error_code = e.code
            error_headers = dict(e.headers) if hasattr(e, 'headers') else {}

            # 에러 본문을 안전하게 읽기
            try:
                error_body = e.read().decode('utf-8')
            except:
                error_body = "Unable to read error response"

            # 429 (Too Many Requests) 또는 403 (Secondary rate limit) 처리
            if error_code in [429, 403] and retry_count < max_retries:
                # Retry-After 헤더 확인
                retry_after = error_headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    # Exponential backoff
                    wait_time = base_delay * (2 ** retry_count)

                # Secondary rate limit 메시지 확인
                if 'secondary rate limit' in error_body.lower() or error_code == 403:
                    wait_time = max(wait_time, 60)  # 최소 60초 대기

                print(f"\n⚠ Rate limit 도달. {wait_time}초 대기 후 재시도... (시도 {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)

                # 재시도
                return self._make_request(endpoint, method, data, retry_count + 1)

            raise Exception(f"GitHub API 오류 ({error_code}): {error_body}") from None
        except urllib.error.URLError as e:
            error_reason = str(e.reason)
            raise Exception(f"GitHub 연결 실패: {error_reason}") from None

    def _get_authenticated_user(self) -> Dict:
        """인증된 사용자 정보 가져오기"""
        return self._make_request('user')

    def _parse_rate_limit_headers(self, headers):
        """
        API 응답 헤더에서 Rate Limit 정보 파싱

        Args:
            headers: HTTP 응답 헤더
        """
        try:
            if 'X-RateLimit-Limit' in headers:
                self.rate_limit_info['limit'] = int(headers['X-RateLimit-Limit'])
            if 'X-RateLimit-Remaining' in headers:
                self.rate_limit_info['remaining'] = int(headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Reset' in headers:
                self.rate_limit_info['reset'] = int(headers['X-RateLimit-Reset'])
        except (ValueError, TypeError):
            # 헤더 파싱 실패 시 무시
            pass

    def _adaptive_delay(self):
        """
        Rate Limit 상태에 따른 적응형 딜레이

        - 남은 요청 수가 많으면 짧게 대기
        - 남은 요청 수가 적으면 길게 대기
        """
        remaining = self.rate_limit_info.get('remaining')
        limit = self.rate_limit_info.get('limit')
        reset_time = self.rate_limit_info.get('reset')

        if remaining is None or limit is None:
            # Rate Limit 정보가 없으면 기본 딜레이
            time.sleep(0.5)
            return

        # Rate Limit 상태 표시
        percentage = (remaining / limit * 100) if limit > 0 else 0

        if remaining < 10:
            # 남은 요청이 10개 미만이면 경고 및 긴 대기
            if reset_time:
                reset_datetime = datetime.datetime.fromtimestamp(reset_time)
                reset_str = reset_datetime.strftime('%H:%M:%S')
                MigrationLogger.warning(
                    f"⚠ Rate Limit 거의 소진! ({remaining}/{limit}, {percentage:.1f}% 남음, 리셋: {reset_str})"
                )
            else:
                MigrationLogger.warning(
                    f"⚠ Rate Limit 거의 소진! ({remaining}/{limit}, {percentage:.1f}% 남음)"
                )
            time.sleep(5)  # 5초 대기
        elif remaining < 100:
            # 남은 요청이 100개 미만이면 경고
            MigrationLogger.warning(
                f"Rate Limit 주의: {remaining}/{limit} 남음 ({percentage:.1f}%)"
            )
            time.sleep(2)  # 2초 대기
        elif remaining < 500:
            # 남은 요청이 500개 미만이면 정보 표시
            if remaining % 100 == 0:  # 100개 단위로만 표시
                MigrationLogger.info(
                    f"Rate Limit: {remaining}/{limit} 남음 ({percentage:.1f}%)"
                )
            time.sleep(1)  # 1초 대기
        else:
            # 여유가 있으면 짧게 대기
            time.sleep(0.5)

    def get_rate_limit_status(self) -> Dict:
        """
        현재 Rate Limit 상태 조회

        Returns:
            Rate Limit 정보 딕셔너리
        """
        try:
            response = self._make_request('rate_limit')
            core_limit = response['resources']['core']

            self.rate_limit_info['limit'] = core_limit['limit']
            self.rate_limit_info['remaining'] = core_limit['remaining']
            self.rate_limit_info['reset'] = core_limit['reset']

            return core_limit
        except Exception:
            return self.rate_limit_info

    def create_repo(self, name: str, description: str = '', private: bool = True, org: str = None) -> Dict:
        """저장소 생성"""
        data = {
            'name': name,
            'description': description,
            'private': private
        }

        if org:
            # Organization에 저장소 생성
            endpoint = f"orgs/{org}/repos"
        else:
            # 개인 계정에 저장소 생성
            endpoint = 'user/repos'

        return self._make_request(endpoint, method='POST', data=data)

    def get_repo(self, owner: str, name: str) -> Dict:
        """저장소 정보 가져오기"""
        return self._make_request(f"repos/{owner}/{name}")

    def get_branches(self, owner: str, repo: str) -> List[Dict]:
        """
        저장소의 모든 브랜치 가져오기

        Args:
            owner: 저장소 소유자
            repo: 저장소 이름

        Returns:
            브랜치 목록
        """
        branches = []
        page = 1
        per_page = 100

        while True:
            endpoint = f"repos/{owner}/{repo}/branches?page={page}&per_page={per_page}"
            results = self._make_request(endpoint)

            if not results:
                break

            branches.extend(results)

            if len(results) < per_page:
                break

            page += 1

        return branches

    def get_tags(self, owner: str, repo: str) -> List[Dict]:
        """
        저장소의 모든 태그 가져오기

        Args:
            owner: 저장소 소유자
            repo: 저장소 이름

        Returns:
            태그 목록
        """
        tags = []
        page = 1
        per_page = 100

        while True:
            endpoint = f"repos/{owner}/{repo}/tags?page={page}&per_page={per_page}"
            results = self._make_request(endpoint)

            if not results:
                break

            tags.extend(results)

            if len(results) < per_page:
                break

            page += 1

        return tags

    def get_commits(self, owner: str, repo: str, sha: str = None, per_page: int = 20) -> List[Dict]:
        """
        저장소의 커밋 목록 가져오기

        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            sha: 브랜치/태그/커밋 SHA (None이면 기본 브랜치)
            per_page: 페이지당 커밋 수

        Returns:
            커밋 목록
        """
        endpoint = f"repos/{owner}/{repo}/commits?per_page={per_page}"
        if sha:
            endpoint += f"&sha={sha}"

        return self._make_request(endpoint)

    def compare_commits(self, owner: str, repo: str, base: str, head: str) -> Dict:
        """
        두 커밋 간의 차이 비교

        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            base: 기준 커밋/브랜치
            head: 비교 대상 커밋/브랜치

        Returns:
            비교 결과 (ahead_by, behind_by, commits 등)
        """
        endpoint = f"repos/{owner}/{repo}/compare/{base}...{head}"
        return self._make_request(endpoint)

    def add_collaborator(self, owner: str, repo: str, username: str, permission: str = 'push') -> Dict:
        """
        저장소에 collaborator 추가

        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            username: 추가할 사용자 이름
            permission: 권한 (pull, push, admin, maintain, triage)

        Returns:
            API 응답
        """
        endpoint = f"repos/{owner}/{repo}/collaborators/{username}"
        data = {
            'permission': permission
        }
        return self._make_request(endpoint, method='PUT', data=data)

    def add_team_to_repo(self, org: str, team_slug: str, owner: str, repo: str, permission: str = 'push') -> Dict:
        """
        Organization 저장소에 팀 추가

        Args:
            org: Organization 이름
            team_slug: 팀 슬러그 (팀 이름)
            owner: 저장소 소유자
            repo: 저장소 이름
            permission: 권한 (pull, push, admin, maintain, triage)

        Returns:
            API 응답
        """
        endpoint = f"orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}"
        data = {
            'permission': permission
        }
        return self._make_request(endpoint, method='PUT', data=data)

    def update_topics(self, owner: str, repo: str, topics: List[str]) -> Dict:
        """
        저장소의 topics 업데이트

        Args:
            owner: 저장소 소유자
            repo: 저장소 이름
            topics: 설정할 topic 목록

        Returns:
            API 응답
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/topics"

        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.mercy-preview+json',
            'Content-Type': 'application/json'
        }

        data = json.dumps({'names': topics}).encode('utf-8')
        request = urllib.request.Request(url, data=data, headers=headers, method='PUT')

        try:
            import ssl
            if not self.verify_ssl:
                context = ssl._create_unverified_context()
                with urllib.request.urlopen(request, context=context) as response:
                    response_data = response.read().decode('utf-8')
                    self._parse_rate_limit_headers(response.headers)
                    self._adaptive_delay()
                    return json.loads(response_data) if response_data else {}
            else:
                with urllib.request.urlopen(request) as response:
                    response_data = response.read().decode('utf-8')
                    self._parse_rate_limit_headers(response.headers)
                    self._adaptive_delay()
                    return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            error_code = e.code
            try:
                error_body = e.read().decode('utf-8')
            except:
                error_body = "Unable to read error response"
            raise Exception(f"GitHub Topics API 오류 ({error_code}): {error_body}") from None
        except urllib.error.URLError as e:
            error_reason = str(e.reason)
            raise Exception(f"GitHub 연결 실패: {error_reason}") from None


class GitLabToGitHubMigrator:
    """GitLab에서 GitHub로 저장소를 이관하는 메인 클래스"""

    def __init__(self, config_path: str = "config.json"):
        """
        초기화

        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.logger = MigrationLogger()
        self.temp_dir = None

        # GitLab API 클라이언트 초기화
        self.gitlab = GitLabAPI(
            self.config['gitlab']['url'],
            self.config['gitlab']['token']
        )

        # GitHub API 클라이언트 초기화
        verify_ssl = self.config.get('options', {}).get('verify_ssl', True)
        if not verify_ssl:
            self.logger.warning("⚠ SSL 검증이 비활성화되어 있습니다. (보안 위험)")

        self.github = GitHubAPI(
            self.config['github']['token'],
            verify_ssl=verify_ssl
        )

        self.logger.info(f"GitLab 연결: {self.config['gitlab']['url']}")
        self.logger.info(f"GitHub 사용자: {self.github.user['login']}")

        # 초기 Rate Limit 상태 확인
        self._display_rate_limit_status()

    def _display_rate_limit_status(self):
        """현재 GitHub API Rate Limit 상태 표시"""
        try:
            limit_info = self.github.get_rate_limit_status()
            remaining = limit_info.get('remaining', 0)
            limit = limit_info.get('limit', 0)
            reset_time = limit_info.get('reset', 0)

            if limit > 0:
                percentage = (remaining / limit * 100)
                reset_datetime = datetime.datetime.fromtimestamp(reset_time)
                reset_str = reset_datetime.strftime('%Y-%m-%d %H:%M:%S')

                self.logger.info(
                    f"GitHub API Rate Limit: {remaining}/{limit} ({percentage:.1f}% 남음, 리셋: {reset_str})"
                )

                # 남은 요청이 적으면 경고
                if remaining < 100:
                    self.logger.warning(
                        f"⚠ Rate Limit이 부족합니다. 이관 중 속도가 느려질 수 있습니다."
                    )
        except Exception as e:
            self.logger.warning(f"Rate Limit 정보 조회 실패: {e}")

    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"설정 파일을 찾을 수 없습니다: {config_path}\n"
                f"config.example.json을 참고하여 config.json을 생성하세요."
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _run_git_command(self, command: List[str], cwd: str = None) -> subprocess.CompletedProcess:
        """Git 명령 실행"""
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
            self.logger.error(f"Git 명령 실패: {' '.join(command)}")
            self.logger.error(f"오류: {e.stderr}")
            raise

    def _handle_remove_readonly(self, func, path, exc_info):
        """
        읽기 전용 파일 삭제를 위한 에러 핸들러
        Git 저장소의 .git 디렉토리에는 읽기 전용 파일이 많아서
        shutil.rmtree() 실행 시 권한 오류가 발생할 수 있습니다.
        """
        # 읽기 전용 속성 제거 후 재시도
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)

    def _remove_temp_dir(self, temp_dir: str):
        """임시 디렉토리 안전하게 삭제"""
        try:
            # 읽기 전용 파일 처리를 위한 onerror 콜백 사용
            shutil.rmtree(temp_dir, onerror=self._handle_remove_readonly)
            self.logger.info("임시 디렉토리 삭제 완료")
        except Exception as e:
            self.logger.warning(f"임시 디렉토리 삭제 실패: {e}")
            self.logger.warning(f"수동 삭제 필요: {temp_dir}")

    def migrate_repository(self, repo_config: Dict) -> bool:
        """
        단일 저장소를 이관

        Args:
            repo_config: 저장소 설정

        Returns:
            성공 여부
        """
        gitlab_project_id = repo_config.get('gitlab_project_id')
        gitlab_project_path = repo_config.get('gitlab_project_path')
        github_repo_name = repo_config['github_repo_name']

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"이관 시작: {github_repo_name}")
        self.logger.info(f"{'='*60}")

        try:
            # 1. GitLab 프로젝트 가져오기
            project_identifier = gitlab_project_id or gitlab_project_path
            if not project_identifier:
                raise ValueError("gitlab_project_id 또는 gitlab_project_path가 필요합니다")

            gl_project = self.gitlab.get_project(project_identifier)
            self.logger.success(f"GitLab 프로젝트 발견: {gl_project['path_with_namespace']}")

            # Dry run 모드 확인
            if self.config['options'].get('dry_run', False):
                self.logger.warning("DRY RUN 모드: 실제 이관을 수행하지 않습니다")
                self.logger.info(f"이관 대상: {gl_project['http_url_to_repo']} → {github_repo_name}")
                return True

            # 2. GitHub 저장소 생성
            gh_repo = self._create_github_repo(repo_config, gl_project)

            # 2-1. GitHub 저장소 권한 부여 (collaborators, teams)
            self._grant_repository_permissions(gh_repo, repo_config)

            # 2-2. GitLab namespace ID를 GitHub topic으로 추가
            self._add_gitlab_namespace_topic(gh_repo, gl_project)

            # 3. 임시 디렉토리에 GitLab 저장소 클론
            self.temp_dir = tempfile.mkdtemp(prefix='gitlab_migration_')
            self.logger.info(f"임시 디렉토리 생성: {self.temp_dir}")

            clone_url = self._get_gitlab_clone_url(gl_project)
            self.logger.info(f"GitLab 저장소 클론 중...")

            # Git clone --mirror
            self._run_git_command(['git', 'clone', '--mirror', clone_url, self.temp_dir])
            self.logger.success("클론 완료")

            # 4. GitHub로 푸시
            github_url = self._get_github_push_url(gh_repo)
            self.logger.info(f"GitHub로 푸시 중...")

            # 원격 저장소 설정
            self._run_git_command(['git', 'remote', 'set-url', 'origin', github_url], cwd=self.temp_dir)

            # 모든 브랜치와 태그 푸시
            if self.config['options'].get('preserve_branches', True):
                self._run_git_command(['git', 'push', '--mirror'], cwd=self.temp_dir)
            else:
                self._run_git_command(['git', 'push', '--all'], cwd=self.temp_dir)
                if self.config['options'].get('preserve_tags', True):
                    self._run_git_command(['git', 'push', '--tags'], cwd=self.temp_dir)

            # Git push 후 rate limit 방지를 위한 대기
            self.logger.info("푸시 완료. Rate limit 방지를 위해 잠시 대기 중...")
            time.sleep(3)

            self.logger.success(f"이관 완료: {gh_repo['html_url']}")

            return True

        except Exception as e:
            self.logger.error(f"이관 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 임시 디렉토리 정리
            if self.temp_dir and os.path.exists(self.temp_dir):
                self._remove_temp_dir(self.temp_dir)

    def _create_github_repo(self, repo_config: Dict, gl_project: Dict) -> Dict:
        """GitHub 저장소 생성"""
        github_repo_name = repo_config['github_repo_name']
        description = repo_config.get('description', gl_project.get('description', ''))
        private = repo_config.get('private', True)
        org_name = self.config['github'].get('organization')

        try:
            if org_name:
                self.logger.info(f"Organization '{org_name}'에 저장소 생성 중...")
                gh_repo = self.github.create_repo(
                    name=github_repo_name,
                    description=description,
                    private=private,
                    org=org_name
                )
            else:
                self.logger.info(f"개인 계정에 저장소 생성 중...")
                gh_repo = self.github.create_repo(
                    name=github_repo_name,
                    description=description,
                    private=private
                )

            self.logger.success(f"GitHub 저장소 생성됨: {gh_repo['html_url']}")
            return gh_repo

        except Exception as e:
            if '422' in str(e):
                self.logger.warning(f"저장소가 이미 존재합니다. 기존 저장소를 사용합니다.")
                owner = org_name if org_name else self.github.user['login']
                return self.github.get_repo(owner, github_repo_name)
            raise

    def _get_gitlab_clone_url(self, gl_project: Dict) -> str:
        """GitLab 클론 URL 생성"""
        clone_method = self.config['options'].get('clone_method', 'https')

        if clone_method == 'ssh':
            return gl_project['ssh_url_to_repo']
        else:
            # HTTPS URL에 토큰 포함
            url = gl_project['http_url_to_repo']
            token = self.config['gitlab']['token']
            # https://gitlab.com/group/project.git -> https://oauth2:TOKEN@gitlab.com/group/project.git
            return url.replace('https://', f'https://oauth2:{token}@')

    def _get_github_push_url(self, gh_repo: Dict) -> str:
        """GitHub 푸시 URL 생성"""
        clone_method = self.config['options'].get('clone_method', 'https')

        if clone_method == 'ssh':
            return gh_repo['ssh_url']
        else:
            # HTTPS URL에 토큰 포함
            token = self.config['github']['token']
            clone_url = gh_repo['clone_url']
            # https://github.com/user/repo.git -> https://TOKEN@github.com/user/repo.git
            return clone_url.replace('https://', f'https://{token}@')

    def _grant_repository_permissions(self, gh_repo: Dict, repo_config: Dict):
        """
        GitHub 저장소에 collaborators와 teams 권한 부여

        Args:
            gh_repo: GitHub 저장소 정보
            repo_config: 저장소 설정 (collaborators, teams 포함)
        """
        owner = gh_repo['owner']['login']
        repo_name = gh_repo['name']
        org_name = self.config['github'].get('organization')

        # Dry run 모드면 시뮬레이션만
        is_dry_run = self.config['options'].get('dry_run', False)

        # Collaborators 추가
        collaborators = repo_config.get('collaborators', [])
        if collaborators:
            self.logger.info(f"\nCollaborators 권한 부여 중...")
            for collab in collaborators:
                username = collab.get('username')
                permission = collab.get('permission', 'push')

                if not username:
                    self.logger.warning(f"Collaborator username이 없습니다. 건너뜁니다.")
                    continue

                try:
                    if is_dry_run:
                        self.logger.info(f"  [DRY RUN] {username} ({permission}) 권한 부여 예정")
                    else:
                        self.github.add_collaborator(owner, repo_name, username, permission)
                        self.logger.success(f"  ✓ {username} ({permission}) 권한 부여 완료")
                        time.sleep(1)  # Rate limit 방지
                except Exception as e:
                    self.logger.error(f"  ✗ {username} 권한 부여 실패: {e}")

        # Teams 추가 (Organization 저장소인 경우만)
        teams = repo_config.get('teams', [])
        if teams and org_name:
            self.logger.info(f"\nTeams 권한 부여 중...")
            for team in teams:
                team_slug = team.get('team_slug')
                permission = team.get('permission', 'push')

                if not team_slug:
                    self.logger.warning(f"Team slug가 없습니다. 건너뜁니다.")
                    continue

                try:
                    if is_dry_run:
                        self.logger.info(f"  [DRY RUN] Team '{team_slug}' ({permission}) 권한 부여 예정")
                    else:
                        self.github.add_team_to_repo(org_name, team_slug, owner, repo_name, permission)
                        self.logger.success(f"  ✓ Team '{team_slug}' ({permission}) 권한 부여 완료")
                        time.sleep(1)  # Rate limit 방지
                except Exception as e:
                    self.logger.error(f"  ✗ Team '{team_slug}' 권한 부여 실패: {e}")
        elif teams and not org_name:
            self.logger.warning(f"\nTeams 설정이 있지만 Organization이 아니므로 건너뜁니다.")

    def _add_gitlab_namespace_topic(self, gh_repo: Dict, gl_project: Dict):
        """
        GitLab namespace ID를 GitHub topic으로 추가

        Args:
            gh_repo: GitHub 저장소 정보
            gl_project: GitLab 프로젝트 정보
        """
        owner = gh_repo['owner']['login']
        repo_name = gh_repo['name']

        # Dry run 모드면 시뮬레이션만
        is_dry_run = self.config['options'].get('dry_run', False)

        try:
            # GitLab namespace 정보 가져오기
            namespace = gl_project.get('namespace', {})
            namespace_id = namespace.get('id')
            namespace_name = namespace.get('name', 'unknown')

            if not namespace_id:
                self.logger.warning(f"\nGitLab namespace ID를 찾을 수 없습니다. Topic 추가를 건너뜁니다.")
                return

            # topic 이름: gitlab-ns-{namespace_id}
            topic_name = f"gitlab-ns-{namespace_id}"

            # GitHub topic 규칙: 소문자, 숫자, 하이픈만 가능, 최대 50자
            # 이미 규칙을 만족하지만 안전하게 소문자로 변환
            topic_name = topic_name.lower()

            if is_dry_run:
                self.logger.info(f"\n[DRY RUN] GitLab namespace topic 추가 예정: {topic_name} (namespace: {namespace_name})")
            else:
                self.logger.info(f"\nGitLab namespace topic 추가 중: {topic_name} (namespace: {namespace_name})")
                self.github.update_topics(owner, repo_name, [topic_name])
                self.logger.success(f"  ✓ Topic 추가 완료: {topic_name}")
                time.sleep(1)  # Rate limit 방지

        except Exception as e:
            self.logger.error(f"  ✗ Topic 추가 실패: {e}")

    def _scan_groups_and_generate_repo_list(self) -> List[Dict]:
        """
        GitLab 그룹을 스캔하여 저장소 목록 생성

        Returns:
            저장소 설정 목록
        """
        scan_groups = self.config.get('scan_groups', [])

        if not scan_groups:
            return []

        all_repos = []

        for group_config in scan_groups:
            group_id = group_config.get('group_id') or group_config.get('group_path')
            if not group_id:
                self.logger.warning("그룹 ID 또는 경로가 지정되지 않았습니다. 건너뜁니다.")
                continue

            self.logger.info(f"\n그룹 스캔 중: {group_id}")

            try:
                # 그룹 내 모든 프로젝트 가져오기
                include_subgroups = group_config.get('include_subgroups', True)
                projects = self.gitlab.get_group_projects(group_id, include_subgroups)

                self.logger.success(f"{len(projects)}개의 프로젝트 발견")

                # 저장소 설정 생성
                naming_rule = group_config.get('naming_rule', 'project_name')
                default_private = group_config.get('default_private', True)
                default_collaborators = group_config.get('default_collaborators', [])
                default_teams = group_config.get('default_teams', [])

                for project in projects:
                    # GitHub 저장소 이름 결정
                    if naming_rule == 'project_name':
                        github_name = project['name']
                    elif naming_rule == 'path_with_namespace':
                        # icis/rater/project -> rater-project
                        github_name = project['path_with_namespace'].replace('/', '-')
                    elif naming_rule == 'custom':
                        # 사용자 정의 규칙 (향후 확장 가능)
                        github_name = project['path']
                    else:
                        github_name = project['name']

                    repo_config = {
                        'gitlab_project_id': project['id'],
                        'gitlab_project_path': project['path_with_namespace'],
                        'github_repo_name': github_name,
                        'description': project.get('description', ''),
                        'private': default_private
                    }

                    # 기본 collaborators/teams 추가
                    if default_collaborators:
                        repo_config['collaborators'] = default_collaborators
                    if default_teams:
                        repo_config['teams'] = default_teams

                    all_repos.append(repo_config)
                    self.logger.info(f"  - {project['path_with_namespace']} → {github_name}")

            except Exception as e:
                self.logger.error(f"그룹 스캔 실패: {e}")
                continue

        return all_repos

    def migrate_all(self):
        """모든 저장소 이관"""
        # 그룹 스캔 여부 확인
        repositories = self.config.get('repositories', [])
        scan_groups = self.config.get('scan_groups', [])

        if scan_groups:
            self.logger.info("GitLab 그룹 스캔을 시작합니다...")
            scanned_repos = self._scan_groups_and_generate_repo_list()

            if scanned_repos:
                # 스캔된 저장소와 수동 설정 저장소 병합
                repositories.extend(scanned_repos)
                self.logger.success(f"\n그룹 스캔 완료: {len(scanned_repos)}개 프로젝트 발견")

        if not repositories:
            self.logger.warning("이관할 저장소가 없습니다.")
            return

        self.logger.info(f"\n총 {len(repositories)}개의 저장소를 이관합니다.\n")

        success_count = 0
        fail_count = 0

        for idx, repo_config in enumerate(repositories, 1):
            self.logger.info(f"\n[{idx}/{len(repositories)}] 처리 중...")

            if self.migrate_repository(repo_config):
                success_count += 1
            else:
                fail_count += 1

            # 다음 저장소 이관 전 대기 (API rate limit 고려)
            if idx < len(repositories):
                time.sleep(2)

        # 최종 결과 출력
        self.logger.info(f"\n{'='*60}")
        self.logger.info("이관 완료")
        self.logger.info(f"{'='*60}")
        self.logger.success(f"성공: {success_count}개")
        if fail_count > 0:
            self.logger.error(f"실패: {fail_count}개")


def main():
    """메인 함수"""
    CYAN = '\033[96m'
    RESET = '\033[0m'

    print(f"""
{CYAN}╔══════════════════════════════════════════════════════════╗
║     GitLab to GitHub Migration Tool                      ║
║     여러 저장소를 GitLab에서 GitHub로 이관               ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")

    # 설정 파일 경로 확인
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'

    try:
        migrator = GitLabToGitHubMigrator(config_path)
        migrator.migrate_all()

    except FileNotFoundError as e:
        print(f"\033[91m오류: {e}\033[0m")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\033[93m사용자에 의해 중단되었습니다.\033[0m")
        sys.exit(1)
    except Exception as e:
        print(f"\033[91m예상치 못한 오류: {e}\033[0m")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
