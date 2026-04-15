"""
camera1.py — Mobile Camera Handler for AI Crowd Surveillance System

SETUP INSTRUCTIONS FOR USER:
─────────────────────────────────────────────────────────────
Replit runs in the cloud — it cannot reach local network IPs (192.168.x.x).
You must expose your camera via a public tunnel URL.

Option A — Public URL (ngrok / Cloudflare Tunnel):
  1. Install IP Webcam app on Android (Google Play) or IP Camera Lite on iOS.
  2. Start the server in the app (default port 8080).
  3. On the same PC/phone, install ngrok and run: ngrok http 8080
  4. Copy the https://xxxx.ngrok.io URL and paste it in the sidebar with /video appended.

Option B — Browser WebRTC (no tunnel needed):
  Uses your browser's built-in camera access — works on Replit without any setup.
─────────────────────────────────────────────────────────────
"""

import cv2
import threading
import time
import urllib.request
import urllib.error
import numpy as np


# ── URL UTILITIES ────────────────────────────────────────────────────────────

def _validate_stream_url(url: str, timeout: int = 5) -> tuple[bool, str]:
    """
    Validate stream URL before opening VideoCapture.
    Blocks private/LAN IPs with a helpful error before even attempting a
    connection — they are unreachable from the Replit cloud.
    Returns (is_valid: bool, message: str).
    """
    if not url:
        return False, "No URL provided."

    url = url.strip()

    # Block private LAN IPs — unreachable from Replit cloud
    private_prefixes = (
        "http://192.168.", "http://10.", "http://172.16.",
        "http://172.17.", "http://172.18.", "http://172.19.",
        "http://172.20.", "http://172.21.", "http://172.22.",
        "http://172.23.", "http://172.24.", "http://172.25.",
        "http://172.26.", "http://172.27.", "http://172.28.",
        "http://172.29.", "http://172.30.", "http://172.31.",
        "http://localhost", "http://127.",
    )
    for prefix in private_prefixes:
        if url.startswith(prefix):
            return False, (
                "LOCAL IP DETECTED — Cannot connect from Replit.\n\n"
                "Replit runs in the cloud and cannot reach your home network.\n\n"
                "TO FIX:\n"
                "1. Keep IP Webcam running on your phone (port 8080)\n"
                "2. Download ngrok: https://ngrok.com/download\n"
                "3. Run on your PC: ngrok http 8080\n"
                "4. Copy the URL shown: https://xxxx.ngrok.io\n"
                "5. Paste that URL here (add /video at the end)\n"
                "   Example: https://xxxx.ngrok.io/video"
            )

    # Test if URL is reachable by probing the shot.jpg endpoint
    try:
        urllib.request.urlopen(url.replace("/video", "/shot.jpg"), timeout=timeout)
        return True, "Stream reachable."
    except urllib.error.URLError as e:
        return False, f"Stream unreachable: {e.reason}"
    except Exception as e:
        # Fall back to probing the base URL itself
        try:
            urllib.request.urlopen(url, timeout=timeout)
            return True, "Stream reachable."
        except Exception:
            return False, f"Cannot reach stream: {e}"


def open_ip_webcam(url: str) -> "cv2.VideoCapture | None":
    """
    Open IP Webcam stream with validation.
    Shows clear Streamlit error messages on failure.
    Returns a VideoCapture on success, None on failure.
    """
    import streamlit as st

    is_valid, message = _validate_stream_url(url)
    if not is_valid:
        st.error(f"📵 Mobile Camera Error\n\n{message}")
        return None

    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        st.error(
            f"OpenCV could not open stream: `{url}`\n\n"
            "Check the URL format. IP Webcam video stream should end with `/video`."
        )
        return None

    return cap


def test_stream_url(url: str, timeout: int = 5) -> tuple[bool, str]:
    """
    Probe a stream URL before opening VideoCapture.
    Returns (success: bool, message: str).
    """
    if not url or not url.strip():
        return False, "No URL provided."

    url = url.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        return False, f"Invalid URL format: must start with http:// or https://"

    # Probe the base URL (strip /video path for the ping check)
    probe_url = url.rsplit("/video", 1)[0].rsplit("/videofeed", 1)[0].rsplit("/mjpeg", 1)[0]
    if not probe_url:
        probe_url = url

    try:
        req = urllib.request.Request(probe_url, method="GET")
        req.add_header("User-Agent", "ICSS/1.0")
        with urllib.request.urlopen(req, timeout=timeout):
            pass
        return True, f"Stream reachable ✅  ({url})"
    except urllib.error.HTTPError as e:
        # HTTP errors still mean the server is reachable
        if e.code < 500:
            return True, f"Server reachable ✅  (HTTP {e.code} — {url})"
        return False, (
            f"Server error HTTP {e.code} at {url}. "
            "Check that IP Webcam is still running."
        )
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "192.168" in url or "10." in url or "172." in url:
            hint = (
                "Local/private IP addresses are blocked on Replit. "
                "Use a public tunnel URL (ngrok / Cloudflare Tunnel). "
                "See the setup instructions in the sidebar."
            )
        else:
            hint = f"Cannot reach {url}. Check the URL and your tunnel app."
        return False, f"Connection failed — {reason}. {hint}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


