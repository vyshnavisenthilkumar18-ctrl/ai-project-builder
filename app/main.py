from __future__ import annotations
import io, json, os, re, secrets, time, uuid, zipfile, base64
from typing import Any
from urllib.parse import urlencode
import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.middleware.sessions import SessionMiddleware

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "AI Project Builder"
    secret_key: str = "development-only-change-me"
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://localhost:8000/api/github/callback"
    github_scopes: str = "repo"
    max_upload_mb: int = 10

settings = Settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax",
                   https_only=settings.cookie_secure, max_age=60*60*8)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                   allow_credentials=True, allow_methods=["GET","POST","OPTIONS"],
                   allow_headers=["Content-Type"])
PROJECTS: dict[str, dict[str, Any]] = {}

SAFE_NAME = re.compile(r"^[A-Za-z0-9._/-]+$")
BLOCKED_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".pytest_cache"}
BLOCKED_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "credentials.json"}

def clean_path(path: str) -> str:
    path = path.replace("\\", "/").strip("/")
    parts = path.split("/")
    if not path or not SAFE_NAME.fullmatch(path) or any(p in ("", ".", "..") for p in parts):
        raise ValueError("Unsafe file path")
    if any(p in BLOCKED_PARTS for p in parts) or parts[-1] in BLOCKED_NAMES or parts[-1].startswith(".env."):
        raise ValueError("Sensitive or generated path is not allowed")
    return path

def require_project(project_id: str):
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found or backend restarted.")
    return project

class GenerateRequest(BaseModel):
    topic: str = Field(min_length=10, max_length=30000)
    language: str = "Python"
    framework: str = "React + Vite / FastAPI"
    analysis: str | None = None

class PublishRequest(BaseModel):
    project_id: str
    mode: str = Field(pattern="^(create|existing)$")
    repo_name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=350)
    private: bool = True
    branch: str = Field(default="main", min_length=1, max_length=100)
    confirm: bool = False

@app.get("/api/health")
async def health():
    return {"status":"ok", "ai_configured":bool(settings.ai_api_key),
            "github_configured":bool(settings.github_client_id and settings.github_client_secret)}

async def extract_upload(upload: UploadFile) -> str:
    data = await upload.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Upload exceeds {settings.max_upload_mb} MB limit.")
    name = (upload.filename or "").lower()
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")[:30000]
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages)[:30000]
        except Exception as e:
            raise HTTPException(400, f"Could not read PDF: {e}")
    if name.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)[:30000]
        except Exception as e:
            raise HTTPException(400, f"Could not read DOCX: {e}")
    if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(io.BytesIO(data))
            return pytesseract.image_to_string(img)[:30000]
        except Exception:
            raise HTTPException(400, "Image OCR failed. Install Tesseract OCR and pytesseract, or upload TXT/PDF/DOCX.")
    raise HTTPException(415, "Supported formats: PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP.")

@app.post("/api/projects/analyze")
async def analyze(request: Request, topic: str = Form(default=""), file: UploadFile | None = File(default=None)):
    uploaded_text = await extract_upload(file) if file else ""
    combined = "\n\n".join(x for x in [topic.strip(), uploaded_text.strip()] if x)
    if len(combined) < 10:
        raise HTTPException(400, "Enter a project topic or upload a specification with readable text.")
    # Analysis endpoint validates and summarizes the input without pretending an AI call occurred.
    result = {"topic": combined[:30000], "characters": len(combined),
              "detected_sections": [s for s in ["objective","features","requirements","technology","security","testing"]
                                    if s in combined.lower()],
              "message": "Specification extracted and ready for generation."}
    request.session["last_topic"] = combined[:30000]
    return result

SYSTEM_PROMPT = """You are a senior software engineer generating a runnable project repository.
Return ONLY a JSON object: {"project_name":"kebab-case-name","summary":"...","files":[{"path":"relative/path","content":"complete file content"}]}.
Include a useful frontend and backend appropriate to the requested stack, README.md, .gitignore, .env.example, dependency manifests, and basic tests where appropriate.
Never include real secrets, access tokens, private keys, or actual .env files. Use placeholders in .env.example.
Keep every path relative, normalized, and safe. Do not use markdown fences. Avoid huge binaries and node_modules/build outputs.
Generate coherent code, not pseudocode or TODO-only stubs. Be honest in README about required external credentials.
"""

