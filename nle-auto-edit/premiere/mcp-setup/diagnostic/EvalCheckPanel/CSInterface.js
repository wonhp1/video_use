function CSInterface() {}

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