# ── MOBILE CAMERA STREAM CLASS ───────────────────────────────────────────────

class MobileCameraStream:
    """
    Handles mobile camera streaming via a public HTTP/HTTPS URL (e.g. ngrok tunnel).
    Accepts any full URL — not just local IPs — making it compatible with Replit.
    """

    def __init__(self, stream_url: str):
        """
        stream_url: Full public URL to the video stream, e.g.
                    https://abc123.ngrok.io/video
        """
        self.stream_url = stream_url.strip()

        # Derive a display-friendly base URL
        parts = self.stream_url.split("/")
        self.base_url = "/".join(parts[:3]) if len(parts) >= 3 else self.stream_url

        # Fallback candidate URLs
        base = self.base_url
        self.stream_urls = [
            self.stream_url,
            f"{base}/video",
            f"{base}/videofeed",
            f"{base}/mjpeg/1",
        ]
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for u in self.stream_urls:
            if u not in seen:
                seen.add(u)
                deduped.append(u)
        self.stream_urls = deduped

        self.cap          = None
        self.frame        = None
        self.running      = False
        self.connected    = False
        self.error_msg    = ""
        self.fps          = 0
        self._lock        = threading.Lock()
        self._thread      = None
        self._frame_count = 0
        self._start_time  = time.time()

        # Legacy compat attributes
        self.ip   = self.base_url
        self.port = ""

    # ── CONNECTION ──────────────────────────────────────────────────────────

    def test_connection(self) -> tuple[bool, str]:
        return test_stream_url(self.stream_url)

    def connect(self) -> tuple[bool, str]:
        for url in self.stream_urls:
            try:
                cap = cv2.VideoCapture(url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 30)

                if not cap.isOpened():
                    cap.release()
                    continue

                for _ in range(3):
                    cap.grab()

                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    self.cap       = cap
                    self.connected = True
                    self.error_msg = ""
                    return True, f"✅ Connected: {url}"

                cap.release()

            except Exception:
                continue

        self.error_msg = (
            "❌ Could not read frames from any stream URL.\n"
            "Make sure your tunnel (ngrok / Cloudflare) is running and the URL is correct."
        )
        return False, self.error_msg

    # ── STREAMING ───────────────────────────────────────────────────────────

    def start(self) -> tuple[bool, str]:
        ok, msg = self.connect()
        if not ok:
            return False, msg

        self.running     = True
        self._start_time = time.time()
        self._thread     = threading.Thread(
            target=self._capture_loop, daemon=True
        )
        self._thread.start()

        timeout = time.time() + 2.0
        while time.time() < timeout:
            if self.get_frame() is not None:
                return True, msg
            time.sleep(0.05)

        return True, msg + " (waiting for first frame...)"

    def _capture_loop(self):
        consecutive_failures = 0

        while self.running:
            if self.cap and self.cap.isOpened():
                grabbed = self.cap.grab()
                if grabbed:
                    ret, frame = self.cap.retrieve()
                    if ret and frame is not None and frame.size > 0:
                        frame = cv2.resize(frame, (640, 480))

                        with self._lock:
                            self.frame = frame

                        self._frame_count += 1
                        elapsed  = time.time() - self._start_time
                        self.fps = round(
                            self._frame_count / elapsed if elapsed > 0 else 0, 1
                        )
                        consecutive_failures = 0
                        continue

                consecutive_failures += 1
                if consecutive_failures > 30:
                    self.connected = False
                    consecutive_failures = 0
                    time.sleep(1)
                    self.connect()
            else:
                time.sleep(0.1)

    def get_frame(self) -> np.ndarray | None:
        with self._lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running   = False
        self.connected = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.cap:
            self.cap.release()
            self.cap = None
        with self._lock:
            self.frame = None

    def get_status(self) -> dict:
        return {
            'connected' : self.connected,
            'ip'        : self.base_url,
            'port'      : self.port,
            'fps'       : self.fps,
            'url'       : self.stream_url,
            'error'     : self.error_msg,
        }


# ── STREAMLIT SIDEBAR RENDERER ───────────────────────────────────────────────

