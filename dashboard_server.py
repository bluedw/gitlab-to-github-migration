#!/usr/bin/env python3
"""
GitLab to GitHub Migration Dashboard Server
웹에서 refresh와 migrate 실행 가능 (표준 라이브러리만 사용)
"""

import http.server
import socketserver
import json
import subprocess
import os
import sys
import io
import urllib.parse
import threading
import time


# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


class MigrationHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """마이그레이션 대시보드 HTTP 요청 핸들러"""

    def do_GET(self):
        """GET 요청 처리"""
        if self.path == '/' or self.path == '/index.html':
            # dashboard.html을 index로 제공
            self.path = '/dashboard.html'

        # 정적 파일 제공
        return super().do_GET()

    def do_POST(self):
        """POST 요청 처리 (refresh, migrate, cleanup 실행)"""
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == '/api/refresh':
            self._handle_refresh()
        elif parsed_path.path == '/api/migrate':
            self._handle_migrate()
        elif parsed_path.path == '/api/cleanup':
            self._handle_cleanup()
        elif parsed_path.path == '/api/status':
            self._handle_status()
        else:
            self._send_json_response(404, {'error': 'Not Found'})

    def _handle_refresh(self):
        """Dashboard refresh 처리"""
        try:
            # dashboard.py --refresh 실행
            result = subprocess.run(
                [sys.executable, 'dashboard.py', '--refresh'],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                self._send_json_response(200, {
                    'status': 'success',
                    'message': '대시보드가 성공적으로 새로고침되었습니다.',
                    'output': result.stdout
                })
            else:
                self._send_json_response(500, {
                    'status': 'error',
                    'message': '대시보드 새로고침 실패',
                    'error': result.stderr
                })
        except subprocess.TimeoutExpired:
            self._send_json_response(500, {
                'status': 'error',
                'message': '대시보드 새로고침 시간 초과 (5분)'
            })
        except Exception as e:
            self._send_json_response(500, {
                'status': 'error',
                'message': f'오류 발생: {str(e)}'
            })

    def _handle_migrate(self):
        """Migration 처리 (백그라운드 실행)"""
        try:
            # migrate.py를 백그라운드에서 실행
            # 완료되면 자동으로 dashboard.html 생성됨

            def run_migration():
                subprocess.run(
                    [sys.executable, 'migrate.py'],
                    capture_output=True,
                    text=True
                )

            # 백그라운드 스레드에서 실행
            thread = threading.Thread(target=run_migration, daemon=True)
            thread.start()

            self._send_json_response(202, {
                'status': 'started',
                'message': '마이그레이션이 백그라운드에서 시작되었습니다. 완료되면 대시보드가 자동으로 업데이트됩니다.'
            })

        except Exception as e:
            self._send_json_response(500, {
                'status': 'error',
                'message': f'오류 발생: {str(e)}'
            })

    def _handle_cleanup(self):
        """Cleanup 처리 (백그라운드 실행)"""
        try:
            # 요청 본문 읽기 (group_path, include_subgroups)
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                params = json.loads(body)
            else:
                params = {}

            group_path = params.get('group_path')
            include_subgroups = params.get('include_subgroups', True)

            def run_cleanup():
                # cleanup_github.py를 명령행 인자와 함께 실행
                cmd = [sys.executable, 'cleanup_github.py']

                # group_path가 제공되면 -g 옵션 추가
                if group_path:
                    cmd.extend(['-g', group_path])
                    # include_subgroups 옵션 추가
                    if not include_subgroups:
                        cmd.append('--no-subgroups')

                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )

            # 백그라운드 스레드에서 실행
            thread = threading.Thread(target=run_cleanup, daemon=True)
            thread.start()

            self._send_json_response(202, {
                'status': 'started',
                'message': 'Cleanup이 백그라운드에서 시작되었습니다. 터미널에서 진행 상황을 확인하세요.'
            })

        except Exception as e:
            self._send_json_response(500, {
                'status': 'error',
                'message': f'오류 발생: {str(e)}'
            })

    def _handle_status(self):
        """마이그레이션 상태 확인"""
        try:
            # migration_results.json 파일 확인
            if os.path.exists('migration_results.json'):
                with open('migration_results.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._send_json_response(200, {
                    'status': 'available',
                    'data': {
                        'timestamp': data.get('timestamp'),
                        'total': data.get('total'),
                        'success': data.get('success'),
                        'failed': data.get('failed'),
                        'dry_run': data.get('dry_run')
                    }
                })
            else:
                self._send_json_response(200, {
                    'status': 'no_data',
                    'message': '마이그레이션 결과가 없습니다.'
                })

        except Exception as e:
            self._send_json_response(500, {
                'status': 'error',
                'message': f'오류 발생: {str(e)}'
            })

    def _send_json_response(self, status_code, data):
        """JSON 응답 전송"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        """로그 메시지 출력"""
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")


def main():
    """메인 함수"""
    PORT = 8080

    print("""
╔══════════════════════════════════════════════════════════╗
║     GitLab to GitHub Migration Dashboard Server         ║
║     웹에서 refresh/migrate 실행 가능                     ║
╚══════════════════════════════════════════════════════════╝
""")

    print(f"서버 시작 중... 포트: {PORT}")
    print(f"브라우저에서 접속: http://localhost:{PORT}")
    print("종료하려면 Ctrl+C를 누르세요.\n")

    try:
        with socketserver.TCPServer(("", PORT), MigrationHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n서버를 종료합니다...")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48 or e.errno == 98:  # Address already in use
            print(f"\n오류: 포트 {PORT}이(가) 이미 사용 중입니다.")
            print(f"다른 프로세스를 종료하거나 다른 포트를 사용하세요.")
            sys.exit(1)
        else:
            raise


if __name__ == '__main__':
    main()
