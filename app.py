from flask import Flask, render_template, request, send_file
import os
from PyPDF2 import PdfMerger
import urllib.parse

app = Flask(__name__, static_folder='static', template_folder='templates')

DATA_FOLDER = "data/grade1"
OUTPUT_FOLDER = "data"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/merge', methods=['POST'])
def merge_pdfs():
    filename = request.form['filename'].strip()
    if not filename:
        return "❌ 파일 이름을 입력하세요.", 400

    safe_filename = urllib.parse.quote(filename)
    merger = PdfMerger()

    pdf_files = sorted([
        f for f in os.listdir(DATA_FOLDER)
        if f.lower().endswith(".pdf")
    ])

    if not pdf_files:
        return "❌ PDF 파일이 없습니다.", 400

    for pdf in pdf_files:
        merger.append(os.path.join(DATA_FOLDER, pdf))

    output_path = os.path.join(OUTPUT_FOLDER, f"{filename}.pdf")
    merger.write(output_path)
    merger.close()

    return send_file(output_path, as_attachment=True, download_name=f"{filename}.pdf")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