def render_mobile_camera_sidebar(session_state) -> MobileCameraStream | None:
    """
    Renders mobile camera controls in the Streamlit sidebar.
    Supports two modes:
      - Option A: Public URL via ngrok / Cloudflare Tunnel
      - Option B: Browser WebRTC (handled in app.py main area)
    """
    import streamlit as st

    st.sidebar.markdown("---")
    st.sidebar.subheader("📱 Mobile Camera")

    camera_mode = st.sidebar.radio(
        "Connection mode",
        ["Public URL (ngrok / Tunnel)", "Browser WebRTC (no tunnel)"],
        key="mobile_camera_mode",
        help="Replit cannot reach local IPs (192.168.x.x). Use a tunnel or WebRTC.",
    )
    session_state["camera_mode"] = camera_mode

    if camera_mode == "Public URL (ngrok / Tunnel)":
        # ── Setup instructions ───────────────────────────────────────────
        with st.sidebar.expander("🔧 How to get a public URL", expanded=False):
            st.markdown("""
**Step 1 — Start IP Webcam on your phone**
- Android: [IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam) (free)
- iOS: IP Camera Lite
- Tap **Start Server** (default port: 8080)

**Step 2 — Create a tunnel from your PC**
```bash
pip install pyngrok
ngrok http 8080
```
Copy the `https://xxxx.ngrok.io` URL shown.

**Step 3 — Paste the URL below**
Append `/video` to the ngrok URL, e.g.:
`https://abc123.ngrok.io/video`

> ⚠️ Local IPs (192.168.x.x) are **blocked** on Replit — the tunnel is required.
            """)

        stream_url = st.sidebar.text_input(
            "IP Webcam Stream URL",
            value=session_state.get("ip_webcam_url", ""),
            placeholder="https://xxxx.ngrok.io/video",
            help=(
                "On Replit, use a public ngrok URL — local IPs (192.168.x.x) won't work. "
                "Run: ngrok http 8080  →  copy the https URL  →  add /video at the end."
            ),
            key="ip_webcam_url",
        )

        col_test, col_conn, col_disc = st.sidebar.columns(3)

        with col_test:
            if st.button("🔌 Test", key="mobile_test_btn"):
                if stream_url:
                    with st.sidebar.spinner("Testing…"):
                        ok, msg = test_stream_url(stream_url)
                    if ok:
                        st.sidebar.success(msg)
                    else:
                        st.sidebar.error(msg)
                else:
                    st.sidebar.warning("Enter a URL first.")

        # Determine current connection state for button guards
        _already_connected = (
            "mobile_stream" in session_state
            and session_state["mobile_stream"].connected
        )

        with col_conn:
            # Disable Connect when already live — prevents duplicate streams
            if st.button(
                "▶ Connect",
                key="mobile_connect_btn",
                disabled=_already_connected,
                help="Already connected — Stop first to reconnect." if _already_connected else None,
            ):
                if not stream_url:
                    st.sidebar.warning("Enter a stream URL first.")
                else:
                    # Pre-flight check
                    ok, msg = test_stream_url(stream_url)
                    if not ok:
                        st.sidebar.error(msg)
                        st.sidebar.info(
                            "💡 Use a public tunnel URL. "
                            "Local IPs are not reachable from Replit."
                        )
                    else:
                        if "mobile_stream" in session_state:
                            session_state["mobile_stream"].stop()

                        stream = MobileCameraStream(stream_url)
                        conn_ok, conn_msg = stream.start()

                        if conn_ok:
                            session_state["mobile_stream"]     = stream
                            session_state["use_mobile_camera"] = True
                            st.sidebar.success(conn_msg)
                        else:
                            st.sidebar.error(conn_msg)

        with col_disc:
            # Disable Stop when nothing is connected
            _can_stop = "mobile_stream" in session_state
            if st.button(
                "⏹ Stop",
                key="mobile_disconnect_btn",
                disabled=not _can_stop,
                help="No active stream to stop." if not _can_stop else None,
            ):
                if "mobile_stream" in session_state:
                    session_state["mobile_stream"].stop()
                    del session_state["mobile_stream"]
                session_state["use_mobile_camera"] = False
                st.sidebar.info("📱 Disconnected")

        # ── Status indicator ─────────────────────────────────────────────
        if "mobile_stream" in session_state:
            status = session_state["mobile_stream"].get_status()
            if status["connected"]:
                st.sidebar.success(
                    f"🟢 Live — {status['fps']} FPS\n{status['url']}"
                )
            else:
                st.sidebar.error(
                    f"🔴 Disconnected\n{status.get('error', '')}"
                )

    else:
        # Option B — Browser WebRTC
        st.sidebar.info(
            "WebRTC uses your **browser camera** directly — no tunnel needed.\n\n"
            "Select **Mobile Camera (IP Webcam)** as the Input Mode and the "
            "WebRTC streamer will appear in the main area."
        )
        session_state["use_mobile_camera"] = False

    return session_state.get("mobile_stream", None)
