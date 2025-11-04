
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from io import BytesIO
from pypdf import PdfReader, PdfWriter
import os, datetime

app = FastAPI()
app.mount("/", StaticFiles(directory="static", html=True), name="static")

DATA_ROOT = "data"

@app.get("/api/grades")
async def get_grades():
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
    selected_files = payload.files
    folder = os.path.join(DATA_ROOT, grade)

    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="해당 학년 폴더가 없습니다.")

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
