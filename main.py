import hashlib
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

EMAIL = "24f3000906@ds.study.iitm.ac.in".strip().lower()

app = FastAPI()

TOOLS = [{
    "name": "solve_challenge",
    "description": "Returns the exam response for the current request's challenge header.",
    "inputSchema": {"type": "object", "properties": {}},
}]


def ok(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def err(rid, code, msg):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}}


def handle(msg, headers):
    method = msg.get("method")
    rid = msg.get("id")

    # Notifications have no id and get no response
    if rid is None:
        return None

    if method == "initialize":
        version = (msg.get("params") or {}).get("protocolVersion", "2025-03-26")
        return ok(rid, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-server", "version": "1.0.0"},
        })
    if method == "ping":
        return ok(rid, {})
    if method == "tools/list":
        return ok(rid, {"tools": TOOLS})
    if method == "tools/call":
        name = (msg.get("params") or {}).get("name")
        if name != "solve_challenge":
            return err(rid, -32602, f"Unknown tool: {name}")
        challenge = headers.get("x-exam-challenge", "")
        text = hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]
        return ok(rid, {"content": [{"type": "text", "text": text}], "isError": False})
    return err(rid, -32601, f"Method not found: {method}")


@app.post("/")
@app.post("/mcp")
async def mcp(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(err(None, -32700, "Parse error"), status_code=400)

    if isinstance(body, list):
        out = [r for r in (handle(m, request.headers) for m in body) if r]
        return JSONResponse(out) if out else Response(status_code=202)

    resp = handle(body, request.headers)
    if resp is None:
        return Response(status_code=202)
    return JSONResponse(resp)


@app.get("/health")
async def health():
    return {"status": "ok"}
