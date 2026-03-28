"""Live progress: Tkinter in a background thread, or Rich terminal UI."""
from __future__ import annotations

import queue
import threading
import time
from collections import deque
from datetime import datetime
from typing import Callable

try:
    import tkinter as tk
    from tkinter import scrolledtext, ttk

    _HAS_TK = True
except Exception:
    _HAS_TK = False


class StatusWindow:
    """Progress bar, log (last 50 lines), stats, pause/resume."""

    def __init__(self) -> None:
        self.total: int = 0
        self.processed: int = 0
        self.successes: int = 0
        self.failures: int = 0
        self.pause_event = threading.Event()
        self._log_lines: deque[str] = deque(maxlen=50)
        self._q: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._start = time.monotonic()
        self._durations: deque[float] = deque(maxlen=20)
        self._last_batch_t: float | None = None
        self._rich_mode = not _HAS_TK
        self._on_retry_failed: Callable[[], None] | None = None

    def set_total(self, n: int) -> None:
        self.total = max(0, n)
        self._start = time.monotonic()
        self._q.put(("total", n))

    def set_retry_handler(self, fn: Callable[[], None] | None) -> None:
        self._on_retry_failed = fn

    def update(self, transcript_id: int, title: str, pass_num: int, status_str: str) -> None:
        sym = "✓" if status_str == "success" else "✗"
        if status_str == "retrying":
            sym = "⟳"
        line = f"{datetime.now().isoformat(timespec='seconds')}  [{sym}] id={transcript_id}  pass={pass_num}  {status_str}  {title[:80]}"
        self._log_lines.append(line)
        if status_str == "failed":
            self.failures += 1
        elif status_str == "success" and pass_num == 2:
            self.successes += 1
        if pass_num == 2 or (pass_num == 1 and status_str == "failed"):
            self.processed += 1
        now = time.monotonic()
        if self._last_batch_t is not None:
            self._durations.append(now - self._last_batch_t)
        self._last_batch_t = now
        self._q.put(("log", line))

    def mark_batch_tick(self) -> None:
        """Call between LLM batches to refine ETA (rolling average)."""
        self._last_batch_t = time.monotonic()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        if _HAS_TK:
            self._thread = threading.Thread(target=self._run_tk, daemon=True)
            self._thread.start()
        else:
            self._thread = threading.Thread(target=self._run_rich_stub, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        self._q.put(("quit", None))

    def _run_tk(self) -> None:
        root = tk.Tk()
        root.title("SA Locals RAG — pipeline")
        root.geometry("720x420")

        top = ttk.Frame(root, padding=8)
        top.pack(fill=tk.X)

        self._var_prog = tk.StringVar(value="This run: 0 / 0 videos (not transcript #)")
        ttk.Label(top, textvariable=self._var_prog).pack(anchor=tk.W)

        self._pb = ttk.Progressbar(top, length=680, mode="determinate")
        self._pb.pack(fill=tk.X, pady=4)

        stats = ttk.Frame(root, padding=8)
        stats.pack(fill=tk.X)
        self._var_stats = tk.StringVar(value="OK: 0  Fail: 0  ETA: —")
        ttk.Label(stats, textvariable=self._var_stats).pack(anchor=tk.W)

        logf = ttk.Frame(root, padding=8)
        logf.pack(fill=tk.BOTH, expand=True)
        self._txt = scrolledtext.ScrolledText(logf, height=14, state=tk.DISABLED)
        self._txt.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(root, padding=8)
        btns.pack(fill=tk.X)

        def toggle_pause() -> None:
            if self.pause_event.is_set():
                self.pause_event.clear()
                btn_pause.config(text="Pause")
            else:
                self.pause_event.set()
                btn_pause.config(text="Resume")

        btn_pause = ttk.Button(btns, text="Pause", command=toggle_pause)
        btn_pause.pack(side=tk.LEFT, padx=4)

        def retry_click() -> None:
            if self._on_retry_failed:
                self._on_retry_failed()

        ttk.Button(btns, text="Retry Failed (callback)", command=retry_click).pack(
            side=tk.LEFT, padx=4
        )

        def poll() -> None:
            try:
                while True:
                    kind, payload = self._q.get_nowait()
                    if kind == "quit":
                        root.destroy()
                        return
                    if kind == "total":
                        self._var_prog.set(f"This run: 0 / {payload} videos (queued)")
                        self._pb["maximum"] = max(1, int(payload))
                        self._pb["value"] = 0
                    if kind == "log":
                        self._txt.config(state=tk.NORMAL)
                        self._txt.insert(tk.END, payload + "\n")
                        self._txt.see(tk.END)
                        self._txt.config(state=tk.DISABLED)
                        self._var_prog.set(
                            f"This run: {self.processed} / {max(1, self.total)} videos"
                        )
                        self._pb["value"] = min(self.processed, self._pb["maximum"])
                        eta = self._eta_str()
                        self._var_stats.set(
                            f"OK: {self.successes}  Fail: {self.failures}  ETA: {eta}"
                        )
            except queue.Empty:
                pass
            if self._running.is_set() or root.winfo_exists():
                root.after(120, poll)

        root.after(100, poll)
        root.mainloop()

    def _eta_str(self) -> str:
        if self.total <= 0 or not self._durations:
            return "—"
        avg = sum(self._durations) / len(self._durations)
        per_video = avg / 3.0 if avg > 0 else 0
        remaining = max(0, self.total - self.processed)
        sec = remaining * per_video * 2
        if sec < 60:
            return f"~{int(sec)}s"
        return f"~{int(sec // 60)}m"

    def _run_rich_stub(self) -> None:
        try:
            from rich.console import Console
            from rich.live import Live
            from rich.table import Table

            console = Console()

            def render() -> Table:
                t = Table(title="SA Locals RAG")
                t.add_column("Progress")
                t.add_row(f"{self.processed} / {self.total}")
                t.add_row(f"OK {self.successes}  Fail {self.failures}")
                t.add_row(self._eta_str())
                t.add_row("— log —")
                for line in list(self._log_lines)[-12:]:
                    t.add_row(line[:120])
                return t

            with Live(render(), refresh_per_second=4, console=console) as live:
                while self._running.is_set():
                    live.update(render())
                    time.sleep(0.25)
        except Exception:
            while self._running.is_set():
                time.sleep(0.5)


def make_pipeline_callback(sw: StatusWindow) -> Callable[[int, str, int, str], None]:
    return sw.update
