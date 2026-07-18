"""
招聘结构化面试 · 云端合并后端（零依赖业务，仅 FastAPI）
部署后获得一个 URL，前端「云端同步」填写该地址 + 房间密钥即可：
  - 面试官提交评分 → POST /api/score → 自动按 (面试官,候选人) 去重合并
  - HR「从云端刷新」→ GET /api/state → 拉取最新合并结果
  - HR「上传配置到云端」→ POST /api/state → 同步岗位/面试官/候选人
数据按房间密钥隔离，存于 cloud_data/<room>.json。
"""
import os, json
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="HR Interview Cloud Sync")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 前端托管在 GitHub Pages，需跨域
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = os.environ.get("CLOUD_DIR", "cloud_data")
os.makedirs(BASE, exist_ok=True)

def _path(room): return os.path.join(BASE, room + ".json")
def _load(room):
    p = _path(room)
    if os.path.exists(p):
        try: return json.load(open(p, encoding="utf-8"))
        except Exception: pass
    return {"positions": [], "interviewers": [], "candidates": [], "archived": [], "scores": []}
def _save(room, st):
    json.dump(st, open(_path(room), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

@app.get("/api/state")
def get_state(room: str):
    if not room: raise HTTPException(400, "room required")
    return {"state": _load(room)}

@app.post("/api/state")
async def post_state(req: Request):
    b = await req.json()
    room = b.get("room")
    if not room: raise HTTPException(400, "room required")
    _save(room, b.get("state", {}))
    return {"ok": True}

@app.post("/api/score")
async def post_score(req: Request):
    b = await req.json()
    room = b.get("room")
    score = b.get("score")
    if not room or not score: raise HTTPException(400, "room & score required")
    st = _load(room)
    st.setdefault("scores", [])
    cid, iid = score.get("candidate_id"), score.get("interviewer_id")
    ex = next((s for s in st["scores"] if s.get("interviewer_id") == iid and s.get("candidate_id") == cid), None)
    if ex: ex.update(score)
    else: st["scores"].append(score)
    _save(room, st)
    return {"ok": True}

@app.get("/")
def root():
    return {"service": "hr-interview-cloud", "status": "ok"}
