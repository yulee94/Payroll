const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const port = Number(process.env.PORT || process.argv[2] || 4174);
const clients = new Set();
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".js": "text/javascript; charset=utf-8"
};

const noCacheHeaders = {
  "cache-control": "no-store, no-cache, must-revalidate, max-age=0",
  "pragma": "no-cache"
};

function assetVersion(fileName) {
  try {
    return String(fs.statSync(path.join(root, fileName)).mtimeMs);
  } catch {
    return String(Date.now());
  }
}

function sendIndex(res) {
  fs.readFile(path.join(root, "index.html"), "utf8", (err, html) => {
    if (err) {
      res.writeHead(404, { ...noCacheHeaders, "content-type": "text/plain; charset=utf-8" });
      res.end("Not found");
      return;
    }
    const versioned = html
      .replace("./styles.css", `./styles.css?v=${assetVersion("styles.css")}`)
      .replace("./app.js", `./app.js?v=${assetVersion("app.js")}`);
    res.writeHead(200, { ...noCacheHeaders, "content-type": types[".html"] });
    res.end(versioned);
  });
}

function sendFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { ...noCacheHeaders, "content-type": "text/plain; charset=utf-8" });
      res.end("Not found");
      return;
    }
    res.writeHead(200, { ...noCacheHeaders, "content-type": types[path.extname(filePath)] || "application/octet-stream" });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  if (req.url === "/events") {
    res.writeHead(200, {
      "cache-control": "no-cache",
      "connection": "keep-alive",
      "content-type": "text/event-stream"
    });
    res.write("\n");
    clients.add(res);
    req.on("close", () => clients.delete(res));
    return;
  }

  const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
  if (urlPath === "/catalog.json") {
    sendFile(res, path.join(root, "..", "src", "i18n", "catalog.json"));
    return;
  }
  if (urlPath === "/" || urlPath === "/index.html") {
    sendIndex(res);
    return;
  }
  const safePath = urlPath;
  const filePath = path.normalize(path.join(root, safePath));
  if (!filePath.startsWith(root)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }
  sendFile(res, filePath);
});

for (const filePath of [
  path.join(root, "index.html"),
  path.join(root, "styles.css"),
  path.join(root, "app.js"),
  path.join(root, "..", "src", "i18n", "catalog.json")
]) {
  fs.watch(filePath, { persistent: false }, () => {
    for (const client of clients) client.write("event: reload\ndata: now\n\n");
  });
}

server.listen(port, "127.0.0.1", () => {
  console.log(`Bitween demo-only preview running at http://127.0.0.1:${port}`);
});
