"""Write a deterministic SYNTHETIC access log (combined format + latency).
5000 lines over 10 minutes. Usage: make_log.py OUT"""
import sys
routes = ["/api/orders", "/api/users", "/static/app.js", "/static/app.css"]
with open(sys.argv[1], "w") as f:
    for i in range(5000):
        m, s = divmod(i * 600 // 5000, 60)
        k = i % 100
        if k < 60:
            path, status = "/healthz", 200
        elif k < 95:
            path, status = routes[i % 4], 200 if k < 90 else 304
        elif k < 99:
            path, status = routes[i % 2], 404 if k < 97 else 401
        else:
            path, status = "/api/orders", 503
        f.write(f'10.0.{i % 7}.{i % 250} - - [17/Sep/2026:12:{m:02d}:{s:02d} +0000] '
                f'"GET {path} HTTP/1.1" {status} {100 + i % 900} "-" "synthetic-agent/1.0" 0.{i % 1000:03d}\n')
