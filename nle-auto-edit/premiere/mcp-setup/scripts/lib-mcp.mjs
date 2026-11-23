// premiere-pro-mcp 서버를 stdio로 띄워 도구를 여러 번 부를 수 있게 해 주는 작은 클라이언트.
// ensure-premiere.mjs가 쓴다. 한 번만 부를 때는 mcp-call.mjs를 쓴다.

import { spawn, execSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

export function resolveServer() {
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

// 도구 결과의 text를 JSON으로 풀고, { ok, data, text, error } 형태로 돌려준다.
// 서버는 data를 바로 주기도 하고 { ok, tool, data } 로 감싸 주기도 해서 둘 다 받는다.
function unwrap(res) {
  if (res.error) return { ok: false, error: res.error.message ?? JSON.stringify(res.error), text: "" };
  const text = (res.result?.content ?? []).filter((c) => c.type === "text").map((c) => c.text).join("\n");
  let parsed = null;
  try {
    parsed = JSON.parse(text);
  } catch {
    /* 오류 문장 등 JSON이 아닌 결과 */
  }
  const data = parsed && typeof parsed === "object" && "data" in parsed && "tool" in parsed ? parsed.data : parsed;
  const ok = !res.result?.isError && !(parsed && parsed.ok === false);
  return { ok, data, text, error: ok ? null : text };
}

export async function connect({ timeoutMs = 60000 } = {}) {
  const server = resolveServer();
  const child = spawn(server.cmd, server.args, { stdio: ["pipe", "pipe", "pipe"], shell: server.shell });
  let stderr = "";
  child.stderr.on("data", (d) => (stderr += d.toString()));
  const started = new Promise((resolve, reject) => {
    child.on("error", reject);
    child.on("spawn", resolve);
  });
  await started;

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

  const request = (method, params, t = timeoutMs) => {
    const id = nextId++;
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`timeout ${t}ms: ${method}${params?.name ? ` ${params.name}` : ""}`));
      }, t);
      pending.set(id, (msg) => {
        clearTimeout(timer);
        resolve(msg);
      });
    });
  };

  const init = await request("initialize", {
    protocolVersion: "2025-06-18",
    capabilities: {},
    clientInfo: { name: "premiere-mcp-setup-skill", version: "1.1.0" },
  });
  if (init.error) throw new Error(`initialize 실패: ${JSON.stringify(init.error)}`);
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized", params: {} }) + "\n");

  return {
    serverInfo: init.result?.serverInfo ?? {},
    async call(name, args = {}, t) {
      try {
        return unwrap(await request("tools/call", { name, arguments: args }, t));
      } catch (e) {
        return { ok: false, timeout: /^timeout/.test(e.message), error: e.message, text: "", data: null };
      }
    },
    stderr: () => stderr,
    close() {
      child.kill();
    },
  };
}
