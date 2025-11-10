import os, re, json, urllib.parse
from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfMerger

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")

@app.route("/")
def index():
    grades = [d for d in os.listdir(DATA_FOLDER) if os.path.isdir(os.path.join(DATA_FOLDER, d))]
    return render_template("index.html", grades=grades, pdf_files=None, selected_grade=None)

@app.route("/grade/<grade>")
def show_grade(grade):
    grade_path = os.path.join(DATA_FOLDER, grade)
    if not os.path.exists(grade_path):
        return "해당 학년 폴더가 존재하지 않습니다.", 404

    def natural_key(filename):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r'([0-9]+)', filename)]
    pdf_files = sorted(
        [f for f in os.listdir(grade_path) if f.lower().endswith(".pdf")],
        key=natural_key
    )
    return render_template("index.html", grades=None, pdf_files=pdf_files, selected_grade=grade)

@app.route("/merge", methods=["POST"])
def merge_pdfs():
    selected_grade = request.form.get("selected_grade")
    selected_files = request.form.getlist("selected_files")
    file_order = request.form.get("file_order", "[]")
    output_filename = request.form.get("output_filename", "합쳐진파일")

    try:
        order_list = json.loads(file_order)
    except json.JSONDecodeError:
        order_list = selected_files

    ordered_files = [f for f in order_list if f in selected_files]

    if not selected_grade or not ordered_files:
        return "선택된 파일이 없습니다.", 400

    grade_path = os.path.join(DATA_FOLDER, selected_grade)
    merger = PdfMerger()
    for filename in ordered_files:
        merger.append(os.path.join(grade_path, filename))

    merged_path = os.path.join(grade_path, f"{output_filename}.pdf")
    merger.write(merged_path)
    merger.close()

    encoded_name = urllib.parse.quote(f"{output_filename}.pdf")
    response = send_file(merged_path, as_attachment=True)
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_name}"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
