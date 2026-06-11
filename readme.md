# Microsoft AI Skills Fest 2026 - Azure AI Foundry

Projects built during Microsoft AI Skills Fest (June 2026), focused on Azure AI Foundry, the OpenAI Responses API, and AI agent development.

---

## Projects

### Interview Prep Coach
[`labfiles/foundry-chat/python/chat-app`](./labfiles/foundry-chat/python/chat-app)

<img width="1470" height="956" alt="Screenshot 2026-06-09 at 10 40 52 PM" src="https://github.com/user-attachments/assets/02329646-4f67-46a4-aa8b-8fc461d6218f" />
<img width="1470" height="956" alt="Screenshot 2026-06-09 at 10 40 21 PM" src="https://github.com/user-attachments/assets/b11632e2-d6a1-40a1-87fc-ff15c2cdfd73" />


An AI-powered mock interview coach that conducts realistic 6-turn interviews tailored to a specific job description and resume, then generates a structured debrief with actionable feedback. Built with Azure AI Foundry, OpenAI Responses API, Flask, and Docker.

Key engineering decisions: token-efficient context compression, stateful conversation via `previous_response_id`, streaming responses, and PDF resume parsing.

---

## Exercises

### Foundry Chat (`labfiles/foundry-chat/python/chat-app`)

Sequential exercises building up a generative AI chat client:

| Exercise | What it covers |
|---|---|
| `chat-app.py` | ChatCompletions API, then migrated to Responses API |
| Conversation tracking | `previous_response_id` for stateful multi-turn chat |
| Streaming | Incremental response rendering via `stream=True` |
| `chat-async.py` | Async client using `AsyncOpenAI` and `azure.identity.aio` |

---

## Stack

- Azure AI Foundry
- OpenAI Python SDK (Responses API)
- Azure Identity (`DefaultAzureCredential`)
- Flask
- Docker
- Python 3.13

---

## Setup

Each project has its own README with setup instructions. All projects require:

- An active Azure subscription with an AI Foundry project
- A deployed GPT-4.1 model
- Python 3.13.x
- Azure CLI (`az login`)

---

## Background

Built as part of the [Microsoft AI Skills Fest 2026](https://aka.ms/AISkillsFest), extended with original projects applying the patterns covered in the exercises to real-world use cases.
