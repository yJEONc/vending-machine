import os
import io
import tempfile
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from PyPDF2 import PdfMerger

app = Flask(__name__)
# 배포 전에 더 복잡한 랜덤 값으로 바꾸는 걸 추천
app.secret_key = "change-this-to-a-random-secret-key"

# 네가 만들어둔 구글 드라이브 폴더 ID
ROOT_FOLDER_ID = "18L1UqiyY6AmfTcPOFTdJZ6bYuCnHHGZ3"

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service():
    """service_account.json을 사용해서 Drive API v3 서비스 객체 생성"""
    creds = service_account.Credentials.from_service_account_file(
        "service_account.json", scopes=SCOPES
    )
    service = build("drive", "v3", credentials=creds)
    return service


def get_folder_name(service, folder_id):
    try:
        file = service.files().get(fileId=folder_id, fields="name").execute()
        return file.get("name", "폴더")
    except Exception:
        return "폴더"


@app.route("/")
def index():
    # 항상 루트 폴더 기준으로 시작
    return redirect(url_for("browse", folder_id=ROOT_FOLDER_ID))


@app.route("/folder/<folder_id>")
def browse(folder_id):
    service = get_drive_service()

    # 현재 폴더 이름
    folder_name = get_folder_name(service, folder_id)

    # 현재 폴더 안의 항목들 가져오기 (v3)
    q = f"'{folder_id}' in parents and trashed = false"
    result = service.files().list(q=q, fields="files(id, name, mimeType)").execute()
    items = result.get("files", [])

    folders = []
    pdf_files = []

    for item in items:
        mime = item.get("mimeType", "")
        if mime == "application/vnd.google-apps.folder":
            folders.append(item)
        else:
            name = item.get("name", "")
            if name.lower().endswith(".pdf"):
                pdf_files.append(item)

    return render_template(
        "folder.html",
        folder_id=folder_id,
        root_id=ROOT_FOLDER_ID,
        folder_name=folder_name,
        folders=folders,
        pdf_files=pdf_files,
    )


@app.route("/upload", methods=["POST"])
def upload():
    folder_id = request.form.get("folder_id")
    file = request.files.get("file")

    if not file or file.filename == "":
        flash("업로드할 파일을 선택하세요.")
        return redirect(url_for("browse", folder_id=folder_id))

    service = get_drive_service()

    # 업로드용 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    try:
        file_metadata = {"name": file.filename, "parents": [folder_id]}
        media = MediaFileUpload(tmp_path, mimetype="application/pdf")
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        flash(f"'{file.filename}' 업로드 완료")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return redirect(url_for("browse", folder_id=folder_id))


@app.route("/create_folder", methods=["POST"])
def create_folder():
    parent_id = request.form.get("folder_id")
    new_name = request.form.get("new_folder_name", "").strip()

    if not new_name:
        flash("폴더 이름을 입력하세요.")
        return redirect(url_for("browse", folder_id=parent_id))

    service = get_drive_service()

    folder_metadata = {
        "name": new_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }

    service.files().create(body=folder_metadata, fields="id").execute()
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

    service = get_drive_service()
    merger = PdfMerger()
    temp_paths = []

    try:
        # 선택한 각 파일을 다운로드해서 병합
        for file_id in selected_ids:
            request_drive = service.files().get_media(fileId=file_id)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp_path = tmp.name

            fh = open(tmp_path, "wb")
            downloader = MediaIoBaseDownload(fh, request_drive)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            fh.close()
            temp_paths.append(tmp_path)
            merger.append(tmp_path)

        # 병합 결과를 메모리에 저장
        out_stream = io.BytesIO()
        merger.write(out_stream)
        merger.close()
        out_stream.seek(0)

        # 병합된 파일을 드라이브에 업로드
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as merged_tmp:
            merged_tmp.write(out_stream.getvalue())
            merged_tmp_path = merged_tmp.name

        file_metadata = {"name": output_name, "parents": [folder_id]}
        media = MediaFileUpload(merged_tmp_path, mimetype="application/pdf")
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        if os.path.exists(merged_tmp_path):
            os.unlink(merged_tmp_path)

        flash(f"병합된 파일 '{output_name}' 이(가) 현재 폴더에 저장되었습니다.")

        # 동시에 브라우저로 다운로드도 제공
        out_stream.seek(0)
        return send_file(
            out_stream,
            as_attachment=True,
            download_name=output_name,
            mimetype="application/pdf",
        )

    finally:
        # 다운로드 받았던 임시 PDF들 삭제
        for p in temp_paths:
            if os.path.exists(p):
                os.unlink(p)


if __name__ == "__main__":
    app.run(debug=True)
