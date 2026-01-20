#!/usr/bin/env python3
"""
API 테스트 스크립트 - 어디서 에러가 발생하는지 확인
"""

import json
from migrate import GitLabAPI, GitHubAPI

# config.json 로드
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

print("=" * 70)
print("GitLab API 테스트")
print("=" * 70)

try:
    gitlab = GitLabAPI(config['gitlab']['url'], config['gitlab']['token'])
    print("✓ GitLab API 초기화 성공")

    # 존재하지 않는 프로젝트로 테스트 (404 에러 유발)
    try:
        gitlab.get_project("nonexistent/project/12345")
        print("✓ GitLab get_project 성공")
    except Exception as e:
        print(f"✗ GitLab get_project 에러: {e}")

except Exception as e:
    print(f"✗ GitLab 초기화 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("GitHub API 테스트")
print("=" * 70)

try:
    verify_ssl = config.get('options', {}).get('verify_ssl', True)
    github = GitHubAPI(config['github']['token'], verify_ssl=verify_ssl)
    print(f"✓ GitHub API 초기화 성공 (사용자: {github.user['login']})")

    # 존재하지 않는 저장소로 테스트 (404 에러 유발)
    try:
        github.get_repo("nonexistent-owner", "nonexistent-repo")
        print("✓ GitHub get_repo 성공")
    except Exception as e:
        print(f"✗ GitHub get_repo 에러: {e}")

    # 브랜치 조회 테스트
    try:
        github.get_branches("nonexistent-owner", "nonexistent-repo")
        print("✓ GitHub get_branches 성공")
    except Exception as e:
        print(f"✗ GitHub get_branches 에러: {e}")

except Exception as e:
    print(f"✗ GitHub 초기화 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("테스트 완료")
print("=" * 70)
