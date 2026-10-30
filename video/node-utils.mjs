import fs from "node:fs";

/** Tìm Chrome/Edge sẵn có; trả về {} nếu không thấy (Remotion tự tải headless shell). */
export const browserOption = () => {
  const candidates = [
    process.env.REMOTION_BROWSER_EXECUTABLE,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  ].filter(Boolean);
  const browserExecutable = candidates.find((item) => fs.existsSync(item)) ?? null;
  if (browserExecutable) {
    console.log(`Browser: ${browserExecutable}`);
  }
  return browserExecutable ? { browserExecutable } : {};
};

/** Đọc `--name value` từ argv. */
export const makeFlag = (argv) => (name) => {
  const index = argv.indexOf(`--${name}`);
  return index >= 0 ? argv[index + 1] : undefined;
};
