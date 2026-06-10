# app.py

import os
import uuid
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from dotenv import load_dotenv
from context import build_client, compress_context, SessionState
from prompts import INTERVIEW_PROMPT, DEBRIEF_PROMPT

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
MODEL = os.getenv("MODEL_DEPLOYMENT")

app = Flask(__name__)

# In-memory session store. Each key is a session_id, value is a SessionState.
sessions = {}
client = build_client(ENDPOINT)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start_session():
    """
    Receives resume + JD, runs compression, returns session_id.
    Raw resume and JD are not stored after compression.
    """
    data = request.get_json()
    resume = data.get("resume", "").strip()
    jd = data.get("jd", "").strip()

    if not resume or not jd:
        return jsonify({"error": "Resume and job description are required."}), 400

    compressed = compress_context(client, MODEL, resume, jd)
    session_id = str(uuid.uuid4())
    sessions[session_id] = SessionState(compressed_context=compressed, max_turns=6)

    return jsonify({"session_id": session_id})


@app.route("/first-question", methods=["POST"])
def first_question():
    """
    Streams the opening question. No previous_response_id yet.
    """
    data = request.get_json()
    session_id = data.get("session_id")
    session = sessions.get(session_id)

    if not session:
        return jsonify({"error": "Invalid session."}), 404

    system_prompt = INTERVIEW_PROMPT.format(
        compressed_context=session.compressed_context
    )

    def generate():
        stream = client.responses.create(
            model=MODEL,
            instructions=system_prompt,
            input="Begin the interview with your first question.",
            max_output_tokens=150,
            stream=True
        )
        question_text = ""
        for event in stream:
            if event.type == "response.output_text.delta":
                question_text += event.delta
                yield event.delta
            elif event.type == "response.completed":
                session.last_response_id = event.response.id
                session.last_question = question_text

    return Response(stream_with_context(generate()), mimetype="text/plain")


@app.route("/answer", methods=["POST"])
def answer():
    """
    Receives candidate answer, streams the next question.
    Logs the completed turn before streaming the next one.
    """
    data = request.get_json()
    session_id = data.get("session_id")
    answer_text = data.get("answer", "").strip()
    session = sessions.get(session_id)

    if not session:
        return jsonify({"error": "Invalid session."}), 404

    if session.is_complete():
        return jsonify({"done": True})

    system_prompt = INTERVIEW_PROMPT.format(
        compressed_context=session.compressed_context
    )

    # Log the turn that just completed before making the next call
    session.log_turn(session.last_question, answer_text)

    def generate():
        stream = client.responses.create(
            model=MODEL,
            instructions=system_prompt,
            input=answer_text,
            previous_response_id=session.last_response_id,
            max_output_tokens=150,
            stream=True
        )
        next_question = ""
        for event in stream:
            if event.type == "response.output_text.delta":
                next_question += event.delta
                yield event.delta
            elif event.type == "response.completed":
                session.last_response_id = event.response.id
                session.last_question = next_question

    if session.is_complete():
        return jsonify({"done": True})

    return Response(stream_with_context(generate()), mimetype="text/plain")


@app.route("/debrief", methods=["POST"])
def debrief():
    """
    Streams the debrief using only the compact turn log.
    Called after the interview is complete.
    """
    data = request.get_json()
    session_id = data.get("session_id")
    session = sessions.get(session_id)

    if not session:
        return jsonify({"error": "Invalid session."}), 404

    if not session.turn_log:
        return jsonify({"error": "No turns logged."}), 400

    debrief_prompt = DEBRIEF_PROMPT.format(
        compressed_context=session.compressed_context,
        turn_log=session.formatted_turn_log()
    )

    def generate():
        stream = client.responses.create(
            model=MODEL,
            instructions=debrief_prompt,
            input="Provide the debrief now.",
            max_output_tokens=400,
            stream=True
        )
        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta

    return Response(stream_with_context(generate()), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)
