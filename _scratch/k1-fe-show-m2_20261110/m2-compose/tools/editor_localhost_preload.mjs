// Preload for the PRISM minimal editor: force every http server to bind 127.0.0.1 only
// (server.js calls server.listen(PORT) with no host). No PRISM file is modified.
import http from "node:http";
const orig = http.Server.prototype.listen;
http.Server.prototype.listen = function (port, ...rest) {
  if (typeof port === "number" && (rest.length === 0 || typeof rest[0] === "function")) {
    return orig.call(this, port, "127.0.0.1", ...rest);
  }
  return orig.call(this, port, ...rest);
};
