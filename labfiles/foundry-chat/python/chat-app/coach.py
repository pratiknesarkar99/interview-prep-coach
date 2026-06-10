# coach.py

import os
from dotenv import load_dotenv
from pypdf import PdfReader
from context import build_client, compress_context, SessionState
from prompts import INTERVIEW_PROMPT, DEBRIEF_PROMPT

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
MODEL = os.getenv("MODEL_DEPLOYMENT")


def get_multiline_input(prompt: str) -> str:
    """Collect multi-line input until user enters a blank line."""
    print(prompt)
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


def load_resume() -> str:
    """
    Gives the user two options: paste text or provide a PDF path.
    PDF text is extracted locally before any API call, so no extra token cost.
    """
    print("\nResume input options:")
    print("  1. Paste resume text")
    print("  2. Provide path to a PDF file")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "2":
        path = input("Enter the full path to your PDF: ").strip()
        try:
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
            if not text.strip():
                print("Could not extract text from PDF. Falling back to paste mode.")
                return get_multiline_input("\nPaste your resume text (blank line to finish):")
            print("PDF loaded successfully.")
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}. Falling back to paste mode.")
            return get_multiline_input("\nPaste your resume text (blank line to finish):")
    else:
        return get_multiline_input("\nPaste your resume text (blank line to finish):")


def run_interview(client, session: SessionState):
    """
    Interview loop using streaming + previous_response_id.
    Identical pattern to chat-app.py from the lab.
    Output capped at 150 tokens per turn since questions should be concise.
    """
    system_prompt = INTERVIEW_PROMPT.format(
        compressed_context=session.compressed_context
    )

    print("\n--- Interview starting. Type your answer and press Enter twice to submit. ---")
    print("--- Type 'quit' and press Enter twice to end early. ---\n")

    # First question, no previous_response_id yet
    stream = client.responses.create(
        model=MODEL,
        instructions=system_prompt,
        input="Begin the interview with your first question.",
        max_output_tokens=150,
        stream=True
    )

    first_question = ""
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
            first_question += event.delta
        elif event.type == "response.completed":
            session.last_response_id = event.response.id
    print("\n")

    session.last_question = first_question

    # Conversation loop
    while not session.is_complete():
        answer = get_multiline_input("Your answer:")

        if answer.strip().lower() == "quit":
            print("\nSession ended early.")
            break

        stream = client.responses.create(
            model=MODEL,
            instructions=system_prompt,
            input=answer,
            previous_response_id=session.last_response_id,
            max_output_tokens=150,
            stream=True
        )

        next_question = ""
        for event in stream:
            if event.type == "response.output_text.delta":
                print(event.delta, end="", flush=True)
                next_question += event.delta
            elif event.type == "response.completed":
                session.last_response_id = event.response.id
        print("\n")

        # Log the completed turn before moving to the next
        session.log_turn(session.last_question, answer)
        session.last_question = next_question

    print(f"\n--- Interview complete ({session.turn_count}/{session.max_turns} turns) ---\n")


def run_debrief(client, session: SessionState):
    """
    Single call using only the compact turn log, not the full response chain.
    This is what keeps debrief cost predictable regardless of session length.
    """
    if not session.turn_log:
        print("No turns logged. Skipping debrief.")
        return

    print("Generating your debrief...\n")

    debrief_prompt = DEBRIEF_PROMPT.format(
        compressed_context=session.compressed_context,
        turn_log=session.formatted_turn_log()
    )

    stream = client.responses.create(
        model=MODEL,
        instructions=debrief_prompt,
        input="Provide the debrief now.",
        max_output_tokens=400,
        stream=True
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
        elif event.type == "response.completed":
            pass
    print("\n")


def main():
    print("=== Interview Prep Coach ===")

    client = build_client(ENDPOINT)

    resume = load_resume()
    jd = get_multiline_input("\nPaste the job description (blank line to finish):")

    print("\nCompressing context... (one API call, then raw text is discarded)")
    compressed = compress_context(client, MODEL, resume, jd)
    print("Done.\n")

    session = SessionState(compressed_context=compressed, max_turns=6)

    run_interview(client, session)
    run_debrief(client, session)


if __name__ == "__main__":
    main()