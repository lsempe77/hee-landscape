// Render HTML infographics at a fixed desktop width, independent of the screen.
let renderer;
function loadRenderer() {
  if (!renderer) renderer = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = new URL("./vendor/html2canvas-1.4.1.min.js", import.meta.url).href;
    script.onload = () => resolve(window.html2canvas);
    script.onerror = () => { script.remove(); renderer = null; reject(new Error("Image renderer could not load.")); };
    document.head.appendChild(script);
  });
  return renderer;
}

export async function downloadHtmlFigure(url, filename) {
  const render = await loadRenderer();
  const frame = document.createElement("iframe");
  frame.title = "Preparing figure download";
  frame.setAttribute("aria-hidden", "true");
  frame.style.cssText = "position:fixed;left:-20000px;top:0;width:1200px;height:2400px;border:0;pointer-events:none";
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Figure took too long to load.")), 45000);
      frame.onload = () => { clearTimeout(timer); resolve(); };
      frame.onerror = () => { clearTimeout(timer); reject(new Error("Figure could not load.")); };
      frame.src = url;
      document.body.appendChild(frame);
    });
    const doc = frame.contentDocument;
    const win = frame.contentWindow;
    await doc.fonts.ready;
    const plots = [...doc.querySelectorAll(".js-plotly-plot")];
    if (!win.Plotly || !plots.length) throw new Error("Figure charts could not load. Please retry.");
    const snapshots = [];
    for (const plot of plots) {
      await Promise.all(plot._promises || []);
      if (!plot._fullLayout) throw new Error("Figure charts are still loading. Please retry.");
      snapshots.push({ id: plot.id, width: plot.clientWidth, height: plot.clientHeight,
        src: await win.Plotly.toImage(plot, { format: "png", scale: 2 }) });
    }
    const canvas = await render(doc.querySelector(".wrap") || doc.body, {
      scale: 2, backgroundColor: win.getComputedStyle(doc.body).backgroundColor,
      windowWidth: 1200, scrollX: 0, scrollY: 0, logging: false,
      onclone(clone) {
        clone.querySelectorAll(".q, #pop, .modebar").forEach(node => node.remove());
        for (const shot of snapshots) {
          const image = clone.createElement("img");
          image.src = shot.src;
          image.style.cssText = `display:block;width:${shot.width}px;height:${shot.height}px`;
          clone.getElementById(shot.id).replaceWith(image);
        }
      }
    });
    const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
    if (!blob) throw new Error("PNG could not be created.");
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename.replace(/\.[^.]+$/, "") + ".png";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
  } finally {
    frame.remove();
  }
}
