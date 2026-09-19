#!/usr/bin/env python3

import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

WIDTH = 2592
HEIGHT = 1944
FPS = 15
PORT = 8080


class CameraHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            html = """<!DOCTYPE html>
<html>
<head>
    <title>Pi Camera</title>
    <meta name="viewport" content="width=device-width">
</head>
<body style="margin:0;background:#111;text-align:center">
    <img src="/stream" style="max-width:100%;height:auto">
</body>
</html>"""

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html.encode())

        elif self.path == "/stream":

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=frame"
            )
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()

            cmd = [
                "rpicam-vid",
                "-t", "0",
                "--width", str(WIDTH),
                "--height", str(HEIGHT),
                "--framerate", str(FPS),
                "--codec", "mjpeg",
                "--inline",
                "-o", "-"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )

            try:
                data = b""

                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break

                    data += chunk

                    while True:
                        start = data.find(b"\xff\xd8")
                        if start < 0:
                            data = data[-1:]
                            break

                        end = data.find(b"\xff\xd9", start + 2)

                        if end < 0:
                            data = data[start:]
                            break

                        jpg = data[start:end + 2]
                        data = data[end + 2:]

                        self.wfile.write(
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " +
                            str(len(jpg)).encode() +
                            b"\r\n\r\n" +
                            jpg +
                            b"\r\n"
                        )
                        self.wfile.flush()

            except (BrokenPipeError, ConnectionResetError):
                pass

            finally:
                process.terminate()


server = HTTPServer(("0.0.0.0", PORT), CameraHandler)

print(f"Camera stream: http://0.0.0.0:{PORT}")

server.serve_forever()