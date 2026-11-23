#!/usr/bin/env node
// premiere-pro-mcp 설치·연결 전후 상태를 읽기 전용으로 점검한다. 아무것도 바꾸지 않는다.
// 사용법: node preflight.mjs [--json]
// macOS와 Windows 11(Premiere 2027, 2026-11-22)에서 검증됨.

import { execSync } from "node:child_process";
import { existsSync, readdirSync, statSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const isMac = process.platform === "darwin";
const isWin = process.platform === "win32";
const sh = (cmd, timeout = 20000) => {
  try {
    return execSync(cmd, { encoding: "utf8", shell: true, timeout, stdio: ["ignore", "pipe", "pipe"] }).trim();
  } catch {
    return null;
  }
};
const nonAscii = (s) => /[^\x00-\x7F]/.test(s ?? "");
const r = { platform: process.platform, checks: {} };

// Node
const [maj, min] = process.versions.node.split(".").map(Number);
r.checks.node = { version: process.versions.node, ok: maj > 20 || (maj === 20 && min >= 19) };

// premiere-pro-mcp 설치 상태
const lsJson = sh("npm ls -g premiere-pro-mcp --depth=0 --json");
let installed = null;
try {
  installed = JSON.parse(lsJson ?? "{}").dependencies?.["premiere-pro-mcp"]?.version ?? null;
} catch {}
r.checks.package = {
  installed,
  latest: sh("npm view premiere-pro-mcp version", 30000),
  repository: sh("npm view premiere-pro-mcp repository.url", 30000),
};

// CEP 커넥터
const cepRoot = isMac
  ? path.join(os.homedir(), "Library/Application Support/Adobe/CEP/extensions")
  : path.join(process.env.APPDATA ?? "", "Adobe/CEP/extensions");
const cepDir = path.join(cepRoot, "MCPBridgeCEP");
const cep = { dir: cepDir, installed: existsSync(cepDir) };
if (cep.installed) {
  cep.installedAt = statSync(cepDir).mtime.toISOString();
  const manifest = path.join(cepDir, "CSXS/manifest.xml");
  if (existsSync(manifest)) {
    const xml = readFileSync(manifest, "utf8");
    cep.bundleVersion = xml.match(/ExtensionBundleVersion="([^"]+)"/)?.[1] ?? null;
    cep.hostRange = xml.match(/<Host Name="PPRO" Version="([^"]+)"/)?.[1] ?? null;
  }
  // 서명된 패키지(MCPBridgeCEP.zxp)를 풀어 설치하면 META-INF/signatures.xml이 있다.
  // 서명된 커넥터는 PlayerDebugMode 없이도 로드된다(2026-11-22 Windows 11 + Premiere 2027 실측).
  cep.signed = existsSync(path.join(cepDir, "META-INF/signatures.xml"));
}
r.checks.cepConnector = cep;

// PlayerDebugMode (서명 없는 CEP 확장 허용)
const debug = {};
for (let n = 9; n <= 14; n++) {
  const v = isMac
    ? sh(`defaults read com.adobe.CSXS.${n} PlayerDebugMode`)
    : isWin
      ? sh(`reg query HKCU\\Software\\Adobe\\CSXS.${n} /v PlayerDebugMode`)?.match(/REG_SZ\s+(\S+)/)?.[1] ?? null
      : null;
  debug[`CSXS.${n}`] = v;
}
r.checks.playerDebugMode = debug;

// Premiere 설치본
const premiere = [];
if (isMac) {
  for (const d of readdirSync("/Applications").filter((n) => n.startsWith("Adobe Premiere Pro"))) {
    const dir = path.join("/Applications", d);
    for (const app of readdirSync(dir).filter((n) => n.endsWith(".app") && n.startsWith("Adobe Premiere Pro"))) {
      const plist = path.join(dir, app, "Contents/Info.plist");
      const ver = sh(`defaults read "${plist}" CFBundleShortVersionString`);
      const bundleId = sh(`defaults read "${plist}" CFBundleIdentifier`);
      const plug = sh(
        `defaults read "${path.join(dir, app, "Contents/Frameworks/PlugPlug.framework/Resources/Info.plist")}" CFBundleShortVersionString`,
      );
      premiere.push({ app: path.join(dir, app), version: ver, bundleId, cepVersion: plug });
    }
  }
} else if (isWin) {
  const base = "C:\\Program Files\\Adobe";
  if (existsSync(base)) {
    for (const d of readdirSync(base).filter((n) => n.startsWith("Adobe Premiere Pro"))) {
      const exe = path.join(base, d, "Adobe Premiere Pro.exe");
      const ver = existsSync(exe)
        ? sh(`powershell -NoProfile -Command "(Get-Item -LiteralPath '${exe}').VersionInfo.ProductVersion"`)
        : null;
      premiere.push({ dir: path.join(base, d), version: ver });
    }
  }
}
r.checks.premiereInstalls = premiere;

