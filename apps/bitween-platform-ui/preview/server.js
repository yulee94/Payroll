const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const port = Number(process.env.PORT || process.argv[2] || 4173);
const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"]
]);

function send(res, status, body, type = "text/plain; charset=utf-8") {
  res.writeHead(status, { "content-type": type });
  res.end(body);
}

const server = http.createServer((req, res) => {
  const requestedPath = decodeURIComponent((req.url || "/").split("?")[0]);
  const relativePath = requestedPath === "/" ? "index.html" : requestedPath.replace(/^\/+/, "");
  const filePath = path.normalize(path.join(root, relativePath));

  if (!filePath.startsWith(root)) {
    send(res, 403, "Forbidden");
    return;
  }

  fs.readFile(filePath, (error, data) => {
    if (error) {
      send(res, 404, "Not found");
      return;
    }
    send(res, 200, data, contentTypes.get(path.extname(filePath)) || "application/octet-stream");
  });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Bitween UI preview: http://127.0.0.1:${port}`);
});
