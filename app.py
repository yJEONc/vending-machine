from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfMerger
import os, urllib.parse

app = Flask(__name__)
DATA_FOLDER = "data"

@app.route("/")
def index():
    pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith(".pdf")]
    return render_template("index.html", pdf_files=pdf_files)

@app.route("/merge", methods=["POST"])
def merge_pdfs():
    selected_files = request.form.getlist("selected_files")
    output_filename = request.form.get("output_filename", "합쳐진파일")

    if not selected_files:
        return "선택된 파일이 없습니다.", 400

    merger = PdfMerger()
    for filename in selected_files:
        merger.append(os.path.join(DATA_FOLDER, filename))

    merged_path = os.path.join(DATA_FOLDER, f"{output_filename}.pdf")
    merger.write(merged_path)
    merger.close()

    encoded_name = urllib.parse.quote(f"{output_filename}.pdf")
    response = send_file(merged_path, as_attachment=True)
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_name}"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
