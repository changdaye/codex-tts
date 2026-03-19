from pathlib import Path
import threading

from codex_tts.ipc import JsonSocketServer, call_daemon


def test_ipc_round_trip_returns_json_response(tmp_path):
    socket_path = tmp_path / "daemon.sock"
    server = JsonSocketServer(
        socket_path,
        handler=lambda request: {
            "ok": True,
            "echo": request["message"],
        },
    )
    server.start()

    def handle_request() -> None:
        server.handle_next_request(timeout=1.0)

    worker = threading.Thread(target=handle_request)
    worker.start()
    try:
        response = call_daemon(socket_path, {"message": "hello"})
    finally:
        worker.join(timeout=2.0)
        server.close()

    assert response == {"ok": True, "echo": "hello"}


def test_json_socket_server_replaces_stale_socket_file(tmp_path):
    socket_path = tmp_path / "daemon.sock"
    socket_path.write_text("stale", encoding="utf-8")

    server = JsonSocketServer(socket_path, handler=lambda request: {"ok": True})
    try:
        server.start()
        assert socket_path.exists()
        assert socket_path.is_socket()
    finally:
        server.close()
