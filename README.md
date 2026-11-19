# Aira - Gemini Live Personal Voice Agent

Aira is a real-time, speech-to-speech personal assistant powered by the
Gemini Live API. It listens through the microphone, responds with natural
spoken audio, follows the conversation, and keeps its help focused on the
user's goals, routines, preferences, and daily life.

![Aira desktop voice interface](https://github.com/user-attachments/assets/3309095c-25f7-4021-b85a-2a0d08c78a83)

## Highlights

- **Live voice conversation** with low-latency microphone streaming and audio playback
- **Personal companion behavior** focused on goals, routines, planning, and decisions
- **English, Hindi, and Hinglish** with automatic language matching
- **Consistent feminine voice** with a warm, gentle speaking style
- **Interruption support** so the user can speak while Aira is responding
- **Live transcript** for both user and assistant speech
- **Microphone activity meter** with mute and signal warnings
- **PDF-grounded questions** using locally extracted document text
- **Native Linux file selection** through GTK when `zenity` is available
- **Desktop and terminal modes** from the same application

## How it works

```text
Microphone (16 kHz PCM)
        |
        v
Gemini Live API <---- PDF context
        |
        v
Speakers (24 kHz PCM) + live transcript
```

The desktop interface runs on Tkinter while Gemini, audio capture, playback,
and document delivery run asynchronously in the background. Audio is captured
with `arecord` and played with `aplay`, avoiding a native PortAudio dependency.

## Requirements

- Linux desktop
- Python 3.14 or newer
- [`uv`](https://docs.astral.sh/uv/)
- ALSA utilities providing `arecord` and `aplay`
- A [Gemini API key](https://aistudio.google.com/api-keys)
- A working microphone and speaker or headphones
- Optional: `zenity` for the native GTK PDF selector

On Debian or Ubuntu, the required system audio tools are available from the
`alsa-utils` package.

## Quick start

### 1. Install project dependencies

```bash
uv sync
```

### 2. Add the Gemini API key

Create a `.env` file in the project root:

```dotenv
GEMINI_API_KEY=your-api-key-here
```

The application loads this file automatically. `.env` is excluded by
`.gitignore`; never commit the real API key.

### 3. Start Aira

```bash
uv run voice-agent
```

The desktop call interface opens automatically. Start speaking when the status
changes to **LIVE**. Headphones are recommended to prevent Aira's output from
being captured by the microphone.

## Personal assistant behavior

Aira is designed as a personal companion rather than a generic question-answer
bot. During the current call, it can use details the user shares about:

- Priorities and current goals
- Daily routines and habits
- Work, study, and personal projects
- Preferred communication style
- Decisions, reflections, and next steps

Aira does not claim persistent memory between separate calls. Personal context
is available to the active Gemini Live session only and may need to be shared
again after restarting the application.

## Ask questions about a PDF

1. Select **Add PDF** in the desktop interface.
2. Choose a text-based PDF using the system file selector.
3. Wait until the knowledge source reports that it is ready.
4. Ask questions naturally by voice.

PDF text is extracted locally before being sent to the active conversation.
The uploaded document becomes the primary source for later answers, while
general knowledge may be added when useful and clearly distinguished.

### PDF limitations

- Scanned or image-only PDFs require OCR before upload.
- Extracted text is limited to 250,000 characters.
- Adding another PDF replaces the previous document context.

## Configuration

Command-line options can override the defaults:

```bash
uv run voice-agent --help
uv run voice-agent --terminal
uv run voice-agent --voice Sulafat
uv run voice-agent --input-device default --output-device default
uv run voice-agent --system-instruction "Help me stay focused on my study plan."
```

The same settings can be placed in `.env`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Gemini API authentication | Required |
| `GEMINI_LIVE_MODEL` | Gemini Live model ID | `gemini-3.8-live` |
| `GEMINI_LIVE_VOICE` | Prebuilt Gemini voice | `Sulafat` |
| `GEMINI_SYSTEM_INSTRUCTION` | Custom assistant behavior | Aira personal companion prompt |
| `AUDIO_INPUT_DEVICE` | ALSA capture device | `default` |
| `AUDIO_OUTPUT_DEVICE` | ALSA playback device | `default` |

The fixed voice and language-stability instructions remain active when a custom
assistant instruction is supplied.

## Terminal mode

Run without the desktop interface:

```bash
uv run voice-agent --terminal
```

Use `Ctrl+C` to stop the session.

## Troubleshooting

### No microphone activity

List ALSA capture devices:

```bash
arecord -L
```

On PipeWire systems, inspect and select the intended input source:

```bash
wpctl status
wpctl set-default <source-id>
```

The microphone selected in the system sound settings must be active and not a
disconnected Bluetooth source.

### No audio response

List playback devices and try an explicit device:

```bash
aplay -L
uv run voice-agent --output-device <device-name>
```

Also confirm that the application output is not muted in the system mixer.

### API key error

Confirm that `.env` exists in the project root and contains either
`GEMINI_API_KEY` or `GOOGLE_API_KEY`.

### PDF selector does not look native

Install `zenity` to use the GTK system file selector. The application falls
back to Tkinter's file chooser when `zenity` is unavailable.

## Project structure

| File | Responsibility |
| --- | --- |
| `main.py` | Gemini Live session, audio streaming, transcripts, and document delivery |
| `desktop_ui.py` | Desktop call interface, PDF extraction, and UI event handling |
| `pyproject.toml` | Project metadata, dependencies, and executable entry point |
| `uv.lock` | Reproducible dependency versions |

## Privacy notes

- The API key remains in the local `.env` file.
- PDF text is extracted locally, then sent to Gemini as conversation context.
- Spoken audio is streamed to the Gemini Live API to generate responses.
- The current implementation does not provide persistent personal memory.

## Development checks

```bash
uv run python -m compileall -q main.py desktop_ui.py
uv build
git diff --check
```