async def generate_with_ai(topic: str, language: str, framework: str):
    if not settings.ai_api_key:
        raise HTTPException(503, "AI provider is not configured. Set AI_API_KEY in backend/.env.")
    payload = {"model": settings.ai_model, "temperature": 0.2,
               "messages":[{"role":"system","content":SYSTEM_PROMPT},
                           {"role":"user","content":f"Project specification:\n{topic}\n\nPreferred language: {language}\nFramework: {framework}\nGenerate a complete practical codebase."}]}
    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(settings.ai_base_url.rstrip("/") + "/chat/completions",
                                     headers={"Authorization":f"Bearer {settings.ai_api_key}"},
                                     json=payload)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, f"AI provider returned HTTP {e.response.status_code}. Check model/key/quota.")
        except Exception as e:
            raise HTTPException(502, f"AI provider request failed: {type(e).__name__}.")
    try:
        match = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(match.group(0) if match else raw)
        files = {}
        for item in data.get("files", []):
            path = clean_path(str(item.get("path", "")))
            content = item.get("content", "")
            if not isinstance(content, str):
                raise ValueError("File content must be text")
            if len(content) > 1_000_000:
                raise ValueError("Generated file exceeds 1 MB")
            files[path] = content
        if not files:
            raise ValueError("No files returned")
        for required, content in {
            "README.md": "# Generated Project\n\nReview and test before use.\n",
            ".gitignore": ".env\n.venv/\nnode_modules/\n__pycache__/\ndist/\n",
            ".env.example": "# Add required environment variables here\n"
        }.items():
            files.setdefault(required, content)
        return {"name": re.sub(r"[^a-z0-9-]", "-", data.get("project_name","generated-project").lower()).strip("-")[:80] or "generated-project",
                "summary": str(data.get("summary","Generated codebase"))[:2000], "files": files}
    except Exception as e:
        raise HTTPException(502, f"AI response was not valid project JSON: {e}")

@app.post("/api/projects/generate")
async def generate(body: GenerateRequest, request: Request):
    result = await generate_with_ai(body.topic, body.language, body.framework)
    project_id = str(uuid.uuid4())
    PROJECTS[project_id] = {"id":project_id, **result, "topic":body.topic, "created_at":int(time.time())}
    request.session["last_project_id"] = project_id
    return {"project_id":project_id, "project_name":result["name"], "summary":result["summary"],
            "files":[{"path":p,"size":len(c.encode("utf-8"))} for p,c in sorted(result["files"].items())]}

@app.get("/api/projects/{project_id}/files")
async def list_files(project_id: str):
    p = require_project(project_id)
    return {"project_id":project_id,"project_name":p["name"],"summary":p["summary"],
            "files":[{"path":k,"content":v,"size":len(v.encode("utf-8"))} for k,v in sorted(p["files"].items())]}

@app.get("/api/projects/{project_id}/download")
async def download_project(project_id: str):
    p = require_project(project_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in p["files"].items():
            try: safe = clean_path(path)
            except ValueError: continue
            zf.writestr(f'{p["name"]}/{safe}', content)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/zip",
        headers={"Content-Disposition":f'attachment; filename="{p["name"]}.zip"'})

def github_token(request: Request) -> str:
    token = request.session.get("github_access_token")
    if not token:
        raise HTTPException(401, "Connect GitHub first.")
    return token

@app.get("/api/github/login")
async def github_login(request: Request):
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(503, "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.")
    state = secrets.token_urlsafe(32)
    request.session["github_oauth_state"] = state
    params = {"client_id":settings.github_client_id,"redirect_uri":settings.github_callback_url,
              "scope":settings.github_scopes,"state":state}
    return RedirectResponse("https://github.com/login/oauth/authorize?" + urlencode(params))

@app.get("/api/github/callback")
async def github_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(settings.frontend_origin + "/?github=denied")
    expected = request.session.pop("github_oauth_state", None)
    if not expected or not secrets.compare_digest(expected, state):
        raise HTTPException(400, "Invalid OAuth state.")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("https://github.com/login/oauth/access_token",
            headers={"Accept":"application/json"},
            json={"client_id":settings.github_client_id,"client_secret":settings.github_client_secret,"code":code,
                  "redirect_uri":settings.github_callback_url})
        if r.status_code != 200 or not r.json().get("access_token"):
            raise HTTPException(502, "GitHub OAuth token exchange failed.")
        request.session["github_access_token"] = r.json()["access_token"]
    return RedirectResponse(settings.frontend_origin + "/?github=connected")

