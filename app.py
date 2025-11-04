
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from io import BytesIO
from pypdf import PdfReader, PdfWriter
import json, os, datetime

app = FastAPI()

# Static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Load index
with open("files_index.json", "r", encoding="utf-8") as f:
    INDEX = json.load(f)

@app.get("/api/grades")
async def get_grades():
    return INDEX["grades"]

@app.get("/api/scopes")
async def get_scopes(grade: str):
    return INDEX["scopes"].get(grade, [])

class CompilePayload(BaseModel):
    grade: str
    scopes: list[str]

@app.post("/api/compile")
async def compile_pdfs(payload: CompilePayload):
    grade = payload.grade
    scopes = payload.scopes or []
    if not grade or not scopes:
        raise HTTPException(status_code=400, detail="grade와 scopes가 필요합니다.")

    candidates = [f for f in INDEX["files"] if f["grade"] == grade and f["scope"] in scopes]
    scope_order = {s["id"]: i for i, s in enumerate(INDEX["scopes"].get(grade, []))}
    candidates.sort(key=lambda x: (scope_order.get(x["scope"], 9999), x.get("order", 9999), x["path"]))

    if not candidates:
        raise HTTPException(status_code=404, detail="해당 조건에 맞는 파일이 없습니다.")

    writer = PdfWriter()
    for item in candidates:
        path = item["path"]
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {path}")
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    ts = datetime.datetime.now().strftime("%Y%m%d")
    scopes_part = "-".join(scopes)
    filename = f"{grade}_{scopes_part}_{ts}.pdf"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return StreamingResponse(output, media_type="application/pdf", headers=headers)
