import asyncio
import math
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from argparse import Namespace
from pathlib import Path
from tkinter import filedialog, messagebox

from pypdf import PdfReader

from main import AgentCallbacks, AgentControls, run_agent

BACKGROUND = "#070911"
SURFACE = "#101522"
SURFACE_LIGHT = "#182033"
SURFACE_HOVER = "#222c43"
TEXT = "#f7f8ff"
MUTED_TEXT = "#8d98ad"
ACCENT = "#8b6cff"
ACCENT_LIGHT = "#c2b5ff"
CYAN = "#4edcff"
SUCCESS = "#62e5aa"
WARNING = "#ffca68"
DANGER = "#ff5574"
MAX_DOCUMENT_CHARACTERS = 250_000
type UiEvent = tuple[str, str] | tuple[str, float] | tuple[str, tuple[str, str]]


class VoiceAgentWindow:
    def __init__(self, args: Namespace) -> None:
        self.args = args
        self.root = tk.Tk()
        self.root.title("Aira - Gemini Voice Agent")
        self.root.geometry("1080x780")
        self.root.minsize(900, 680)
        self.root.configure(bg=BACKGROUND)
        self.root.protocol("WM_DELETE_WINDOW", self.end_call)

        self.events: queue.Queue[UiEvent] = queue.Queue()
        self.controls = AgentControls(
            threading.Event(), threading.Event(), queue.Queue()
        )
        self.state = "connecting"
        self.level = 0.0
        self.animation_frame = 0
        self.transcript_count = 0
        self.document_name = "No document selected"
        self.closed = False

        self._build_header()
        self._build_agent_stage()
        self._build_transcript()
        self._build_controls()
        self._start_agent()
        self._process_events()
        self._animate()

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=BACKGROUND)
        header.pack(fill="x", padx=38, pady=(26, 18))

        brand = tk.Frame(header, bg=BACKGROUND)
        brand.pack(side="left")
        tk.Label(
            brand,
            text="AIRA",
            bg=BACKGROUND,
            fg=TEXT,
            font=("DejaVu Sans", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="Gemini Live voice companion",
            bg=BACKGROUND,
            fg=MUTED_TEXT,
            font=("DejaVu Sans", 9),
        ).pack(anchor="w", pady=(2, 0))

        badges = tk.Frame(header, bg=BACKGROUND)
        badges.pack(side="right")
        tk.Label(
            badges,
            text="  EN + HI  ",
            bg=SURFACE,
            fg=ACCENT_LIGHT,
            font=("DejaVu Sans", 9, "bold"),
            padx=8,
            pady=6,
        ).pack(side="left", padx=(0, 10))
        self.connection = tk.Label(
            badges,
            text="  CONNECTING  ",
            bg=SURFACE,
            fg=MUTED_TEXT,
            font=("DejaVu Sans", 9, "bold"),
            padx=8,
            pady=6,
        )
        self.connection.pack(side="left")

    def _build_agent_stage(self) -> None:
        self.content = tk.Frame(self.root, bg=BACKGROUND)
        self.content.pack(fill="both", expand=True, padx=38)

        stage = tk.Frame(
            self.content,
            bg=SURFACE,
            width=350,
            padx=24,
            pady=22,
        )
        stage.pack(side="left", fill="y", padx=(0, 14))
        stage.pack_propagate(False)

        tk.Label(
            stage,
            text="VOICE SESSION",
            bg=SURFACE,
            fg=MUTED_TEXT,
            font=("DejaVu Sans", 9, "bold"),
        ).pack(anchor="w")

        self.orb = tk.Canvas(
            stage,
            width=280,
            height=270,
            bg=SURFACE,
            highlightthickness=0,
        )
        self.orb.pack(pady=(2, 0))
        self.state_label = tk.Label(
            stage,
            text="Joining the conversation...",
            bg=SURFACE,
            fg=TEXT,
            font=("DejaVu Sans", 17, "bold"),
            wraplength=300,
        )
        self.state_label.pack()
        self.hint_label = tk.Label(
            stage,
            text="Setting up a secure live audio session",
            bg=SURFACE,
            fg=MUTED_TEXT,
            font=("DejaVu Sans", 10),
            wraplength=290,
            justify="center",
        )
        self.hint_label.pack(pady=(7, 18))

        meter_header = tk.Frame(stage, bg=SURFACE)
        meter_header.pack(fill="x")
        tk.Label(
            meter_header,
            text="MICROPHONE",
            bg=SURFACE,
            fg=MUTED_TEXT,
            font=("DejaVu Sans", 8, "bold"),
        ).pack(side="left")
        self.mic_label = tk.Label(
            meter_header,
            text="READY",
            bg=SURFACE,
            fg=SUCCESS,
            font=("DejaVu Sans", 8, "bold"),
        )
        self.mic_label.pack(side="right")
        self.level_meter = tk.Canvas(
            stage,
            height=12,
            bg=SURFACE_LIGHT,
            highlightthickness=0,
        )
        self.level_meter.pack(fill="x", pady=(7, 18))

        document_card = tk.Frame(stage, bg=SURFACE_LIGHT, padx=14, pady=12)
        document_card.pack(fill="x", side="bottom")
        tk.Label(
            document_card,
            text="KNOWLEDGE SOURCE",
            bg=SURFACE_LIGHT,
            fg=MUTED_TEXT,
            font=("DejaVu Sans", 8, "bold"),
        ).pack(anchor="w")
        self.document_label = tk.Label(
            document_card,
            text=self.document_name,
            bg=SURFACE_LIGHT,
            fg=TEXT,
            font=("DejaVu Sans", 10, "bold"),
            anchor="w",
        )
        self.document_label.pack(fill="x", pady=(6, 2))
        self.document_detail = tk.Label(
            document_card,
            text="Upload a PDF to ask grounded questions",
            bg=SURFACE_LIGHT,
            fg=MUTED_TEXT,
            font=("DejaVu Sans", 8),
            anchor="w",
        )
        self.document_detail.pack(fill="x")

    def _build_transcript(self) -> None:
        container = tk.Frame(self.content, bg=SURFACE, padx=24, pady=20)
        container.pack(side="left", fill="both", expand=True)

        title_row = tk.Frame(container, bg=SURFACE)
        title_row.pack(fill="x", pady=(0, 14))
        tk.Label(
            title_row,
            text="Conversation",
            bg=SURFACE,
            fg=TEXT,
            font=("DejaVu Sans", 15, "bold"),
        ).pack(side="left")
        tk.Label(
            title_row,
            text="LIVE TRANSCRIPT",
            bg=SURFACE_LIGHT,
            fg=MUTED_TEXT,
            font=("DejaVu Sans", 8, "bold"),
            padx=9,
            pady=5,
        ).pack(side="right")

        self.transcript = tk.Text(
            container,
            bg="#0c111d",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("DejaVu Sans", 11),
            height=8,
            padx=18,
            pady=16,
            state="disabled",
        )
        self.transcript.pack(fill="both", expand=True)
        self.transcript.tag_configure(
            "empty", foreground=MUTED_TEXT, justify="center", spacing1=120
        )
        self.transcript.tag_configure(
            "you", foreground=CYAN, font=("DejaVu Sans", 9, "bold"), spacing1=18
        )
        self.transcript.tag_configure(
            "gemini",
            foreground=ACCENT_LIGHT,
            font=("DejaVu Sans", 9, "bold"),
            spacing1=18,
        )
        self.transcript.tag_configure(
            "body",
            foreground=TEXT,
            lmargin1=18,
            lmargin2=18,
            rmargin=18,
            spacing1=5,
            spacing3=5,
        )
        self.transcript.configure(state="normal")
        self.transcript.insert(
            "end",
            "Your conversation will appear here.\n\nStart speaking naturally in English, Hindi, or Hinglish.",
            "empty",
        )
        self.transcript.configure(state="disabled")

    def _build_controls(self) -> None:
        dock = tk.Frame(self.root, bg=BACKGROUND)
        dock.pack(fill="x", padx=38, pady=(16, 24))
        controls = tk.Frame(dock, bg=BACKGROUND)
        controls.pack()

        self.document_button = tk.Button(
            controls,
            text="Add PDF",
            command=self.upload_document,
            width=14,
            bg=SURFACE_LIGHT,
            fg=TEXT,
            activebackground=SURFACE_HOVER,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("DejaVu Sans", 10, "bold"),
            pady=13,
        )
        self.document_button.pack(side="left", padx=8)
        self.mute_button = tk.Button(
            controls,
            text="Mute mic",
            command=self.toggle_mute,
            width=14,
            bg=SURFACE_LIGHT,
            fg=TEXT,
            activebackground=SURFACE_HOVER,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("DejaVu Sans", 10, "bold"),
            pady=13,
        )
        self.mute_button.pack(side="left", padx=8)
        self.end_button = tk.Button(
            controls,
            text="End call",
            command=self.end_call,
            width=14,
            bg=DANGER,
            fg="white",
            activebackground="#d93655",
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("DejaVu Sans", 10, "bold"),
            pady=13,
        )
        self.end_button.pack(side="left", padx=8)

    def _start_agent(self) -> None:
        callbacks = AgentCallbacks(
            on_status=lambda value: self.events.put(("status", value)),
            on_transcript=lambda speaker, text: self.events.put(
                ("transcript", (speaker, text))
            ),
            on_audio_level=lambda value: self.events.put(("level", value)),
            on_warning=lambda value: self.events.put(("warning", value)),
            on_error=lambda value: self.events.put(("error", value)),
        )

        def worker() -> None:
            try:
                asyncio.run(run_agent(self.args, self.controls, callbacks))
            except Exception as error:
                self.events.put(("error", str(error)))

        threading.Thread(target=worker, daemon=True, name="gemini-live").start()

    def _process_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    assert isinstance(value, str)
                    self._set_status(value)
                elif kind == "level":
                    assert isinstance(value, float)
                    self.level = value
                elif kind == "transcript":
                    assert isinstance(value, tuple)
                    speaker, text = value
                    self._append_transcript(speaker, text)
                elif kind == "error":
                    assert isinstance(value, str)
                    self._show_error(value)
                elif kind == "warning":
                    assert isinstance(value, str)
                    self.connection.configure(text="  MIC CHECK  ", fg=WARNING)
                    self.mic_label.configure(text="NO SIGNAL", fg=WARNING)
                    self.state_label.configure(text="Microphone signal missing")
                    self.hint_label.configure(text=value)
                elif kind == "document_loaded":
                    assert isinstance(value, str)
                    self.document_button.configure(text="Replace PDF", state="normal")
                    self.document_name = value
                    self.document_label.configure(text=value)
                    self.document_detail.configure(text="Processing document context...")
                    self.hint_label.configure(text=f"Loading {value} into the conversation")
                elif kind == "document_error":
                    assert isinstance(value, str)
                    self.document_button.configure(text="Add PDF", state="normal")
                    self.document_detail.configure(text="Upload failed - choose another PDF")
                    messagebox.showerror("Could not read PDF", value, parent=self.root)
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(40, self._process_events)

    def _set_status(self, status: str) -> None:
        self.state = status
        labels = {
            "connecting": ("Joining the conversation...", "CONNECTING", MUTED_TEXT),
            "listening": ("I'm listening", "LIVE", SUCCESS),
            "thinking": ("Thinking...", "LIVE", SUCCESS),
            "speaking": ("Aira is speaking", "LIVE", SUCCESS),
            "loading_document": ("Reading your PDF...", "LOADING", WARNING),
            "document_ready": ("Document ready", "LIVE", SUCCESS),
        }
        title, badge, color = labels.get(status, (status.title(), "LIVE", "#5de5a5"))
        self.state_label.configure(text=title)
        self.connection.configure(text=f"  {badge}  ", fg=color)
        hints = {
            "connecting": "Setting up a secure live audio session",
            "listening": "Speak naturally - you can interrupt at any time",
            "thinking": "Understanding what you said",
            "speaking": "You can start speaking to interrupt",
            "loading_document": "Adding the document to this conversation",
            "document_ready": "Ask a question about the uploaded document",
        }
        self.hint_label.configure(text=hints.get(status, ""))
        if status == "document_ready":
            self.document_detail.configure(text="Ready for grounded questions")

    def upload_document(self) -> None:
        path = self._choose_pdf()
        if not path:
            return
        self.document_button.configure(text="Loading...", state="disabled")
        threading.Thread(
            target=self._extract_document,
            args=(Path(path),),
            daemon=True,
            name="pdf-extractor",
        ).start()

    def _choose_pdf(self) -> str:
        zenity = shutil.which("zenity")
        if zenity:
            result = subprocess.run(
                [
                    zenity,
                    "--file-selection",
                    "--title=Choose a PDF",
                    "--file-filter=PDF documents | *.pdf *.PDF",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            if result.returncode == 1:
                return ""

        return filedialog.askopenfilename(
            parent=self.root,
            title="Choose a PDF",
            filetypes=(("PDF documents", "*.pdf"),),
        )

    def _extract_document(self, path: Path) -> None:
        try:
            reader = PdfReader(path)
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if not text:
                raise ValueError(
                    "No readable text was found. Scanned PDFs require OCR before upload."
                )
            if len(text) > MAX_DOCUMENT_CHARACTERS:
                raise ValueError(
                    "This PDF is too large. Use a document with less than "
                    f"{MAX_DOCUMENT_CHARACTERS:,} extracted characters."
                )
            self.controls.documents.put((path.name, text))
            self.events.put(("document_loaded", path.name))
        except Exception as error:
            self.events.put(("document_error", str(error)))

    def _append_transcript(self, speaker: str, text: str) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        tag = "you" if speaker == "You" else "gemini"
        self.transcript.configure(state="normal")
        if self.transcript_count == 0:
            self.transcript.delete("1.0", "end")
        display_speaker = "YOU" if speaker == "You" else "AIRA"
        self.transcript.insert("end", f"{display_speaker}\n", tag)
        self.transcript.insert("end", f"{clean_text}\n", "body")
        self.transcript_count += 1
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _animate(self) -> None:
        self.animation_frame += 1
        phase = self.animation_frame / 9
        pulse = (1 + math.sin(phase)) / 2
        activity = (
            self.level if self.state in {"listening", "thinking"} else pulse * 0.6
        )
        radius = 58 + activity * 18

        self.orb.delete("all")
        center_x, center_y = 140, 132
        for index, color in enumerate(("#171b36", "#22224b", "#31265f")):
            ring = radius + 36 - index * 11 + pulse * 5
            self.orb.create_oval(
                center_x - ring,
                center_y - ring,
                center_x + ring,
                center_y + ring,
                fill=color,
                outline="",
            )
        self.orb.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            fill=ACCENT if self.state != "speaking" else CYAN,
            outline=ACCENT_LIGHT,
            width=2,
        )
        inner = radius * 0.55
        self.orb.create_oval(
            center_x - inner,
            center_y - inner,
            center_x + inner,
            center_y + inner,
            fill=ACCENT_LIGHT if self.state != "speaking" else "#a5f1ff",
            outline="",
        )
        sparkle = 4 + pulse * 3
        self.orb.create_oval(
            center_x - 25 - sparkle,
            center_y - 28 - sparkle,
            center_x - 25 + sparkle,
            center_y - 28 + sparkle,
            fill="#ffffff",
            outline="",
        )

        meter_width = max(1, self.level_meter.winfo_width())
        meter_level = 0.0 if self.controls.muted.is_set() else min(1.0, self.level * 4)
        self.level_meter.delete("all")
        self.level_meter.create_rectangle(
            0,
            0,
            meter_width * meter_level,
            12,
            fill=CYAN if meter_level < 0.75 else SUCCESS,
            outline="",
        )
        if not self.closed:
            self.root.after(35, self._animate)

    def toggle_mute(self) -> None:
        if self.controls.muted.is_set():
            self.controls.muted.clear()
            self.mute_button.configure(text="Mute mic", bg=SURFACE_LIGHT)
            self.mic_label.configure(text="READY", fg=SUCCESS)
            self.hint_label.configure(
                text="Speak naturally - you can interrupt at any time"
            )
        else:
            self.controls.muted.set()
            self.mute_button.configure(text="Unmute", bg="#41365f")
            self.mic_label.configure(text="MUTED", fg=WARNING)
            self.hint_label.configure(text="Microphone muted")

    def _show_error(self, message: str) -> None:
        self.connection.configure(text="  ERROR  ", fg=DANGER)
        self.mic_label.configure(text="OFFLINE", fg=DANGER)
        self.state_label.configure(text="Couldn't start the call")
        self.hint_label.configure(text=message)
        messagebox.showerror("Gemini Voice", message, parent=self.root)

    def end_call(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.controls.stop.set()
        self.root.after(100, self.root.destroy)

    def run(self) -> None:
        self.root.mainloop()
