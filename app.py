# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from io import BytesIO
from pypdf import PdfReader, PdfWriter
import os, datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root_page():
    return FileResponse("static/index.html")

DATA_ROOT = "data"

@app.get("/api/grades")
async def get_grades():
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
        raise HTTPException(status_code=404, detail="Folder not found.")
    pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    pdfs.sort()
    return [{"filename": f} for f in pdfs]

class CompilePayload(BaseModel):
    grade: str
    files: list[str]
    filename: str | None = None

@app.post("/api/compile")
async def compile_pdfs(payload: CompilePayload):
    grade = payload.grade
    selected_files = payload.files or []
    folder = os.path.join(DATA_ROOT, grade)

    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="Target folder not found.")
    if not selected_files:
        raise HTTPException(status_code=400, detail="No selected files.")

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
        raise HTTPException(status_code=400, detail="No PDF files to merge.")

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # filename processing
    if payload.filename and payload.filename.strip():
        base_name = payload.filename.strip()
    else:
        base_name = f"{grade}_merged_{ts}"

    # extension check
    if base_name.lower().endswith('.pdf_'):
        base_name = base_name[:-5] + '.pdf'
    elif base_name.lower().endswith('_'):
        base_name = base_name[:-1] + '.pdf'
    elif not base_name.lower().endswith('.pdf'):
        base_name += '.pdf'

    # safe encoding for all browsers
    safe_name = base_name.encode('utf-8').decode('latin-1', 'ignore')
    headers = {"Content-Disposition": f"attachment; filename="{safe_name}""}

    return StreamingResponse(output, media_type="application/pdf", headers=headers)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
