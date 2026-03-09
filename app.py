from flask import Flask, render_template, request, jsonify
from groq import Groq
import fitz
import re
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------- PDF TEXT ----------
def extract_text_from_pdf(pdf_file):

    text = ""

    try:
        pdf = fitz.open(stream=pdf_file.read(), filetype="pdf")

        for page in pdf:
            text += page.get_text("text")

        pdf.close()

    except Exception as e:
        print("PDF Error:", e)

    return text[:2000]


# ---------- QUESTION GENERATION ----------
def generate_questions(notes_text, mcq_count, two_mark_count, difficulty):

    total_questions = mcq_count + two_mark_count

    prompt = f"""
Generate EXACTLY {total_questions} questions from the notes.

Rules:
- First {mcq_count} must be MCQ questions
- Each MCQ must contain 4 options (A, B, C, D)
- Remaining {two_mark_count} must be short answer questions
- Do NOT generate more than {total_questions}

Format exactly like this:

1. Question text
A) option
B) option
C) option
D) option

2. Question text

3. Question text

Difficulty: {difficulty}

Notes:
{notes_text}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    return response.choices[0].message.content


# ---------- MAIN ----------
@app.route("/", methods=["GET", "POST"])
def index():

    questions = ""
    question_list = []

    if request.method == "POST":

        pdf_file = request.files.get("file")

        if pdf_file:

            mcq_count = int(request.form.get("mcqCount", 2))
            two_mark_count = int(request.form.get("twoMarkCount", 2))
            difficulty = request.form.get("difficulty", "Medium")

            total_questions = mcq_count + two_mark_count

            notes_text = extract_text_from_pdf(pdf_file)

            questions = generate_questions(
                notes_text,
                mcq_count,
                two_mark_count,
                difficulty
            )

            blocks = re.findall(r"\d+\.\s.*?(?=\n\d+\.|\Z)", questions, re.S)

            question_list = [b.strip() for b in blocks if b.strip()]

            # ✅ LIMIT QUESTIONS (prevents AI giving extra)
            question_list = question_list[:total_questions]

    return render_template(
        "index.html",
        questions=questions,
        question_list=question_list
    )


# ---------- EVALUATION ----------
@app.route("/evaluate", methods=["POST"])
def evaluate():

    data = request.json
    questions = data.get("questions", [])
    answers = data.get("answers", [])

    qa_text = ""

    for i in range(len(questions)):

        student_answer = answers[i] if answers[i] else "Blank"

        qa_text += f"""
Question {i+1}:
{questions[i]}

Student Answer:
{student_answer}
"""

    prompt = f"""
Evaluate the answers.

Return ONLY JSON.

Format:

{{
"results":[
{{
"question":1,
"student_answer":"...",
"correct_answer":"...",
"correct":true
}}
],
"percentage":80
}}

Questions and answers:

{qa_text}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    result_text = response.choices[0].message.content

    try:
        json_match = re.search(r"\{.*\}", result_text, re.S)
        result_json = json.loads(json_match.group())

    except:
        result_json = {
            "results": [],
            "percentage": 0
        }

    return jsonify(result_json)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)