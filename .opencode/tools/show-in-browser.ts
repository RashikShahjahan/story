import { tool } from "@opencode-ai/plugin"
import path from "path"
import { pathToFileURL } from "url"

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
}

export default tool({
  description: "Open one local HTML file/URL, or show multiple local animation files one by one in a browser slideshow.",
  args: {
    target: tool.schema.string().optional().describe("Single relative path, absolute path, or URL to open in the browser"),
    targets: tool.schema.array(tool.schema.string()).optional().describe("Multiple local animation file paths to show one by one"),
    secondsPerAnimation: tool.schema.number().optional().describe("Seconds to show each animation before advancing"),
  },
  async execute(args, context) {
    const targets = args.targets?.map((target) => target.trim()).filter(Boolean) ?? []

    if (targets.length > 0) {
      const secondsPerAnimation = args.secondsPerAnimation ?? 8
      const files = await Promise.all(targets.map(async (target) => {
        if (/^https?:\/\//i.test(target)) {
          throw new Error("targets only supports local files; use target for a single URL")
        }

        const filePath = path.isAbsolute(target)
          ? target
          : path.resolve(context.directory, target)

        const file = Bun.file(filePath)
        if (!(await file.exists())) {
          throw new Error(`File does not exist: ${filePath}`)
        }

        return filePath
      }))

      const previewDir = path.resolve(context.directory, ".opencode/generated")
      await Bun.$`mkdir -p ${previewDir}`.quiet()

      const slides = files.map((filePath, index) => {
        const title = path.basename(filePath)
        const src = pathToFileURL(filePath).href
        return `<section class="slide${index === 0 ? " active" : ""}" data-index="${index}">
  <iframe src="${escapeHtml(src)}" title="${escapeHtml(title)}"></iframe>
</section>`
      }).join("\n")

      const previewPath = path.join(previewDir, "story-animations.html")
      await Bun.write(previewPath, `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Story Animations</title>
  <style>
    html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; background: #050505; color: white; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .slide { position: fixed; inset: 0; opacity: 0; pointer-events: none; transition: opacity 500ms ease; }
    .slide.active { opacity: 1; pointer-events: auto; }
    iframe { width: 100%; height: 100%; border: 0; display: block; background: #050505; }
    .hud { position: fixed; left: 16px; right: 16px; bottom: 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border-radius: 999px; background: rgb(0 0 0 / 55%); backdrop-filter: blur(10px); font-size: 14px; }
    button { border: 0; border-radius: 999px; padding: 8px 12px; background: white; color: #111; cursor: pointer; font: inherit; }
    .controls { display: flex; gap: 8px; }
  </style>
</head>
<body>
${slides}
  <div class="hud">
    <div><span id="counter">1</span> / ${files.length}</div>
    <div class="controls">
      <button id="prev" type="button">Previous</button>
      <button id="toggle" type="button">Pause</button>
      <button id="next" type="button">Next</button>
    </div>
  </div>
  <script>
    const slides = [...document.querySelectorAll('.slide')];
    const counter = document.querySelector('#counter');
    const toggle = document.querySelector('#toggle');
    let index = 0;
    let playing = true;
    let timer;

    function show(nextIndex) {
      slides[index].classList.remove('active');
      index = (nextIndex + slides.length) % slides.length;
      slides[index].classList.add('active');
      counter.textContent = String(index + 1);
      restart();
    }

    function restart() {
      clearInterval(timer);
      if (playing) timer = setInterval(() => show(index + 1), ${Math.max(1, secondsPerAnimation) * 1000});
    }

    document.querySelector('#prev').addEventListener('click', () => show(index - 1));
    document.querySelector('#next').addEventListener('click', () => show(index + 1));
    toggle.addEventListener('click', () => {
      playing = !playing;
      toggle.textContent = playing ? 'Pause' : 'Play';
      restart();
    });
    addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') show(index - 1);
      if (event.key === 'ArrowRight') show(index + 1);
      if (event.key === ' ') {
        event.preventDefault();
        toggle.click();
      }
    });
    restart();
  </script>
</body>
</html>
`)

      await Bun.$`open ${previewPath}`.quiet()
      return `Opened ${files.length} animations one by one in ${previewPath}.`
    }

    const target = args.target?.trim() ?? ""

    if (!target) {
      throw new Error("target or targets is required")
    }

    if (/^https?:\/\//i.test(target)) {
      await Bun.$`open ${target}`.quiet()
      return `Opened ${target} in the browser.`
    }

    const filePath = path.isAbsolute(target)
      ? target
      : path.resolve(context.directory, target)

    const file = Bun.file(filePath)
    if (!(await file.exists())) {
      throw new Error(`File does not exist: ${filePath}`)
    }

    await Bun.$`open ${filePath}`.quiet()
    return `Opened ${filePath} in the browser.`
  },
})
