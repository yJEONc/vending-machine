import os
import io
import tempfile
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from PyPDF2 import PdfMerger

app = Flask(__name__)
# 👉 배포 전에 더 복잡한 랜덤 값으로 바꾸는 걸 추천
app.secret_key = "change-this-to-a-random-secret-key"

# 네가 만들어둔 구글 드라이브 폴더 ID
ROOT_FOLDER_ID = "18L1UqiyY6AmfTcPOFTdJZ6bYuCnHHGZ3"

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive():
    """service_account.json 을 사용해서 Google Drive 객체 생성"""
    gauth = GoogleAuth()
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'service_account.json',
        scopes=SCOPES
    )
    drive = GoogleDrive(gauth)
    return drive

def get_folder_title(drive, folder_id):
    if not folder_id:
        return "Root"
    try:
        f = drive.CreateFile({'id': folder_id})
        f.FetchMetadata()
        return f.get('title', '폴더')
    except Exception:
        return "폴더"

@app.route("/")
def index():
    # 항상 루트 폴더 기준으로 시작
    return redirect(url_for("browse", folder_id=ROOT_FOLDER_ID))

@app.route("/folder/<folder_id>")
def browse(folder_id):
    drive = get_drive()

    # 현재 폴더 이름
    folder_name = get_folder_title(drive, folder_id)

    # 현재 폴더 안의 항목들 가져오기
    file_list = drive.ListFile({
        'q': f"'{{folder_id}}' in parents and trashed=false",
        'orderBy': 'folder, title'
    }).GetList()

    folders = []
    pdf_files = []

    for f in file_list:
        mime = f.get('mimeType', '')
        if mime == 'application/vnd.google-apps.folder':
            folders.append(f)
        else:
            # PDF만 대상으로
            title = f.get('title', '')
            if title.lower().endswith('.pdf'):
                pdf_files.append(f)

    return render_template(
        "folder.html",
        folder_id=folder_id,
        root_id=ROOT_FOLDER_ID,
        folder_name=folder_name,
        folders=folders,
        pdf_files=pdf_files
    )

@app.route("/upload", methods=["POST"])
def upload():
    folder_id = request.form.get("folder_id")
    file = request.files.get("file")

    if not file:
        flash("업로드할 파일을 선택하세요.")
        return redirect(url_for("browse", folder_id=folder_id))

    drive = get_drive()
    new_file = drive.CreateFile({
        'title': file.filename,
        'parents': [{'id': folder_id}]
    })

    # 임시 파일에 저장 후 업로드 (바이너리 안전)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    new_file.SetContentFile(tmp_path)
    new_file.Upload()

    os.unlink(tmp_path)

    flash(f"'{file.filename}' 업로드 완료")
    return redirect(url_for("browse", folder_id=folder_id))

@app.route("/create_folder", methods=["POST"])
def create_folder():
    parent_id = request.form.get("folder_id")
    new_name = request.form.get("new_folder_name", "").strip()

    if not new_name:
        flash("폴더 이름을 입력하세요.")
        return redirect(url_for("browse", folder_id=parent_id))

    drive = get_drive()
    folder_meta = {
        'title': new_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': parent_id}]
    }
    new_folder = drive.CreateFile(folder_meta)
    new_folder.Upload()

    flash(f"'{new_name}' 폴더 생성 완료")
    return redirect(url_for("browse", folder_id=parent_id))

@app.route("/merge", methods=["POST"])
def merge():
    folder_id = request.form.get("folder_id")
    selected_ids = request.form.getlist("file_ids")
    output_name = request.form.get("output_name", "merged").strip()

    if not selected_ids:
        flash("합칠 PDF 파일을 하나 이상 선택하세요.")
        return redirect(url_for("browse", folder_id=folder_id))

    if not output_name:
        output_name = "merged"

    if not output_name.lower().endswith(".pdf"):
        output_name += ".pdf"

    drive = get_drive()
    merger = PdfMerger()

    # 선택된 각 파일을 임시파일로 저장 후 병합
    temp_paths = []
    try:
        for fid in selected_ids:
            f = drive.CreateFile({'id': fid})
            # 각 파일을 개별 임시 파일로 저장
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            tmp_path = tmp.name
            tmp.close()
            f.GetContentFile(tmp_path)
            temp_paths.append(tmp_path)
            merger.append(tmp_path)

        # 병합 결과를 메모리에 저장
        out_stream = io.BytesIO()
        merger.write(out_stream)
        merger.close()
        out_stream.seek(0)

        # 병합된 파일을 구글 드라이브에 업로드
        merged_file = drive.CreateFile({
            'title': output_name,
            'parents': [{'id': folder_id}]
        })

        # 업로드용 임시파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as merged_tmp:
            merged_tmp.write(out_stream.getvalue())
            merged_tmp_path = merged_tmp.name

        merged_file.SetContentFile(merged_tmp_path)
        merged_file.Upload()

        os.unlink(merged_tmp_path)

        flash(f"병합된 파일 '{output_name}' 이(가) 현재 폴더에 저장되었습니다.")

        # 동시에 브라우저로도 다운로드 제공
        out_stream.seek(0)
        return send_file(
            out_stream,
            as_attachment=True,
            download_name=output_name,
            mimetype='application/pdf'
        )

    finally:
        # 임시 파일들 정리
        for p in temp_paths:
            if os.path.exists(p):
                os.unlink(p)

if __name__ == "__main__":
    # 로컬 테스트용
    app.run(debug=True)
