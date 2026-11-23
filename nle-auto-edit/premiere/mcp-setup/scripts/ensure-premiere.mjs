#!/usr/bin/env node
// Premiere Pro가 꺼져 있으면 켜고, MCP 커넥터가 붙을 때까지 기다린 뒤 연결 상태를 알려 준다.
// --project를 주면 그 프로젝트가 활성이 아닐 때 연다. 다른 프로젝트를 닫거나 저장하지는 않는다.
//
// 사용법:
//   node ensure-premiere.mjs [--project=<.prproj 절대 경로>] [--app=<.app 또는 .exe 경로>] [--wait=180] [--json]
//
// 종료 코드: 0 = 커넥터 연결됨(프로젝트·시퀀스까지 ready가 아니어도 0, 출력의 overall로 구분), 1 = 연결 못 함
// macOS(Premiere 2027)와 Windows 11(Premiere 2027, 2026-11-22)에서 검증됨.

import { execSync, spawn } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { connect } from "./lib-mcp.mjs";

const isMac = process.platform === "darwin";
const isWin = process.platform === "win32";
const opt = Object.fromEntries(
  process.argv.slice(2).filter((a) => a.startsWith("--")).map((a) => {
    const [k, ...v] = a.slice(2).split("=");
    return [k, v.length ? v.join("=") : true];
  }),
);
const waitSec = Number(opt.wait ?? 180);
const log = [];
const say = (s) => {
  log.push(s);
  if (!opt.json) console.log(s);
};
const sh = (cmd) => {
  try {
    return execSync(cmd, { encoding: "utf8", shell: true, stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return null;
  }
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const verNum = (v) => (v ?? "0").split(".").map((n) => Number(n) || 0).reduce((a, n) => a * 1000 + n, 0);

// 설치본 찾기 (최신 버전 먼저)
function findInstalls() {
  const out = [];
  if (isMac) {
    for (const d of readdirSync("/Applications").filter((n) => n.startsWith("Adobe Premiere Pro"))) {
      const dir = path.join("/Applications", d);
      for (const app of readdirSync(dir).filter((n) => n.startsWith("Adobe Premiere Pro") && n.endsWith(".app"))) {
        const p = path.join(dir, app);
        out.push({ path: p, version: sh(`defaults read "${p}/Contents/Info.plist" CFBundleShortVersionString`) });
      }
    }
  } else if (isWin) {
    const base = "C:\\Program Files\\Adobe";
    if (existsSync(base)) {
      for (const d of readdirSync(base).filter((n) => n.startsWith("Adobe Premiere Pro"))) {
        const exe = path.join(base, d, "Adobe Premiere Pro.exe");
        if (existsSync(exe)) out.push({ path: exe, version: d.match(/(\d{4})/)?.[1] ?? null });
      }
    }
  }
  return out.sort((a, b) => verNum(b.version) - verNum(a.version));
}

function isRunning() {
  // pgrep이 가끔 한 번 빈 결과를 주는 경우가 있어 ps로 한 번 더 확인한다.
  if (isMac) {
    const re = "Adobe Premiere Pro[^/]*\\.app/Contents/MacOS/Adobe Premiere Pro[^/]*$";
    return Boolean(sh(`pgrep -f "${re}"`) || sh(`ps -axo command= | grep -E "${re}" | grep -v grep`));
  }
  if (isWin) return /Adobe Premiere Pro\.exe/i.test(sh(`tasklist /FI "IMAGENAME eq Adobe Premiere Pro.exe"`) ?? "");
  return false;
}

function launch(appPath) {
  if (isMac) return sh(`open "${appPath}"`) !== null;
  if (isWin) {
    // `start`를 execSync(stdout 파이프)로 부르면 Premiere가 그 파이프 핸들을 물려받아
    // Premiere가 꺼질 때까지 execSync가 돌아오지 않는다(2026-11-22 Windows 11 실측: 무한 대기).
    // 그래서 파이프 없이 분리된 프로세스로 띄우고 바로 놓아 준다.
    if (!existsSync(appPath)) return false;
    try {
      const child = spawn(appPath, [], { detached: true, stdio: "ignore", windowsHide: false });
      child.on("error", () => {});
      child.unref();
      return true;
    } catch {
      return false;
    }
  }
  return false;
}

const norm = (p) => (p ?? "").normalize("NFC").replace(/\\/g, "/").toLowerCase();
const result = { launched: false, app: null, connector: null, overall: null, components: null, project: null, hints: [] };
let client;

try {
  // 1) 실행 중이 아니면 켠다
  if (isRunning()) {
    say("Premiere: 이미 실행 중");
  } else {
    const installs = findInstalls();
    const app = opt.app ?? installs[0]?.path;
    if (!app) {
      result.hints.push("Premiere 설치본을 찾지 못함. --app=<경로>로 지정하거나 사용자에게 설치 위치를 묻는다.");
      throw new Error("Premiere 설치본 없음");
    }
    if (!opt.app && installs.length > 1)
      result.hints.push(`설치본이 여러 개라 최신(${installs[0].version})을 켬: ${installs.map((i) => i.version).join(", ")}. 다른 버전을 원하면 --app으로 지정.`);
    say(`Premiere 실행: ${app}`);
    if (!launch(app)) throw new Error("Premiere 실행 명령 실패");
    result.launched = true;
    result.app = app;
  }

  // 2) 커넥터가 붙을 때까지 기다린다 (heartbeat가 살아나면 blocking.state가 idle)
  client = await connect();
  const deadline = Date.now() + waitSec * 1000;
  let state = null;
  while (Date.now() < deadline) {
    const t = await client.call("get_bridge_telemetry", {}, 20000);
    state = t.data?.blocking?.state ?? null;
    if (state === "idle") break;
    if (result.launched && !isRunning() && Date.now() > deadline - waitSec * 1000 + 20000) {
      result.hints.push("실행 뒤 Premiere 프로세스가 사라짐: 시작하다 종료됐을 수 있음.");
      break;
    }
    await sleep(5000);
  }
  result.connector = state;
  if (state !== "idle") {
    result.hints.push(
      "커넥터 신호가 오지 않음. 화면에 Premiere 시작 대화상자(충돌 복구, 업데이트·로그인 안내, 저장 확인 등)가 떠 있는지 확인한다(computer use 스크린샷). 처리 뒤 이 스크립트를 다시 실행한다.",
    );
    throw new Error(`커넥터 대기 시간 초과(${waitSec}초), 상태 ${state}`);
  }
  say("커넥터: 연결됨");

  // 3) 요청한 프로젝트가 활성이 아니면 연다
  if (opt.project) {
    // 커넥터가 막 붙은 직후에는 첫 조회가 실패할 수 있어 한 번 더 본다.
    let info = await client.call("get_project_info");
    if (!info.ok) {
      await sleep(3000);
      info = await client.call("get_project_info");
    }
    const activePath = info.ok ? info.data?.path : null;
    if (activePath && norm(activePath) === norm(opt.project)) {
      say(`프로젝트: 이미 활성 (${activePath})`);
    } else {
      if (!existsSync(opt.project)) throw new Error(`프로젝트 파일 없음: ${opt.project}`);
      say(`프로젝트 열기: ${opt.project}`);
      const op = await client.call("open_project", { path: opt.project, idempotency_key: `ensure-open-${Date.now()}` }, 150000);
      if (!op.ok) {
        const tel = await client.call("get_bridge_telemetry", {}, 20000);
        result.hints.push(
          `open_project ${op.timeout ? "타임아웃" : "실패"}: ${op.error}. 브리지 상태 ${tel.data?.blocking?.state}. 대화상자(Scratch Disk Settings, 미디어 연결 등)가 떠 있으면 처리하고, inspect_operation_recovery로 실제 상태를 확인한 뒤 acknowledge_operation_recovery로 잠금을 푼다.`,
        );
      }
    }
  }

  // 4) 최종 연결 확인
  const v = await client.call("verify_premiere_connection", {}, 60000);
  result.overall = v.data?.overall ?? null;
  result.components = (v.data?.components ?? []).map((c) => ({ id: c.id, state: c.state, code: c.code }));
  const info = await client.call("get_project_info");
  if (info.ok) result.project = { name: info.data?.name, path: info.data?.path, activeSequence: info.data?.activeSequence?.name ?? null };
  if (result.components?.find((c) => c.code === "ACTIVE_SEQUENCE_MISSING"))
    result.hints.push("활성 시퀀스가 없음: 어떤 시퀀스를 쓸지 사용자에게 묻고 set_active_sequence로 연다.");
  if (!result.project && !opt.project)
    result.hints.push("열린 프로젝트가 없음(홈 화면): 어떤 프로젝트를 쓸지 사용자에게 묻고 --project로 다시 실행하거나 open_project로 연다.");
  say(`연결 확인: overall ${result.overall}`);
  for (const c of result.components ?? []) say(`  - ${c.id}: ${c.state} (${c.code})`);
  if (result.project) say(`활성 프로젝트: ${result.project.name} / 시퀀스: ${result.project.activeSequence ?? "없음"}`);
} catch (e) {
  result.error = e.message;
  say(`실패: ${e.message}`);
} finally {
  client?.close();
  for (const h of result.hints) say(`참고: ${h}`);
  if (opt.json) console.log(JSON.stringify(result, null, 2));
  process.exit(result.connector === "idle" ? 0 : 1);
}
