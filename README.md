# Gemini Live Voice Agent

A minimal real-time speech-to-speech agent. It captures 16 kHz PCM audio from
the microphone, streams it to the Gemini Live API, and plays Gemini's 24 kHz
PCM response through the speakers.
<img width="1130" height="867" alt="image" src="https://github.com/user-attachments/assets/dbedee50-ee6a-4dc9-b56b-27419ac9dad7" />


## Requirements

- Python 3.14+
- [`uv`](https://docs.astral.sh/uv/)
- Linux with ALSA utilities (`arecord` and `aplay`)
- A [Gemini API key](https://aistudio.google.com/api-keys)

## Setup

```bash
uv sync
cp .env.example .env
# Replace your-api-key inside .env with the real key.
uv run voice-agent
```

The agent automatically loads `.env` from this project. The real `.env` is
ignored by Git and must not be committed.

The dark desktop interface opens automatically with an animated voice orb,
live transcript, microphone activity, mute control, and end-call button.
Headphones are recommended to prevent the microphone from capturing Gemini's
output.

The default `Aoede` voice keeps one warm, feminine, sweet delivery throughout
the call. Responses are limited to English, Hindi, and natural Hinglish, and
the assistant mirrors the language currently used by the speaker.

Aira is configured as a personal companion rather than a generic assistant. It
learns preferences, goals, routines, projects, and communication style during
the current call, then uses that context for personal planning, decisions,
habits, reflection, and focused next steps. Conversation context is session-only;
Aira does not claim to remember personal details after the call ends.

Select **Upload PDF** during a call to add a document. The PDF text is extracted
locally and sent to the current Gemini Live conversation. Future spoken answers
prioritize that document and may supplement it with clearly distinguished
general knowledge. Text-based PDFs are supported; scanned PDFs require OCR.

## Configuration

```bash
uv run voice-agent --help
uv run voice-agent --system-instruction "You are a concise coding tutor."
uv run voice-agent --terminal
```

The fixed voice can still be changed deliberately with `--voice` or
`GEMINI_LIVE_VOICE`. The model can be changed with `--model` or
`GEMINI_LIVE_MODEL`. ALSA devices
can be selected with `--input-device` and `--output-device`; list available
devices with `arecord -L` and `aplay -L`.

If the UI reports that the microphone signal is missing, choose the intended
input in the system sound settings. On PipeWire systems, `wpctl status` shows
the available sources and `wpctl set-default <source-id>` selects one.
