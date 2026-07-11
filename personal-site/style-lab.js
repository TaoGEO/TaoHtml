const tabs = [...document.querySelectorAll(".lab-tabs button")];
const directions = [...document.querySelectorAll(".direction")];
const output = document.querySelector("#choice-output");
const choiceButtons = [...document.querySelectorAll(".mark-button")];

let activeKey = "poster";
const pointer = { x: 0, y: 0, targetX: 0, targetY: 0 };

function setActive(key) {
  activeKey = key;
  tabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.target === key));
  directions.forEach((direction) => {
    direction.classList.toggle("is-active", direction.dataset.direction === key);
  });
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => setActive(tab.dataset.target));
});

choiceButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const value = button.dataset.choice;
    localStorage.setItem("taomir-style-choice", value);
    output.textContent = value;
  });
});

const savedChoice = localStorage.getItem("taomir-style-choice");
if (savedChoice) output.textContent = savedChoice;

window.addEventListener(
  "pointermove",
  (event) => {
    pointer.targetX = event.clientX / Math.max(window.innerWidth, 1) - 0.5;
    pointer.targetY = event.clientY / Math.max(window.innerHeight, 1) - 0.5;
  },
  { passive: true }
);

function updatePointer() {
  pointer.x += (pointer.targetX - pointer.x) * 0.07;
  pointer.y += (pointer.targetY - pointer.y) * 0.07;
  directions.forEach((direction) => {
    direction.style.setProperty("--mx", pointer.x.toFixed(3));
    direction.style.setProperty("--my", pointer.y.toFixed(3));
  });
  requestAnimationFrame(updatePointer);
}
updatePointer();

const canvas = document.querySelector("#warp-canvas");
const ctx = canvas.getContext("2d", { alpha: false });
const image = new Image();
image.src = "./assets/hero-portrait-concept.png";

let canvasWidth = 1;
let canvasHeight = 1;
let imageReady = false;

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const scale = Math.min(window.devicePixelRatio || 1, 2);
  canvasWidth = Math.max(1, Math.round(rect.width * scale));
  canvasHeight = Math.max(1, Math.round(rect.height * scale));
  canvas.width = canvasWidth;
  canvas.height = canvasHeight;
}

function coverRect(imgWidth, imgHeight, targetWidth, targetHeight) {
  const scale = Math.max(targetWidth / imgWidth, targetHeight / imgHeight);
  const width = imgWidth * scale;
  const height = imgHeight * scale;
  return {
    x: (targetWidth - width) * 0.62,
    y: (targetHeight - height) * 0.44,
    width,
    height,
  };
}

function drawWarp(time = 0) {
  if (!imageReady) {
    requestAnimationFrame(drawWarp);
    return;
  }

  const seconds = time * 0.001;
  const rect = coverRect(image.naturalWidth, image.naturalHeight, canvasWidth, canvasHeight);
  const sliceHeight = Math.max(3, Math.round(canvasHeight / 180));
  const amplitude = canvasWidth * (0.006 + Math.abs(pointer.x) * 0.01);

  ctx.fillStyle = "#010202";
  ctx.fillRect(0, 0, canvasWidth, canvasHeight);

  for (let y = 0; y < canvasHeight; y += sliceHeight) {
    const sourceY = ((y - rect.y) / rect.height) * image.naturalHeight;
    const sourceH = (sliceHeight / rect.height) * image.naturalHeight;
    if (sourceY + sourceH < 0 || sourceY > image.naturalHeight) continue;

    const wave =
      Math.sin(y * 0.018 + seconds * 1.2) * amplitude +
      Math.sin(y * 0.006 - seconds * 0.8) * amplitude * 0.42 +
      pointer.x * canvasWidth * 0.006;
    const localAlpha = y / canvasHeight;

    ctx.globalAlpha = 0.94 - localAlpha * 0.08;
    ctx.drawImage(
      image,
      0,
      Math.max(0, sourceY),
      image.naturalWidth,
      Math.min(image.naturalHeight - sourceY, sourceH),
      rect.x + wave,
      y,
      rect.width,
      sliceHeight + 1
    );
  }

  const gradient = ctx.createRadialGradient(
    canvasWidth * (0.64 + pointer.x * 0.08),
    canvasHeight * (0.34 + pointer.y * 0.08),
    0,
    canvasWidth * 0.66,
    canvasHeight * 0.42,
    canvasWidth * 0.62
  );
  gradient.addColorStop(0, "rgba(167,244,255,0.12)");
  gradient.addColorStop(0.46, "rgba(167,244,255,0.03)");
  gradient.addColorStop(1, "rgba(1,2,2,0.74)");
  ctx.globalAlpha = 1;
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvasWidth, canvasHeight);

  requestAnimationFrame(drawWarp);
}

image.addEventListener("load", () => {
  imageReady = true;
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
requestAnimationFrame(drawWarp);

window.addEventListener("keydown", (event) => {
  const keyMap = {
    "1": "poster",
    "2": "cinema",
    "3": "archive",
    "4": "shader",
  };
  if (keyMap[event.key]) setActive(keyMap[event.key]);
});
