import os
os.environ["FLOWMUSIC_PROVIDER"]="mock"
from fastapi.testclient import TestClient
from app.main import app,TOKEN
def test_mock_idempotency():
 with TestClient(app) as c:
  h={"X-Local-Token":TOKEN.read_text()}
  request={"request_id":"test-001","prompt":"Natal piano instrumental"}
  assert c.post("/v1/music/jobs",json=request).status_code==401
  a=c.post("/v1/music/jobs",json=request,headers=h)
  assert a.status_code==202
  assert a.json()["status"]=="completed"
  assert c.post("/v1/music/jobs",json=request,headers=h).json()["job_id"]==a.json()["job_id"]
  assert c.post("/v1/music/jobs",json={**request,"prompt":"Outra"},headers=h).status_code==409
  assert c.get("/v1/music/jobs/"+a.json()["job_id"]+"/artifacts",headers=h).status_code==200
