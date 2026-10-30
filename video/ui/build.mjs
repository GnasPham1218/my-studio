// Build giao diện duyệt (pipeline.ui): một file app.js + css + font vào ui/dist.
// Chạy: node ui/build.mjs (trong thư mục video/). pipeline.ui tự gọi khi khởi động.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const here = path.dirname(fileURLToPath(import.meta.url));

await build({
  entryPoints: [path.join(here, "main.tsx")],
  outfile: path.join(here, "dist", "app.js"),
  bundle: true,
  format: "esm",
  jsx: "automatic",
  minify: true,
  sourcemap: false,
  target: "es2020",
  loader: { ".woff": "file", ".woff2": "file" },
  assetNames: "assets/[name]-[hash]",
  define: { "process.env.NODE_ENV": '"production"' },
  logLevel: "warning",
});
console.log("✓ ui/dist/app.js");
