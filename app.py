from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfMerger
import os
import urllib.parse

app = Flask(__name__)
UPLOAD_FOLDER = "data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/merge", methods=["POST"])
def merge_pdfs():
    files = request.files.getlist("pdf_files")
    output_filename = request.form.get("output_filename", "합쳐진파일")

    if not files:
        return "파일이 선택되지 않았습니다.", 400

    merger = PdfMerger()
    for file in files:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        merger.append(filepath)

    merged_path = os.path.join(UPLOAD_FOLDER, f"{output_filename}.pdf")
    merger.write(merged_path)
    merger.close()

    encoded_name = urllib.parse.quote(f"{output_filename}.pdf")
    response = send_file(merged_path, as_attachment=True)
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_name}"

    for file in files:
        os.remove(os.path.join(UPLOAD_FOLDER, file.filename))
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
