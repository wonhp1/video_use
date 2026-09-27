/**************************************************************************************************
 * ADOBE SYSTEMS INCORPORATED
 * Copyright 2013 Adobe Systems Incorporated
 * All Rights Reserved.
 *
 * NOTICE:  Adobe permits you to use, modify, and distribute this file in accordance with the
 * terms of the Adobe license agreement accompanying it.
 *
 * CSInterface.js - minimal shim for MCP Bridge (CEP 12 fixed build)
 *
 * ── 무엇이 고쳐졌나 ────────────────────────────────────────────────────────────
 * premiere-pro-mcp@1.1.1 이 npm 으로 배포한 원본 shim 은 evalScript 를
 *     var result = __adobe_cep__.evalScript(script);   // 콜백 없이 동기 호출
 * 로 호출했다. CEP 12(Premiere 2025/2026)에서 __adobe_cep__.evalScript 는
 * "비동기"라 즉시 undefined 를 반환하고 결과는 콜백으로 전달된다. 그래서
 * 모든 ExtendScript 호출이 undefined 가 되고 ("Could not detect Premiere
 * Pro version" 경고), MCP 명령이 전부 실패했다.
 *
 * 아래처럼 콜백을 네이티브 계층에 그대로 넘기면 정상 동작한다.
 * ──────────────────────────────────────────────────────────────────────────────
 **************************************************************************************************/

function CSInterface() {}

/**
 * Evaluates an ExtendScript in the host application (CEP 12 async-safe).
 * @param {string} script - The ExtendScript to evaluate.
 * @param {function} callback - Callback invoked asynchronously with the result string.
 */
CSInterface.prototype.evalScript = function (script, callback) {
  if (typeof __adobe_cep__ !== "undefined") {
    if (callback === null || callback === undefined) {
      callback = function (result) {};
    }
    __adobe_cep__.evalScript(script, callback);
  } else {
    console.warn("[CSInterface] Not running in CEP environment");
    if (callback) callback("EvalScript Error: Not in CEP environment");
  }
};

CSInterface.prototype.getHostEnvironment = function () {
  if (typeof __adobe_cep__ !== "undefined") {
    try {
      return JSON.parse(__adobe_cep__.getHostEnvironment());
    } catch (e) {
      return null;
    }
  }
  return null;
};

CSInterface.prototype.getSystemPath = function (pathType) {
  if (typeof __adobe_cep__ !== "undefined") {
    return __adobe_cep__.getSystemPath(pathType);
  }
  return "";
};

CSInterface.prototype.EXTENSION_ID = "extensionId";
