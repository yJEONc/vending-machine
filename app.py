from flask import Flask, render_template, request, send_file
import os
from PyPDF2 import PdfMerger
import io

app = Flask(__name__)

DATA_FOLDER = "data"

@app.route('/')
def index():
    subfolders = [f for f in os.listdir(DATA_FOLDER)
                  if os.path.isdir(os.path.join(DATA_FOLDER, f))]
    return render_template('index.html', subfolders=subfolders)

@app.route('/files', methods=['GET'])
def files():
    folder = request.args.get('folder')
    folder_path = os.path.join(DATA_FOLDER, folder)
    if not os.path.exists(folder_path):
        return f"폴더 '{folder}'를 찾을 수 없습니다.", 404

    pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
    return render_template('files.html', folder=folder, pdf_files=pdf_files)

@app.route('/merge', methods=['POST'])
def merge():
    folder = request.form.get('folder')
    selected_files = request.form.getlist('files')
    output_filename = request.form.get('output_filename', 'merged.pdf')

    if not selected_files:
        return "파일을 하나 이상 선택하세요."

    merger = PdfMerger()
    folder_path = os.path.join(DATA_FOLDER, folder)

    for file in selected_files:
        merger.append(os.path.join(folder_path, file))

    merged_pdf = io.BytesIO()
    merger.write(merged_pdf)
    merger.close()
    merged_pdf.seek(0)

    return send_file(
        merged_pdf,
        as_attachment=True,
        download_name=output_filename,
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)