// Premiere 실행 여부와 시작 시각 → 커넥터 설치 후 재시작이 필요한지
let running = null;
if (isMac) {
  // 앱 이름에 연도가 붙는다(예: "Adobe Premiere Pro 2027.app/Contents/MacOS/Adobe Premiere Pro 2027").
  // crashpad_handler 같은 보조 프로세스는 MacOS/ 뒤 실행 파일 이름이 달라 걸러진다.
  const ps = sh(
    `ps -axo pid=,lstart=,command= | grep -E "Adobe Premiere Pro[^/]*\\.app/Contents/MacOS/Adobe Premiere Pro[^/]*$" | grep -v grep`,
  );
  if (ps) {
    const m = ps.split("\n")[0].trim().match(/^(\d+)\s+(\w{3}\s+\w{3}\s+\d+\s+[\d:]+\s+\d{4})\s+(.*)$/);
    if (m) running = { pid: Number(m[1]), startedAt: new Date(m[2]).toISOString(), command: m[3] };
  }
} else if (isWin) {
  // Windows PowerShell 5.1의 ConvertTo-Json은 DateTime을 "/Date(ms)/"로 내보내 new Date()가 못 읽는다
  // (그래서 예전에는 Premiere가 켜져 있어도 항상 "실행 중 아님"으로 나왔다). 시작 시각은 ISO 문자열로 뽑는다.
  const out = sh(
    `powershell -NoProfile -Command "Get-Process | Where-Object { $_.ProcessName -like 'Adobe Premiere Pro*' } | Select-Object -First 1 Id,@{n='StartTime';e={$_.StartTime.ToString('o')}} | ConvertTo-Json"`,
  );
  try {
    const p = JSON.parse(out ?? "null");
    if (p) running = { pid: p.Id, startedAt: new Date(p.StartTime).toISOString() };
  } catch {}
}
r.checks.premiereRunning = running;
r.checks.restartNeeded = Boolean(
  running && cep.installed && new Date(running.startedAt) < new Date(cep.installedAt),
);

// 경로에 한글 등 비ASCII 문자가 있는지 (expected_project_path 가드 오작동 원인)
r.checks.paths = {
  cwd: process.cwd(),
  cwdNonAscii: nonAscii(process.cwd()),
  tmpdir: os.tmpdir(),
  tmpdirNonAscii: nonAscii(os.tmpdir()),
  homeNonAscii: nonAscii(os.homedir()),
};

// ffmpeg / ffprobe (trim_clip, slip_edit, detect_silence 등에 필요)
const which = (b) => sh(isWin ? `where ${b}` : `command -v ${b}`)?.split(/\r?\n/)[0] ?? null;
r.checks.ffmpeg = { ffmpeg: which("ffmpeg"), ffprobe: which("ffprobe") };

// Claude Code 등록 상태 (현재 폴더 기준)
const mcpGet = sh("claude mcp get premiere-pro", 90000);
r.checks.claudeRegistration = mcpGet
  ? { registered: true, connected: /Connected/.test(mcpGet), scope: mcpGet.match(/Scope:\s*(.+)/)?.[1] ?? null }
  : { registered: false };

if (process.argv.includes("--json")) {
  console.log(JSON.stringify(r, null, 2));
} else {
  const c = r.checks;
  const yes = (b) => (b ? "예" : "아니오");
  console.log(`OS: ${r.platform}`);
  console.log(`Node: ${c.node.version} ${c.node.ok ? "(OK)" : "(20.19 이상 필요)"}`);
  console.log(`premiere-pro-mcp: 설치 ${c.package.installed ?? "없음"} / 최신 ${c.package.latest ?? "?"} / repo ${c.package.repository ?? "?"}`);
  console.log(`CEP 커넥터: ${c.cepConnector.installed ? `설치됨 ${c.cepConnector.bundleVersion ?? ""}${c.cepConnector.signed ? " 서명됨" : " 서명 없음"} (호스트 ${c.cepConnector.hostRange ?? "?"}+, ${c.cepConnector.installedAt})` : "없음"}`);
  console.log(
    `PlayerDebugMode: ${Object.entries(c.playerDebugMode).map(([k, v]) => `${k}=${v ?? "-"}`).join(" ")}${c.cepConnector.signed ? " (서명된 커넥터라 없어도 됨)" : ""}`,
  );
  for (const p of c.premiereInstalls)
    console.log(`Premiere: ${[p.app ?? p.dir, p.version, p.bundleId, p.cepVersion && `CEP ${p.cepVersion}`].filter(Boolean).join(" ")}`);
  if (!c.premiereInstalls.length) console.log("Premiere: 설치본을 찾지 못함");
  console.log(`Premiere 실행 중: ${c.premiereRunning ? `예 (시작 ${c.premiereRunning.startedAt})` : "아니오"}`);
  console.log(`커넥터 반영에 재시작 필요: ${yes(c.restartNeeded)}`);
  console.log(`현재 폴더 비ASCII: ${yes(c.paths.cwdNonAscii)} / 임시 폴더 비ASCII: ${yes(c.paths.tmpdirNonAscii)}`);
  console.log(`ffmpeg: ${c.ffmpeg.ffmpeg ?? "없음"} / ffprobe: ${c.ffmpeg.ffprobe ?? "없음"}`);
  console.log(`Claude Code 등록(현재 폴더): ${c.claudeRegistration.registered ? `${c.claudeRegistration.scope ?? ""} ${c.claudeRegistration.connected ? "Connected" : "연결 안 됨"}` : "없음"}`);
}
