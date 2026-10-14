import os,sqlite3,json,uuid,hashlib,secrets,subprocess,threading
from pathlib import Path
from contextlib import asynccontextmanager, contextmanager
from fastapi import FastAPI,Header,HTTPException,Depends
from pydantic import BaseModel,Field
ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.getenv("FLOWMUSIC_DATA_DIR", str(ROOT/"data")))
DB=DATA/"jobs.db"
TOKEN=DATA/"local-token.txt"
MUTEX=threading.Lock()
def get_provider() -> str:
    return os.getenv("FLOWMUSIC_PROVIDER", "mock")
def secure_token_file(path: Path) -> None:
    if os.name == "nt":
        user = os.getenv("USERNAME")
        if user:
            try:
                subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:(R,W)"], capture_output=True, check=False)
            except Exception:
                pass
    else:
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
class MusicRequest(BaseModel):
 request_id:str=Field(min_length=3,max_length=120,pattern=r"^[a-zA-Z0-9._:-]+$")
 prompt:str=Field(min_length=3,max_length=4000)
 model:str="Lyria 3.5"
 title:str|None=None
 lyrics:str|None=None
 instrumental:bool=False
 duration_seconds:int=Field(default=120,ge=60,le=600)
 output_format:str=Field(default="wav",pattern="^(wav|m4a|mp3)$")
@contextmanager
def db():
 c=sqlite3.connect(DB,timeout=15)
 c.row_factory=sqlite3.Row
 c.execute("PRAGMA journal_mode=WAL")
 try:
  with c:
   yield c
 finally:
  c.close()
def bootstrap():
 DATA.mkdir(parents=True,exist_ok=True);(DATA/"output").mkdir(exist_ok=True)
 if not TOKEN.exists():
  try:
   with TOKEN.open("x",encoding="utf-8") as f:f.write(secrets.token_urlsafe(48))
   secure_token_file(TOKEN)
  except FileExistsError:pass
 with db() as c:
  c.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY,request_id TEXT UNIQUE,hash TEXT,payload TEXT,state TEXT,result TEXT,error TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
  c.execute("UPDATE jobs SET state='needs_review',error='interrupted; remote acceptance unknown' WHERE state IN ('submitting','generating','downloading')")
@asynccontextmanager
async def life(app):
 bootstrap();yield
app=FastAPI(title="Evydencia FlowMusic Local",version="0.1.0",lifespan=life)
def auth(x_local_token:str|None=Header(default=None)):
 if not x_local_token or not secrets.compare_digest(x_local_token,TOKEN.read_text(encoding="utf-8")):raise HTTPException(401,"Local token required")
def result(r):
 return {"job_id":r["id"],"request_id":r["request_id"],"status":r["state"],"result":json.loads(r["result"]) if r["result"] else None,"error":r["error"]}
@app.get("/health")
def health():return {"ok":True}
@app.get("/v1/music/status",dependencies=[Depends(auth)])
def status():return {"provider":get_provider(),"live_enabled":False,"note":"Live generation disabled until manual Windows and terms validation"}
@app.post("/v1/music/jobs",status_code=202,dependencies=[Depends(auth)])
def create(req:MusicRequest):
 payload=json.dumps(req.model_dump(),ensure_ascii=False,sort_keys=True);digest=hashlib.sha256(payload.encode()).hexdigest()
 with MUTEX:
  with db() as c:
   r=c.execute("SELECT * FROM jobs WHERE request_id=?",(req.request_id,)).fetchone()
   if r:
    if r["hash"]!=digest:raise HTTPException(409,"request_id already used")
    return result(r)
   uid=str(uuid.uuid4())
   c.execute("INSERT INTO jobs(id,request_id,hash,payload,state) VALUES(?,?,?,?,?)",(uid,req.request_id,digest,payload,"queued"))
   c.commit()
 if get_provider()=="mock":
  artifact=DATA/"output"/(uid+".json");artifact.write_text(json.dumps({"mock":True,"prompt":req.prompt},ensure_ascii=False),encoding="utf-8")
  value={"mock":True,"artifacts":[{"path":str(artifact),"sha256":hashlib.sha256(artifact.read_bytes()).hexdigest()}]}
  with db() as c:c.execute("UPDATE jobs SET state='completed',result=? WHERE id=?",(json.dumps(value),uid));c.commit()
 else:
  with db() as c:c.execute("UPDATE jobs SET state='auth_required',error='Provider not activated' WHERE id=?",(uid,));c.commit()
 return get_job(uid)
@app.get("/v1/music/jobs/{job_id}",dependencies=[Depends(auth)])
def get_job(job_id:str):
 with db() as c:r=c.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
 if not r:raise HTTPException(404,"Unknown job")
 return result(r)
@app.get("/v1/music/jobs/{job_id}/artifacts",dependencies=[Depends(auth)])
def artifacts(job_id:str):
 r=get_job(job_id)
 if r["status"]!="completed":raise HTTPException(409,"Not completed")
 return r["result"]
@app.get("/v1/music/credits",dependencies=[Depends(auth)])
def credits():return {"available":False,"reason":"Manual account diagnostic required; no secret-bearing remote calls from server"}
