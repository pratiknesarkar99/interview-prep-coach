# Interview Prep Coach

An AI-powered interview coach built on Azure AI Foundry and the OpenAI Responses API. Paste a job description and your resume, and the app conducts a realistic 6-turn mock interview tailored to the role, then generates a structured debrief with specific feedback on your answers.

![Setup Panel](screenshots/setup.png)
![Interview Panel](screenshots/interview.png)
![Debrief Panel](screenshots/debrief.png)

---

## What It Does

1. **Context compression** - Resume and job description are compressed into a compact context in a single API call. Raw inputs are discarded immediately after. The compressed context is used for the rest of the session.
2. **Mock interview** - The model conducts a 6-turn interview, asking one focused question per turn and adapting follow-up questions based on your actual answers using `previous_response_id` for stateful context tracking.
3. **Streaming responses** - Questions and debrief text stream in incrementally, same pattern used in production AI applications.
4. **Debrief** - After the session, a structured critique is generated from a compact turn log covering communication strengths, weak answers, what a real interviewer likely noted, and one concrete improvement.

---

## Architecture

```
User Browser
     │
     ▼
Flask App (app.py)
     │
     ├── POST /start          → compress_context() → SessionState
     ├── POST /first-question → Responses API (stream)
     ├── POST /answer         → Responses API (stream, previous_response_id)
     └── POST /debrief        → Responses API (stream, turn_log only)
                                        │
                                        ▼
                              Azure AI Foundry
                              GPT-4.1 (deployed model)
```

### Token efficiency decisions

This was a first-class design constraint, not an afterthought.

| Decision | Why |
|---|---|
| Compress resume + JD once at session start | Raw inputs (~800 tokens) are never sent again. Compressed context is ~200 tokens. |
| `previous_response_id` for conversation state | No need to re-send message history on every turn. Azure manages the chain server-side. |
| Turn log truncated at logging time (80/120 chars) | Debrief input size is predictable and bounded regardless of answer length. |
| `max_output_tokens` cap on every call | No runaway responses. Each call has an explicit ceiling. |
| Hard 6-turn limit | Prevents unbounded session growth. Keeps total session cost under ~5,000 tokens. |

**Approximate token cost per full session:**

| Step | Input | Output cap |
|---|---|---|
| Compression | ~800 | 300 |
| First question | ~250 | 150 |
| 5 follow-up turns | ~1,250 | 750 |
| Debrief | ~400 | 400 |
| **Total** | **~2,700** | **~1,600** |

---

## Tech Stack

- **Azure AI Foundry** - Model deployment and management
- **OpenAI Responses API** - Stateful conversation via `previous_response_id`, streaming
- **GPT-4.1** - Underlying model
- **Flask** - Lightweight backend, streaming via `stream_with_context`
- **Azure Identity** - `DefaultAzureCredential` for Entra ID auth in local development
- **pypdf** - Local PDF parsing before any API call (no token cost for resume upload)
- **Docker** - Containerized for consistent deployment

---

## Project Structure

```
chat-app/
├── app.py          # Flask backend, all API routes
├── context.py      # Client setup, compression call, SessionState
├── prompts.py      # All system prompts in one place
├── coach.py        # CLI version (works independently of Flask)
├── templates/
│   └── index.html  # Single-page UI, three panels
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── .env            # Not committed
```

Prompts are isolated in `prompts.py` intentionally. Prompt tuning is the main variable for output quality, keeping it separate from logic means you can iterate on wording without touching application code.

---

## Local Setup

### Prerequisites

- Python 3.13.x
- Azure CLI (`az login` required)
- An Azure AI Foundry project with a deployed GPT-4.1 model
- Docker (optional, for container testing)

### Run with Python

```bash
# Clone and navigate to the folder
cd labfiles/foundry-chat/python/chat-app

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI endpoint and model deployment name

# Sign into Azure (for Entra ID auth)
az login

# Run
python app.py
```

Open `http://localhost:5000`.

### Run with Docker

```bash
docker build -t interview-coach .

docker run -p 5001:5000 \
  -e AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/openai/v1" \
  -e MODEL_DEPLOYMENT="gpt-4.1" \
  -e AZURE_API_KEY="your-api-key" \
  interview-coach
```

Open `http://localhost:5001`.

---

## Environment Variables

| Variable | Description |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint from your Foundry project home page |
| `MODEL_DEPLOYMENT` | Exact deployment name assigned to your model in Foundry |
| `AZURE_API_KEY` | API key (Docker/container use only, Entra ID preferred otherwise) |

---

## Auth

- **Local Python** - Uses `DefaultAzureCredential` via `az login`. No API key needed.
- **Docker local** - Uses `AZURE_API_KEY` environment variable. `DefaultAzureCredential` cannot access host `az login` session from inside a container.
- **Azure Container Apps** - Uses Managed Identity. No API keys stored anywhere.

---

## CLI Version

The app also runs as a terminal chat loop via `coach.py`, which was the original version built during the Microsoft AI Skills Fest exercise. It supports both text paste and PDF resume upload.

```bash
python coach.py
```

---

## Background

Built as part of the Microsoft AI Skills Fest (June 2026) exercise series on Azure AI Foundry, extended into a real-world tool. The base exercise covered the OpenAI Responses API, streaming, and `previous_response_id` context tracking. This project applies those patterns to a practical use case with additional engineering for token efficiency, PDF handling, and a web interface.