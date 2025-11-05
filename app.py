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
    r = []
    for name in os.listdir(DATA_ROOT):
        p = os.path.join(DATA_ROOT, name)
        if os.path.isdir(p):
            r.append({"id": name, "label": name})
    return r

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
    folder = os.path.join(DATA_ROOT, payload.grade)
    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="Target folder not found.")
    selected = payload.files or []
    if not selected:
        raise HTTPException(status_code=400, detail="No selected files.")

    w = PdfWriter()
    added = 0
    for fname in selected:
        path = os.path.join(folder, fname)
        if not os.path.exists(path):
            continue
        r = PdfReader(path)
        for pg in r.pages:
            w.add_page(pg)
        added += 1
    if added == 0:
        raise HTTPException(status_code=400, detail="No PDF files to merge.")

    buf = BytesIO()
    w.write(buf)
    buf.seek(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if payload.filename and payload.filename.strip():
        base = payload.filename.strip()
    else:
        base = f"{payload.grade}_merged_{ts}"
    if base.lower().endswith('.pdf_'):
        base = base[:-5] + '.pdf'
    elif base.lower().endswith('_'):
        base = base[:-1] + '.pdf'
    elif not base.lower().endswith('.pdf'):
        base += '.pdf'

    safe = base.encode('utf-8').decode('latin-1', 'ignore')
    headers = {"Content-Disposition": f"attachment; filename="{safe}""}
    return StreamingResponse(buf, media_type="application/pdf", headers=headers)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
