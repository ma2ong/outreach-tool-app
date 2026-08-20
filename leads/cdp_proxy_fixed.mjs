#!/usr/bin/env node
import http from "node:http";
import { URL } from "node:url";

const PORT = Number(process.env.CDP_PROXY_PORT || 3456);
const CHROME_PORT = Number(process.env.CHROME_DEBUG_PORT || 9222);
let ws;
let nextId = 1;
const pending = new Map();
const sessions = new Map();

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let raw = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => { raw += chunk; });
      res.on("end", () => {
        try { resolve(JSON.parse(raw)); } catch (err) { reject(err); }
      });
    }).on("error", reject);
  });
}

async function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === 1)) return;
  const version = await getJson(`http://127.0.0.1:${CHROME_PORT}/json/version`);
  const wsUrl = version.webSocketDebuggerUrl;
  if (!wsUrl) throw new Error("Chrome webSocketDebuggerUrl missing");

  ws = new WebSocket(wsUrl);
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (!msg.id || !pending.has(msg.id)) return;
    const item = pending.get(msg.id);
    pending.delete(msg.id);
    clearTimeout(item.timer);
    item.resolve(msg);
  });
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", (event) => reject(new Error(event.message || "ws error")), { once: true });
  });
}

async function send(method, params = {}, sessionId = null, timeout = 30000) {
  await connect();
  const id = nextId++;
  const payload = { id, method, params };
  if (sessionId) payload.sessionId = sessionId;
  const promise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`CDP timeout: ${method}`));
    }, timeout);
    pending.set(id, { resolve, reject, timer });
  });
  ws.send(JSON.stringify(payload));
  const msg = await promise;
  if (msg.error) throw new Error(msg.error.message || JSON.stringify(msg.error));
  return msg;
}

async function session(targetId) {
  if (sessions.has(targetId)) return sessions.get(targetId);
  const resp = await send("Target.attachToTarget", { targetId, flatten: true });
  const sid = resp.result.sessionId;
  sessions.set(targetId, sid);
  await send("Page.enable", {}, sid);
  await send("Runtime.enable", {}, sid);
  return sid;
}

async function waitReady(sid, ms = 15000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const resp = await send("Runtime.evaluate", {
      expression: "document.readyState",
      returnByValue: true,
    }, sid);
    if (resp.result.result.value === "complete") return;
    await new Promise(r => setTimeout(r, 500));
  }
}

function readBody(req) {
  return new Promise((resolve) => {
    let body = "";
    req.setEncoding("utf8");
    req.on("data", chunk => { body += chunk; });
    req.on("end", () => resolve(body));
  });
}

function reply(res, obj, status = 200) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(obj));
}

const server = http.createServer(async (req, res) => {
  try {
    const parsed = new URL(req.url, `http://127.0.0.1:${PORT}`);
    const q = parsed.searchParams;
    const path = parsed.pathname;

    if (path === "/json/version") {
      return reply(res, await getJson(`http://127.0.0.1:${CHROME_PORT}/json/version`));
    }
    if (path === "/targets") {
      const resp = await send("Target.getTargets");
      return reply(res, resp.result.targetInfos.filter(t => t.type === "page"));
    }
    if (path === "/new") {
      const url = q.get("url") || "about:blank";
      const resp = await send("Target.createTarget", { url, background: false });
      const sid = await session(resp.result.targetId);
      await waitReady(sid).catch(() => {});
      return reply(res, { targetId: resp.result.targetId });
    }
    if (path === "/close") {
      const targetId = q.get("target");
      sessions.delete(targetId);
      const resp = await send("Target.closeTarget", { targetId });
      return reply(res, resp.result || { ok: true });
    }
    if (path === "/info") {
      const sid = await session(q.get("target"));
      const resp = await send("Runtime.evaluate", {
        expression: "JSON.stringify({title:document.title,url:location.href,ready:document.readyState})",
        returnByValue: true,
      }, sid);
      return reply(res, JSON.parse(resp.result.result.value || "{}"));
    }
    if (path === "/eval") {
      const body = await readBody(req);
      const sid = await session(q.get("target"));
      const resp = await send("Runtime.evaluate", {
        expression: body || q.get("expr") || "document.title",
        returnByValue: true,
        awaitPromise: true,
      }, sid);
      return reply(res, { value: resp.result.result.value });
    }
    if (path === "/type") {
      const text = await readBody(req);
      const sid = await session(q.get("target"));
      await send("Input.insertText", { text }, sid);
      return reply(res, { ok: true, len: text.length });
    }
    if (path === "/setFiles") {
      const body = JSON.parse(await readBody(req));
      const sid = await session(q.get("target"));
      await send("DOM.enable", {}, sid);
      const doc = await send("DOM.getDocument", {}, sid);
      const node = await send("DOM.querySelector", {
        nodeId: doc.result.root.nodeId,
        selector: body.selector,
      }, sid);
      if (!node.result.nodeId) return reply(res, { success: false, error: "selector_not_found" }, 404);
      await send("DOM.setFileInputFiles", { nodeId: node.result.nodeId, files: body.files }, sid);
      return reply(res, { success: true });
    }
    return reply(res, { error: "not_found" }, 404);
  } catch (err) {
    return reply(res, { error: err.message || String(err) }, 500);
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`fixed CDP proxy listening on http://127.0.0.1:${PORT}`);
});
