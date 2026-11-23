#!/usr/bin/env node
// premiere-pro-mcp 서버를 stdio로 직접 띄워 도구 하나를 호출한다.
// Claude Code에 막 등록한 MCP 도구는 새 세션부터 보이므로, 설치 직후 같은 세션에서 연결을 확인할 때 쓴다.
//
// 사용법:
//   node mcp-call.mjs <tool> ['{"json":"args"}'] [--timeout=60000]
//   node mcp-call.mjs --list [검색어]          도구 목록(이름) 출력
// 서버 실행 파일은 PREMIERE_MCP_CMD 환경 변수로 바꿀 수 있다.
// 기본값: 전역 npm 루트의 premiere-pro-mcp/dist/index.js 를 지금 실행 중인 node로 띄운다
// (Windows에서 npm 전역 명령이 .cmd라 직접 spawn이 안 되는 문제를 피한다).

import { spawn, execSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const argv = process.argv.slice(2);
const flags = Object.fromEntries(
  argv.filter((a) => a.startsWith("--") && a.includes("=")).map((a) => a.slice(2).split("=")),
);
const positional = argv.filter((a) => !a.startsWith("--"));
const listMode = argv.includes("--list");
const timeoutMs = Number(flags.timeout ?? 60000);

function resolveServer() {
  if (process.env.PREMIERE_MCP_CMD) {
    return { cmd: process.env.PREMIERE_MCP_CMD, args: [], shell: process.platform === "win32" };
  }
  try {
    const root = execSync("npm root -g", { encoding: "utf8", shell: true }).trim();
    const entry = path.join(root, "premiere-pro-mcp", "dist", "index.js");
    if (existsSync(entry)) return { cmd: process.execPath, args: [entry], shell: false };
  } catch {
    /* npm이 없으면 아래 기본값 */
  }
  return { cmd: "premiere-pro-mcp", args: [], shell: process.platform === "win32" };
}

const server = resolveServer();
const child = spawn(server.cmd, server.args, { stdio: ["pipe", "pipe", "pipe"], shell: server.shell });
let stderr = "";
child.stderr.on("data", (d) => (stderr += d.toString()));
child.on("error", (e) => {
  console.error(`서버 실행 실패: ${e.message} (cmd=${server.cmd})`);
  process.exit(2);
});

let buf = "";
const pending = new Map();
let nextId = 1;
child.stdout.on("data", (d) => {
  buf += d.toString();
  let i;
  while ((i = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, i).trim();
    buf = buf.slice(i + 1);
    if (!line) continue;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      continue;
    }
    if (msg.id != null && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  }
});

function request(method, params) {
  const id = nextId++;
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  return new Promise((resolve, reject) => {
    pending.set(id, resolve);
    setTimeout(() => reject(new Error(`timeout ${timeoutMs}ms: ${method}`)), timeoutMs);
  });
}
const notify = (method, params) =>
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n");

let exitCode = 0;
try {
  const init = await request("initialize", {
    protocolVersion: "2025-06-18",
    capabilities: {},
    clientInfo: { name: "premiere-mcp-setup-skill", version: "1.0.0" },
  });
  if (init.error) throw new Error(`initialize 실패: ${JSON.stringify(init.error)}`);
  const info = init.result?.serverInfo ?? {};
  console.error(`[server] ${info.name ?? "?"} ${info.version ?? "?"} (protocol ${init.result?.protocolVersion})`);
  notify("notifications/initialized", {});

  if (listMode) {
    const query = (positional[0] ?? "").toLowerCase();
    const names = [];
    let cursor;
    do {
      const res = await request("tools/list", cursor ? { cursor } : {});
      for (const t of res.result?.tools ?? []) names.push(t.name);
      cursor = res.result?.nextCursor;
    } while (cursor);
    const shown = query ? names.filter((n) => n.toLowerCase().includes(query)) : names;
    console.log(`tools: ${names.length}${query ? ` (match "${query}": ${shown.length})` : ""}`);
    console.log(shown.join("\n"));
  } else {
    const tool = positional[0] ?? "verify_premiere_connection";
    const args = positional[1] ? JSON.parse(positional[1]) : {};
    const res = await request("tools/call", { name: tool, arguments: args });
    if (res.error) {
      console.log(JSON.stringify(res.error, null, 2));
      exitCode = 1;
    }
    for (const c of res.result?.content ?? []) console.log(c.type === "text" ? c.text : JSON.stringify(c));
    if (res.result?.isError) exitCode = 1;
  }
} catch (e) {
  console.error(`실패: ${e.message}`);
  if (stderr.trim()) console.error(`[server stderr]\n${stderr.trim().slice(-2000)}`);
  exitCode = 1;
} finally {
  child.kill();
  process.exit(exitCode);
}
