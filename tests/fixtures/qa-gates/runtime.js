const deck = document.querySelector(".deck");
const slides = [...document.querySelectorAll(".slide")];
const selector = ".fragment";

function controlledNodes(slide) {
  return [...slide.querySelectorAll(selector)];
}

function normalizeSteps(slide) {
  let next = 0;
  for (const node of controlledNodes(slide)) {
    const authored = Number.parseInt(node.dataset.step || "", 10);
    next = Number.isInteger(authored) && authored > 0 ? Math.max(next, authored) : next + 1;
    node.dataset.taohtmlStep = String(Number.isInteger(authored) && authored > 0 ? authored : next);
  }
}

slides.forEach(normalizeSteps);

const state = {
  mode: deck.dataset.mode === "reading" ? "reading" : "presentation",
  index: 0,
  stages: slides.map(() => 0),
};

function stepCount(slide) {
  return controlledNodes(slide).reduce(
    (maximum, node) => Math.max(maximum, Number.parseInt(node.dataset.taohtmlStep || "0", 10)),
    0,
  );
}

function setStage(index, next) {
  const count = stepCount(slides[index]);
  state.stages[index] = Math.max(0, Math.min(count, next));
  slides[index].dataset.stepIndex = String(state.stages[index]);
  for (const node of controlledNodes(slides[index])) {
    node.classList.toggle(
      "visible",
      Number.parseInt(node.dataset.taohtmlStep || "0", 10) <= state.stages[index],
    );
  }
}

function render() {
  deck.dataset.mode = state.mode;
  slides.forEach((slide, index) => {
    slide.classList.toggle("active", index === state.index);
    setStage(index, state.mode === "reading" ? stepCount(slide) : state.stages[index]);
  });
  history.replaceState(null, "", `#${state.index + 1}`);
}

function showPage(index) {
  state.index = Math.max(0, Math.min(slides.length - 1, index));
  render();
}

function nextPage() {
  showPage(state.index + 1);
}

function previousPage() {
  showPage(state.index - 1);
}

function nextStep() {
  if (state.mode === "reading") return nextPage();
  const count = stepCount(slides[state.index]);
  if (state.stages[state.index] < count) {
    setStage(state.index, state.stages[state.index] + 1);
    return;
  }
  nextPage();
}

function previousStep() {
  if (state.mode === "reading") return previousPage();
  if (state.stages[state.index] > 0) {
    setStage(state.index, state.stages[state.index] - 1);
    return;
  }
  previousPage();
}

function setMode(mode) {
  if (!['reading', 'presentation'].includes(mode)) return;
  state.mode = mode;
  if (mode === "presentation") state.stages[state.index] = 0;
  render();
}

function getState() {
  return { mode: state.mode, index: state.index, stages: [...state.stages] };
}

async function toggleFullscreen() {}

window.TaoHtmlRuntime = Object.freeze({
  getState,
  setMode,
  showPage,
  nextStep,
  previousStep,
  nextPage,
  previousPage,
  toggleFullscreen,
});

window.addEventListener("keydown", event => {
  if (event.key === "ArrowRight") nextStep();
  if (event.key === "ArrowLeft") previousStep();
});

function fitDeck() {
  if (deck.dataset.responsive === "true") {
    deck.style.transform = "none";
    return;
  }
  const scale = Math.min(window.innerWidth / 1600, window.innerHeight / 900);
  deck.style.transform = `scale(${scale})`;
}

window.addEventListener("resize", fitDeck);
fitDeck();
render();
