from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from io import BytesIO
from pypdf import PdfReader, PdfWriter
import os, datetime

app = FastAPI()

# ✅ 정적 파일은 /static으로 mount (더 이상 "/"에 mount하지 않음)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ 루트로 들어오면 index.html 직접 반환
@app.get("/")
def root_page():
    return FileResponse("static/index.html")

DATA_ROOT = "data"

@app.get("/api/grades")
async def get_grades():
    # data 폴더 하위의 디렉터리들을 학년 목록으로 노출
    if not os.path.exists(DATA_ROOT):
        return []
    grades = []
    for name in os.listdir(DATA_ROOT):
        path = os.path.join(DATA_ROOT, name)
        if os.path.isdir(path):
            grades.append({"id": name, "label": name})
    return grades

@app.get("/api/files")
async def list_files(grade: str):
    folder = os.path.join(DATA_ROOT, grade)
    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    pdfs.sort()
    return [{"filename": f} for f in pdfs]

class CompilePayload(BaseModel):
    grade: str
    files: list[str]

@app.post("/api/compile")
async def compile_pdfs(payload: CompilePayload):
    grade = payload.grade
    selected_files = payload.files or []
    folder = os.path.join(DATA_ROOT, grade)

    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="해당 학년 폴더가 없습니다.")
    if not selected_files:
        raise HTTPException(status_code=400, detail="선택된 파일이 없습니다.")

    writer = PdfWriter()
    added = 0
    for fname in selected_files:
        path = os.path.join(folder, fname)
        if not os.path.exists(path):
            continue
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
        added += 1

    if added == 0:
        raise HTTPException(status_code=400, detail="병합할 PDF를 찾을 수 없습니다.")

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{grade}_merged_{ts}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(output, media_type="application/pdf", headers=headers)
