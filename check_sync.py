#!/usr/bin/env python3
"""
GitLab과 GitHub 저장소 동기화 상태 확인 도구
브랜치/태그 개수, 각 브랜치별 커밋 상태를 비교합니다.
"""

import json
import sys
import io
from typing import Dict, List, Tuple
from migrate import GitLabAPI, GitHubAPI, MigrationLogger


# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


class SyncChecker:
    """GitLab과 GitHub 저장소 동기화 상태 확인 클래스"""

    def __init__(self, config_path: str = "config.json"):
        """
        초기화

        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.logger = MigrationLogger()

        # GitLab API 클라이언트 초기화
        self.gitlab = GitLabAPI(
            self.config['gitlab']['url'],
            self.config['gitlab']['token']
        )

        # GitHub API 클라이언트 초기화
        verify_ssl = self.config.get('options', {}).get('verify_ssl', True)
        self.github = GitHubAPI(
            self.config['github']['token'],
            verify_ssl=verify_ssl
        )

    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"설정 파일을 찾을 수 없습니다: {config_path}\n"
                f"config.example.json을 참고하여 config.json을 생성하세요."
            )

    def check_repository_sync(
        self,
        gitlab_project_id: str,
        github_owner: str,
        github_repo: str,
        show_behind_details: bool = True
    ) -> Dict:
        """
        단일 저장소의 동기화 상태 확인

        Args:
            gitlab_project_id: GitLab 프로젝트 ID 또는 경로
            github_owner: GitHub 소유자 (조직 또는 사용자)
            github_repo: GitHub 저장소 이름
            show_behind_details: Behind 상세정보 표시 여부

        Returns:
            동기화 상태 딕셔너리
        """
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"동기화 상태 확인")
        self.logger.info(f"GitLab: {gitlab_project_id}")
        self.logger.info(f"GitHub: {github_owner}/{github_repo}")
        self.logger.info(f"{'='*70}\n")

        sync_status = {
            'gitlab_project': gitlab_project_id,
            'github_repo': f"{github_owner}/{github_repo}",
            'branches': {},
            'tags': {},
            'summary': {}
        }

        try:
            # 1. 브랜치 비교
            self.logger.info("📊 브랜치 비교 중...")
            gitlab_branches = self.gitlab.get_branches(gitlab_project_id)
            github_branches = self.github.get_branches(github_owner, github_repo)

            sync_status['branches'] = self._compare_branches(
                gitlab_branches,
                github_branches,
                github_owner,
                github_repo,
                show_behind_details
            )

            # 2. 태그 비교
            self.logger.info("\n🏷️  태그 비교 중...")
            gitlab_tags = self.gitlab.get_tags(gitlab_project_id)
            github_tags = self.github.get_tags(github_owner, github_repo)

            sync_status['tags'] = self._compare_tags(gitlab_tags, github_tags)

            # 3. 요약 정보
            sync_status['summary'] = self._generate_summary(sync_status)

            # 4. 결과 출력
            self._print_sync_status(sync_status)

            return sync_status

        except Exception as e:
            self.logger.error(f"동기화 상태 확인 실패: {e}")
            import traceback
            traceback.print_exc()
            return sync_status

    def _compare_branches(
        self,
        gitlab_branches: List[Dict],
        github_branches: List[Dict],
        github_owner: str,
        github_repo: str,
        show_behind_details: bool
    ) -> Dict:
        """
        브랜치 비교

        Args:
            gitlab_branches: GitLab 브랜치 목록
            github_branches: GitHub 브랜치 목록
            github_owner: GitHub 소유자
            github_repo: GitHub 저장소 이름
            show_behind_details: Behind 상세정보 표시 여부

        Returns:
            브랜치 비교 결과
        """
        result = {
            'gitlab_count': len(gitlab_branches),
            'github_count': len(github_branches),
            'details': []
        }

        # 브랜치 이름을 키로 하는 딕셔너리 생성
        gitlab_branch_dict = {b['name']: b for b in gitlab_branches}
        github_branch_dict = {b['name']: b for b in github_branches}

        # 모든 브랜치 이름 수집
        all_branch_names = set(gitlab_branch_dict.keys()) | set(github_branch_dict.keys())

        for branch_name in sorted(all_branch_names):
            gitlab_branch = gitlab_branch_dict.get(branch_name)
            github_branch = github_branch_dict.get(branch_name)

            branch_info = {
                'name': branch_name,
                'status': '',
                'gitlab_commit': '',
                'github_commit': '',
                'behind_details': None
            }

            if gitlab_branch and github_branch:
                # 양쪽에 모두 존재
                gitlab_sha = gitlab_branch['commit']['id']
                github_sha = github_branch['commit']['sha']

                if gitlab_sha == github_sha:
                    branch_info['status'] = '✓ Synced'
                    branch_info['gitlab_commit'] = gitlab_sha[:8]
                    branch_info['github_commit'] = github_sha[:8]
                else:
                    branch_info['status'] = '⚠ Different'
                    branch_info['gitlab_commit'] = gitlab_sha[:8]
                    branch_info['github_commit'] = github_sha[:8]

                    # Behind 상세정보 조회
                    if show_behind_details:
                        try:
                            # GitHub API로 커밋 비교
                            compare = self.github.compare_commits(
                                github_owner,
                                github_repo,
                                github_sha,
                                gitlab_sha
                            )

                            behind_by = compare.get('behind_by', 0)
                            ahead_by = compare.get('ahead_by', 0)

                            if behind_by > 0:
                                branch_info['behind_details'] = {
                                    'behind_by': behind_by,
                                    'ahead_by': ahead_by,
                                    'commits': []
                                }

                                # Behind 커밋 목록 (최대 10개)
                                commits = compare.get('commits', [])
                                for commit in commits[:10]:
                                    branch_info['behind_details']['commits'].append({
                                        'sha': commit['sha'][:8],
                                        'message': commit['commit']['message'].split('\n')[0][:60],
                                        'author': commit['commit']['author']['name'],
                                        'date': commit['commit']['author']['date']
                                    })

                        except Exception as e:
                            branch_info['behind_details'] = {'error': str(e)}

            elif gitlab_branch:
                # GitLab에만 존재
                branch_info['status'] = '✗ Missing in GitHub'
                branch_info['gitlab_commit'] = gitlab_branch['commit']['id'][:8]
                branch_info['github_commit'] = '-'
            else:
                # GitHub에만 존재
                branch_info['status'] = '✗ Extra in GitHub'
                branch_info['gitlab_commit'] = '-'
                branch_info['github_commit'] = github_branch['commit']['sha'][:8]

            result['details'].append(branch_info)

        return result

    def _compare_tags(self, gitlab_tags: List[Dict], github_tags: List[Dict]) -> Dict:
        """
        태그 비교

        Args:
            gitlab_tags: GitLab 태그 목록
            github_tags: GitHub 태그 목록

        Returns:
            태그 비교 결과
        """
        result = {
            'gitlab_count': len(gitlab_tags),
            'github_count': len(github_tags),
            'details': []
        }

        # 태그 이름을 키로 하는 딕셔너리 생성
        gitlab_tag_dict = {t['name']: t for t in gitlab_tags}
        github_tag_dict = {t['name']: t for t in github_tags}

        # 모든 태그 이름 수집
        all_tag_names = set(gitlab_tag_dict.keys()) | set(github_tag_dict.keys())

        for tag_name in sorted(all_tag_names):
            gitlab_tag = gitlab_tag_dict.get(tag_name)
            github_tag = github_tag_dict.get(tag_name)

            tag_info = {
                'name': tag_name,
                'status': '',
                'gitlab_commit': '',
                'github_commit': ''
            }

            if gitlab_tag and github_tag:
                # 양쪽에 모두 존재
                gitlab_sha = gitlab_tag['commit']['id'] if 'commit' in gitlab_tag else gitlab_tag.get('target', '')
                github_sha = github_tag['commit']['sha']

                if gitlab_sha == github_sha:
                    tag_info['status'] = '✓ Synced'
                else:
                    tag_info['status'] = '⚠ Different'

                tag_info['gitlab_commit'] = gitlab_sha[:8] if gitlab_sha else '-'
                tag_info['github_commit'] = github_sha[:8]

            elif gitlab_tag:
                # GitLab에만 존재
                tag_info['status'] = '✗ Missing in GitHub'
                gitlab_sha = gitlab_tag['commit']['id'] if 'commit' in gitlab_tag else gitlab_tag.get('target', '')
                tag_info['gitlab_commit'] = gitlab_sha[:8] if gitlab_sha else '-'
                tag_info['github_commit'] = '-'
            else:
                # GitHub에만 존재
                tag_info['status'] = '✗ Extra in GitHub'
                tag_info['gitlab_commit'] = '-'
                tag_info['github_commit'] = github_tag['commit']['sha'][:8]

            result['details'].append(tag_info)

        return result

    def _generate_summary(self, sync_status: Dict) -> Dict:
        """
        동기화 상태 요약 생성

        Args:
            sync_status: 동기화 상태

        Returns:
            요약 정보
        """
        branches = sync_status['branches']['details']
        tags = sync_status['tags']['details']

        synced_branches = sum(1 for b in branches if b['status'] == '✓ Synced')
        different_branches = sum(1 for b in branches if '⚠' in b['status'])
        missing_branches = sum(1 for b in branches if 'Missing' in b['status'])
        extra_branches = sum(1 for b in branches if 'Extra' in b['status'])

        synced_tags = sum(1 for t in tags if t['status'] == '✓ Synced')
        different_tags = sum(1 for t in tags if '⚠' in t['status'])
        missing_tags = sum(1 for t in tags if 'Missing' in t['status'])
        extra_tags = sum(1 for t in tags if 'Extra' in t['status'])

        is_fully_synced = (
            different_branches == 0 and
            missing_branches == 0 and
            extra_branches == 0 and
            different_tags == 0 and
            missing_tags == 0 and
            extra_tags == 0
        )

        return {
            'is_fully_synced': is_fully_synced,
            'branches': {
                'synced': synced_branches,
                'different': different_branches,
                'missing': missing_branches,
                'extra': extra_branches
            },
            'tags': {
                'synced': synced_tags,
                'different': different_tags,
                'missing': missing_tags,
                'extra': extra_tags
            }
        }

    def _print_sync_status(self, sync_status: Dict):
        """
        동기화 상태 출력

        Args:
            sync_status: 동기화 상태
        """
        branches = sync_status['branches']
        tags = sync_status['tags']
        summary = sync_status['summary']

        # 브랜치 상태 출력
        print(f"\n{'='*70}")
        print(f"📊 브랜치 비교 결과")
        print(f"{'='*70}")
        print(f"GitLab: {branches['gitlab_count']}개 | GitHub: {branches['github_count']}개")
        print(f"{'-'*70}")
        print(f"{'브랜치명':<30} {'상태':<20} {'GitLab':<12} {'GitHub':<12}")
        print(f"{'-'*70}")

        for branch in branches['details']:
            print(f"{branch['name']:<30} {branch['status']:<20} {branch['gitlab_commit']:<12} {branch['github_commit']:<12}")

            # Behind 상세정보 표시
            if branch.get('behind_details'):
                details = branch['behind_details']
                if 'error' in details:
                    print(f"  └─ 비교 실패: {details['error']}")
                elif details.get('behind_by', 0) > 0:
                    print(f"  └─ GitHub가 {details['behind_by']}개 커밋 뒤처짐 (GitLab이 {details['ahead_by']}개 앞섬)")
                    for commit in details['commits']:
                        print(f"     • {commit['sha']} - {commit['message']}")
                        print(f"       {commit['author']} ({commit['date']})")

        # 태그 상태 출력
        print(f"\n{'='*70}")
        print(f"🏷️  태그 비교 결과")
        print(f"{'='*70}")
        print(f"GitLab: {tags['gitlab_count']}개 | GitHub: {tags['github_count']}개")
        print(f"{'-'*70}")
        print(f"{'태그명':<30} {'상태':<20} {'GitLab':<12} {'GitHub':<12}")
        print(f"{'-'*70}")

        for tag in tags['details']:
            print(f"{tag['name']:<30} {tag['status']:<20} {tag['gitlab_commit']:<12} {tag['github_commit']:<12}")

        # 요약 정보 출력
        print(f"\n{'='*70}")
        print(f"📝 동기화 요약")
        print(f"{'='*70}")

        if summary['is_fully_synced']:
            self.logger.success("✓ 완전히 동기화되어 있습니다!")
        else:
            self.logger.warning("⚠ 동기화 문제가 발견되었습니다.")

        print(f"\n브랜치:")
        print(f"  - 동기화됨: {summary['branches']['synced']}개")
        if summary['branches']['different'] > 0:
            print(f"  - 커밋 차이: {summary['branches']['different']}개")
        if summary['branches']['missing'] > 0:
            print(f"  - GitHub 누락: {summary['branches']['missing']}개")
        if summary['branches']['extra'] > 0:
            print(f"  - GitHub 추가: {summary['branches']['extra']}개")

        print(f"\n태그:")
        print(f"  - 동기화됨: {summary['tags']['synced']}개")
        if summary['tags']['different'] > 0:
            print(f"  - 커밋 차이: {summary['tags']['different']}개")
        if summary['tags']['missing'] > 0:
            print(f"  - GitHub 누락: {summary['tags']['missing']}개")
        if summary['tags']['extra'] > 0:
            print(f"  - GitHub 추가: {summary['tags']['extra']}개")

        print()

    def check_all_repositories(self):
        """설정 파일의 모든 저장소 동기화 상태 확인"""
        repositories = self.config.get('repositories', [])
        github_org = self.config['github'].get('organization')
        github_owner = github_org if github_org else self.github.user['login']

        if not repositories:
            self.logger.warning("확인할 저장소가 없습니다.")
            self.logger.info("config.json의 repositories 섹션을 확인하세요.")
            return

        self.logger.info(f"총 {len(repositories)}개의 저장소 동기화 상태를 확인합니다.\n")

        results = []

        for idx, repo_config in enumerate(repositories, 1):
            gitlab_project = repo_config.get('gitlab_project_id') or repo_config.get('gitlab_project_path')
            github_repo = repo_config['github_repo_name']

            self.logger.info(f"[{idx}/{len(repositories)}] 확인 중...")

            result = self.check_repository_sync(
                gitlab_project,
                github_owner,
                github_repo,
                show_behind_details=True
            )

            results.append(result)

        # 전체 요약
        print(f"\n{'='*70}")
        print(f"🎯 전체 요약")
        print(f"{'='*70}")

        fully_synced = sum(1 for r in results if r['summary'].get('is_fully_synced'))
        has_issues = len(results) - fully_synced

        self.logger.info(f"완전 동기화: {fully_synced}개")
        if has_issues > 0:
            self.logger.warning(f"동기화 문제: {has_issues}개")


def main():
    """메인 함수"""
    CYAN = '\033[96m'
    RESET = '\033[0m'

    print(f"""
{CYAN}╔══════════════════════════════════════════════════════════╗
║     GitLab ↔ GitHub Sync Status Checker                 ║
║     저장소 동기화 상태 확인 도구                         ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")

    # 설정 파일 경로 확인
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'

    try:
        checker = SyncChecker(config_path)
        checker.check_all_repositories()

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
