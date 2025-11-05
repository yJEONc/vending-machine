=from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from urllib.parse import quote
import os, datetime

app = FastAPI()

# 정적 파일 서빙 (index.html 포함)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root_page():
    return FileResponse("static/index.html")

# 데이터 루트
DATA_ROOT = "data"

# 학년 목록 불러오기
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

# 특정 학년의 PDF 파일 목록
@app.get("/api/files")
async def list_files(grade: str):
    folder = os.path.join(DATA_ROOT, grade)
    if not os.path.exists(folder):
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    pdfs.sort()
    return [{"filename": f} for f in pdfs]

# 요청 바디 모델 정의
class CompilePayload(BaseModel):
    grade: str
    files: list[str]
    filename: str | None = None

# PDF 병합 및 다운로드 처리
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

    # 병합 결과 메모리에 저장
    output = BytesIO()
    writer.write(output)
    output.seek(0)

    # 파일명 처리
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = (payload.filename or f"{grade}_merged_{ts}").strip()

    # 언더바, 확장자 중복, 누락 처리
    if base_name.lower().endswith(".pdf_"):
        base_name = base_name[:-5] + ".pdf"
    elif base_name.lower().endswith("_"):
        base_name = base_name[:-1] + ".pdf"
    elif not base_name.lower().endswith(".pdf"):
        base_name += ".pdf"

    # ✅ 한글·공백 자동 인코딩
    # Content-Disposition 헤더의 filename*, RFC5987 방식 인코딩
    encoded_name = quote(base_name)
    content_disposition = (
        f"attachment; filename*=UTF-8''{encoded_name}"
    )

    headers = {"Content-Disposition": content_disposition}

    return StreamingResponse(output, media_type="application/pdf", headers=headers)

if __name__ == "__main__":
    import uvicorn, os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

