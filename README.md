
# 시험범위 PDF 합치기 (FastAPI 버전)

## 로컬 실행
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```
브라우저에서 http://localhost:8000 을 열면 UI가 보입니다.

## 사용법
1) `files_index.json`에서 학년/시험범위/파일경로를 원하는 대로 수정하세요.
2) 실제 PDF를 `data/gradeX/` 폴더에 넣어주세요.
3) 페이지에서 학년 선택 → 시험범위 체크 → "선택한 범위 PDF 합치기" 클릭 → 병합 PDF 다운로드.

## 배포 아이디어
- **Render**: New Web Service → Repo 연결 → Build Command 없음 → Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- **Railway** / **Fly.io**: Dockerfile 사용
- **Vercel**: Python Server (Edge 아님)로는 약간 설정이 필요하니 Render/Fly 추천

## 주의
- pypdf는 일부 PDF 요소(주석/링크/북마크)를 완벽히 유지하지 못할 수 있습니다. 필요시 `pikepdf`로 교체 고려.
- 대용량 병합이 잦다면, 조합 캐시(해시 키로 저장)나 임시파일 기반 스트리밍으로 개선하세요.
