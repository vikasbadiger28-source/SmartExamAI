from flask import Flask, render_template, request, jsonify
from groq import Groq
import fitz
import re
import os

app = Flask(__name__)

# ---------- GROQ CLIENT ----------
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

# ---------- PDF TEXT EXTRACTION ----------
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

    prompt = f"""
You are a professional university exam paper setter.

IMPORTANT RULES:
- Generate ONLY questions.
- Do NOT give answers.
- Do NOT give explanations.
- Mention difficulty as ({difficulty})

Generate exactly:
{mcq_count} MCQs
{two_mark_count} 2-mark questions

Content:
{notes_text}
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating questions: {str(e)}"


# ---------- MAIN ROUTE ----------
@app.route("/", methods=["GET", "POST"])
def index():

    questions = ""
    question_list = []

    if request.method == "POST":

        pdf_file = request.files.get("file")

        if pdf_file:

            mcq_count = int(request.form.get("mcqCount", 0))
            two_mark_count = int(request.form.get("twoMarkCount", 0))
            difficulty = request.form.get("difficulty")

            notes_text = extract_text_from_pdf(pdf_file)

            questions = generate_questions(
                notes_text,
                mcq_count,
                two_mark_count,
                difficulty
            )

            blocks = re.split(r'\n(?=\d+\.)', questions)
            question_list = [b.strip() for b in blocks if b.strip()]

    return render_template(
        "index.html",
        questions=questions,
        question_list=question_list
    )


# ---------- ANSWER EVALUATION ----------
@app.route("/evaluate", methods=["POST"])
def evaluate():

    data = request.json
    questions = data["questions"]
    answers = data["answers"]

    prompt = f"""
You are an exam evaluator.

Evaluate the student answers.

Provide:
- Marks for each question
- Total score
- Short feedback

Questions:
{questions}

Student Answers:
{answers}
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        result = response.choices[0].message.content

    except Exception as e:

        result = f"Error evaluating answers: {str(e)}"

    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)