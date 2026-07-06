"""Smoke test: ARCclaude App HTTP surface (no AI key needed).

Run:  uv run python tests/smoke_app.py
"""

import json
import subprocess
import sys
import time
import urllib.request

PORT = 8991  # avoid clashing with a real app instance
PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {name}")
    else:
        FAIL += 1; print(f"  FAIL  {name}  {detail}")


def get(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=10) as r:
        return r.status, r.read().decode("utf-8", "replace")


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-c",
         f"from arcclaude.webapp import app; import uvicorn; "
         f"uvicorn.run(app, host='127.0.0.1', port={PORT}, log_level='error')"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        ok = False
        for _ in range(40):
            time.sleep(0.5)
            try:
                status, _body = get("/api/status")
                ok = status == 200
                break
            except OSError:
                continue
        check("server starts", ok)

        status, body = get("/")
        check("page served", status == 200 and "ARCclaude" in body and "Connect Pro" in body)

        status, body = get("/api/status")
        st = json.loads(body)
        check("status JSON has keys",
              all(k in st for k in ("configured", "engine", "pro_running", "live_link")))

        status, body = get("/api/liveline")
        check("liveline includes listener path",
              "live_listener.py" in json.loads(body)["line"])

        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}/api/send", method="POST",
            data=json.dumps({"text": ""}).encode(), headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
            check("empty send rejected", False, "got 200")
        except urllib.error.HTTPError as e:
            check("empty send rejected", e.code == 400, str(e.code))
    finally:
        proc.kill()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
