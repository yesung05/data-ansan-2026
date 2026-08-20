"""로컬 서버 실행 스크립트.

index.html 을 더블클릭하면 ES 모듈이 CORS 정책에 막혀 3D가 뜨지 않는다.
이 스크립트로 띄우면 그 문제 없이 바로 열린다.

    python serve.py            # 8000 포트
    python serve.py 8080       # 포트 지정
"""

import http.server
import os
import socketserver
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        # 수정한 JS/CSS 가 캐시에 가려 안 보이는 일을 막는다
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # 요청 로그는 생략


def main():
    socketserver.TCPServer.allow_reuse_address = True
    try:
        server = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    except OSError as err:
        print(f"[오류] {PORT} 포트를 열 수 없습니다: {err}")
        print(f"       다른 포트로 실행해 보세요 —  python serve.py {PORT + 1}")
        return 1

    url = f"http://localhost:{PORT}/"
    print(f"돼지 저금통 공장 라인 3D 시뮬레이터")
    print(f"  {url}")
    print(f"  종료: Ctrl+C")
    threading.Timer(0.5, webbrowser.open, args=[url]).start()

    with server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n서버를 종료했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
