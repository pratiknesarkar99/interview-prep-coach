# context.py

import os
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from prompts import COMPRESS_PROMPT


def build_client(endpoint: str) -> OpenAI:
    api_key = os.getenv("AZURE_API_KEY")

    if api_key:
        # API key auth, used in Docker local testing
        return OpenAI(
            base_url=endpoint,
            api_key=api_key
        )
    else:
        # Entra ID auth, used when az login is active
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://ai.azure.com/.default"
        )
        return OpenAI(
            base_url=endpoint,
            api_key=token_provider
        )

def compress_context(client: OpenAI, model: str, resume: str, jd: str) -> str:
    """
    Single call at session start. Raw resume and JD never sent again after this.
    Output capped at 300 tokens to control cost.
    """
    response = client.responses.create(
        model=model,
        instructions=COMPRESS_PROMPT,
        input=f"RESUME:\n{resume}\n\nJOB DESCRIPTION:\n{jd}",
        max_output_tokens=300
    )
    return response.output_text


class SessionState:
    """
    Tracks everything needed across turns.
    Deliberately avoids storing full message history.
    Turn log entries are truncated at logging time, not at call time,
    so the debrief token cost is predictable.
    """

    def __init__(self, compressed_context: str, max_turns: int = 6):
        self.compressed_context = compressed_context
        self.max_turns = max_turns
        self.turn_count = 0
        self.turn_log = []
        self.last_response_id = None
        self.last_question = ""

    def log_turn(self, question: str, answer: str):
        self.turn_count += 1
        # Truncated here deliberately, controls debrief input size
        self.turn_log.append(
            f"Turn {self.turn_count} | Q: {question[:80]} | A: {answer[:120]}"
        )
        self.last_question = question

    def is_complete(self) -> bool:
        return self.turn_count >= self.max_turns

    def formatted_turn_log(self) -> str:
        return "\n".join(self.turn_log)