async def gh_request(method: str, path: str, token: str, **kwargs):
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.request(method, "https://api.github.com" + path,
            headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json",
                     "X-GitHub-Api-Version":"2022-11-28"}, **kwargs)
    if r.status_code == 401: raise HTTPException(401, "GitHub authorization expired. Reconnect GitHub.")
    if r.status_code == 403: raise HTTPException(403, "GitHub permission/rate limit error. Check OAuth scopes and rate limits.")
    if r.status_code == 404: raise HTTPException(404, "GitHub resource not found or not accessible.")
    if r.status_code >= 400:
        raise HTTPException(502, f"GitHub API error ({r.status_code}): {r.text[:500]}")
    return r.json() if r.content else {}

@app.get("/api/github/status")
async def github_status(request: Request):
    return {"connected":bool(request.session.get("github_access_token")),
            "configured":bool(settings.github_client_id and settings.github_client_secret)}

@app.get("/api/github/repositories")
async def github_repositories(request: Request):
    token = github_token(request)
    return await gh_request("GET","/user/repos?per_page=100&sort=updated",token)

@app.post("/api/github/publish")
async def publish(body: PublishRequest, request: Request):
    if not body.confirm:
        raise HTTPException(400, "Explicit publish confirmation is required.")
    p = require_project(body.project_id)
    token = github_token(request)
    repo_name = body.repo_name.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", repo_name) or repo_name in (".",".."):
        raise HTTPException(400, "Invalid repository name.")
    branch = body.branch.strip()
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", branch) or ".." in branch.split("/"):
        raise HTTPException(400, "Invalid branch name.")
    if body.mode == "create":
        repo = await gh_request("POST","/user/repos",token,json={"name":repo_name,"description":body.description,
            "private":body.private,"auto_init":True})
    else:
        me = await gh_request("GET","/user",token)
        repo = await gh_request("GET",f"/repos/{me['login']}/{repo_name}",token)
    owner = repo["owner"]["login"]
    # Resolve branch and parent commit. New repositories may need a short retry for initial branch availability.
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"https://api.github.com/repos/{owner}/{repo_name}/git/ref/heads/{branch}",
            headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json"})
        if r.status_code == 404 and body.mode == "create":
            # Repository is initialized on its default branch; if requested branch differs, use default ref.
            default_branch = repo.get("default_branch","main")
            branch = default_branch
            r = await client.get(f"https://api.github.com/repos/{owner}/{repo_name}/git/ref/heads/{branch}",
                headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json"})
        if r.status_code >= 400:
            raise HTTPException(409, "Target branch does not exist or cannot be read. Create it first or select an existing branch.")
        ref_data = r.json()
    parent_sha = ref_data["object"]["sha"]
    commit_data = await gh_request("GET",f"/repos/{owner}/{repo_name}/git/commits/{parent_sha}",token)
    tree_items = []
    skipped = []
    for path, content in p["files"].items():
        try: safe = clean_path(path)
        except ValueError:
            skipped.append(path); continue
        tree_items.append({"path":safe,"mode":"100644","type":"blob","content":content})
    if not tree_items: raise HTTPException(400,"No publishable files.")
    tree = await gh_request("POST",f"/repos/{owner}/{repo_name}/git/trees",token,
                            json={"base_tree":commit_data["tree"]["sha"],"tree":tree_items})
    commit = await gh_request("POST",f"/repos/{owner}/{repo_name}/git/commits",token,
        json={"message":f"Publish generated project: {p['name']}","tree":tree["sha"],"parents":[parent_sha]})
    await gh_request("PATCH",f"/repos/{owner}/{repo_name}/git/refs/heads/{branch}",token,
                     json={"sha":commit["sha"],"force":False})
    return {"success":True,"repository_url":repo["html_url"],"commit_url":commit.get("html_url"),
            "branch":branch,"published_files":len(tree_items),"skipped_files":skipped}
