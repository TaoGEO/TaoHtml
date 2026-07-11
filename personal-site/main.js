import * as THREE from "three";

const canvas = document.querySelector("#portrait-canvas");
const stage = document.querySelector(".particle-stage");
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
const clock = new THREE.Clock();

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: true,
  preserveDrawingBuffer: true,
  powerPreference: "high-performance",
});

renderer.setClearColor(0x000000, 0);
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 120);
camera.position.set(0, 0, 7.4);

const world = new THREE.Group();
const farField = new THREE.Group();
const midField = new THREE.Group();
const nearField = new THREE.Group();
const tunnel = new THREE.Group();
const rails = new THREE.Group();
const haze = new THREE.Group();

scene.add(world);
world.add(farField, haze, tunnel, rails, midField, nearField);

const uniforms = {
  uTime: { value: 0 },
  uPointer: { value: new THREE.Vector2(0, 0) },
  uPixelRatio: { value: renderer.getPixelRatio() },
};

const particleVertexShader = `
  attribute vec3 aColor;
  attribute float aSize;
  attribute float aAlpha;
  attribute float aSeed;
  attribute float aDepth;
  varying vec3 vColor;
  varying float vAlpha;
  uniform float uTime;
  uniform vec2 uPointer;
  uniform float uPixelRatio;

  void main() {
    vec3 p = position;
    float drift = uTime * (0.08 + aDepth * 0.12);
    p.x += sin(drift + aSeed * 6.2831 + position.z * 0.18) * (0.018 + aDepth * 0.04);
    p.y += cos(drift * 1.24 + aSeed * 7.0) * (0.014 + aDepth * 0.03);
    p.z += sin(drift * 1.46 + aSeed * 4.4) * (0.035 + aDepth * 0.13);

    vec2 lens = uPointer * vec2(1.75, 1.08);
    vec2 delta = p.xy - lens;
    float influence = smoothstep(1.85, 0.0, length(delta));
    p.xy += normalize(delta + vec2(0.0001)) * influence * (0.045 + aDepth * 0.075);
    p.z += influence * (0.18 + aDepth * 0.24);

    vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
    float perspective = 8.2 / -mvPosition.z;
    gl_PointSize = aSize * uPixelRatio * perspective * (1.0 + influence * 0.58);
    gl_Position = projectionMatrix * mvPosition;

    vColor = aColor;
    vAlpha = aAlpha * (0.72 + influence * 0.48);
  }
`;

const particleFragmentShader = `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    vec2 uv = gl_PointCoord.xy - 0.5;
    float d = dot(uv, uv);
    if (d > 0.25) discard;
    float core = smoothstep(0.075, 0.0, d);
    float halo = smoothstep(0.25, 0.02, d) * 0.38;
    gl_FragColor = vec4(vColor, vAlpha * (core + halo));
  }
`;

function particleMaterial() {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms,
    vertexShader: particleVertexShader,
    fragmentShader: particleFragmentShader,
  });
}

function pushParticle(target, x, y, z, size, alpha, depth, color, seed = Math.random()) {
  target.positions.push(x, y, z);
  target.sizes.push(size);
  target.alphas.push(alpha);
  target.depths.push(depth);
  target.colors.push(color[0], color[1], color[2]);
  target.seeds.push(seed);
}

function createParticleGeometry(kind) {
  const isMobile = window.innerWidth < 760;
  const target = {
    positions: [],
    sizes: [],
    alphas: [],
    depths: [],
    colors: [],
    seeds: [],
  };

  if (kind === "far") {
    const count = isMobile ? 700 : 1600;
    for (let i = 0; i < count; i += 1) {
      pushParticle(
        target,
        -4.2 + Math.random() * 10.8,
        -3.4 + Math.random() * 6.8,
        -11.5 + Math.random() * 7.4,
        0.36 + Math.random() * 1.2,
        0.035 + Math.random() * 0.09,
        0.12 + Math.random() * 0.28,
        [0.42 + Math.random() * 0.2, 0.72 + Math.random() * 0.18, 1.0]
      );
    }
  }

  if (kind === "mid") {
    const count = isMobile ? 1500 : 3600;
    for (let i = 0; i < count; i += 1) {
      const theta = Math.random() * Math.PI * 2;
      const radius = Math.pow(Math.random(), 0.58) * (isMobile ? 1.55 : 2.45);
      const wake = Math.random() < 0.48 ? Math.pow(Math.random(), 0.42) * 3.4 : 0;
      const x = 1.15 + Math.cos(theta) * radius * 0.9 + wake;
      const y = 0.12 + Math.sin(theta) * radius * 0.78 + (Math.random() - 0.5) * wake * 0.22;
      const z = -0.7 + (Math.random() - 0.5) * 2.5 - wake * 0.34;
      const warm = Math.random() > 0.7;
      pushParticle(
        target,
        x,
        y,
        z,
        0.46 + Math.random() * 1.75,
        0.055 + Math.random() * 0.24,
        0.52 + Math.random() * 0.46,
        warm ? [0.9, 0.78 + Math.random() * 0.08, 0.66] : [0.58, 0.85 + Math.random() * 0.12, 1.0]
      );
    }
  }

  if (kind === "near") {
    const count = isMobile ? 120 : 260;
    for (let i = 0; i < count; i += 1) {
      pushParticle(
        target,
        -0.8 + Math.random() * 6.3,
        -2.6 + Math.random() * 5.2,
        0.75 + Math.random() * 2.2,
        0.82 + Math.random() * 2.65,
        0.025 + Math.random() * 0.065,
        0.88 + Math.random() * 0.35,
        [0.72 + Math.random() * 0.18, 0.95, 1.0]
      );
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(target.positions, 3));
  geometry.setAttribute("aColor", new THREE.Float32BufferAttribute(target.colors, 3));
  geometry.setAttribute("aSize", new THREE.Float32BufferAttribute(target.sizes, 1));
  geometry.setAttribute("aAlpha", new THREE.Float32BufferAttribute(target.alphas, 1));
  geometry.setAttribute("aDepth", new THREE.Float32BufferAttribute(target.depths, 1));
  geometry.setAttribute("aSeed", new THREE.Float32BufferAttribute(target.seeds, 1));
  return geometry;
}

function createEllipsePoints(rx, ry, segments = 160, open = false) {
  const points = [];
  const limit = open ? segments : segments + 1;
  for (let i = 0; i < limit; i += 1) {
    const t = i / segments;
    const a = t * Math.PI * 2;
    points.push(new THREE.Vector3(Math.cos(a) * rx, Math.sin(a) * ry, Math.sin(a * 2) * 0.08));
  }
  return points;
}

function createTunnel() {
  const ringCount = window.innerWidth < 760 ? 6 : 9;
  for (let i = 0; i < ringCount; i += 1) {
    const t = i / Math.max(ringCount - 1, 1);
    const geometry = new THREE.BufferGeometry().setFromPoints(createEllipsePoints(0.84 + t * 2.3, 0.52 + t * 1.08));
    const material = new THREE.LineBasicMaterial({
      color: i % 2 === 0 ? 0xa7f4ff : 0xf0d7c2,
      transparent: true,
      opacity: 0.19 - t * 0.095,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const ring = new THREE.Line(geometry, material);
    ring.position.set(1.55 + t * 1.35, 0.02 + t * 0.2, -0.18 - t * 6.2);
    ring.rotation.set(0.2 - t * 0.18, -0.58 + t * 0.18, -0.08 + t * 0.36);
    tunnel.add(ring);
  }
}

function createRails() {
  const material = new THREE.LineBasicMaterial({
    color: 0xa7f4ff,
    transparent: true,
    opacity: 0.095,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  const count = window.innerWidth < 760 ? 9 : 16;
  for (let i = 0; i < count; i += 1) {
    const t = i / Math.max(count - 1, 1);
    const startY = -2.15 + t * 4.3;
    const startX = 0.28 + Math.sin(t * Math.PI) * 0.7;
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(startX, startY, 1.8),
      new THREE.Vector3(1.4 + t * 1.3, startY * 0.55 + 0.34, -0.85 - t * 0.7),
      new THREE.Vector3(4.7 + t * 1.9, 0.22 + (t - 0.5) * 1.25, -6.4 - t * 1.2),
    ]);
    const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(72));
    rails.add(new THREE.Line(geometry, material));
  }
}

function createHaze() {
  const geometry = new THREE.PlaneGeometry(1, 1);
  const configs = [
    { x: 2.15, y: 0.08, z: -1.45, sx: 3.2, sy: 1.05, opacity: 0.035, rot: -0.18 },
    { x: 3.4, y: 0.32, z: -3.1, sx: 5.4, sy: 1.42, opacity: 0.028, rot: 0.22 },
    { x: 4.7, y: -0.18, z: -5.6, sx: 7.4, sy: 1.9, opacity: 0.022, rot: 0.42 },
  ];

  configs.forEach((cfg) => {
    const material = new THREE.MeshBasicMaterial({
      color: 0xa7f4ff,
      transparent: true,
      opacity: cfg.opacity,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const plane = new THREE.Mesh(geometry, material);
    plane.position.set(cfg.x, cfg.y, cfg.z);
    plane.scale.set(cfg.sx, cfg.sy, 1);
    plane.rotation.set(0.15, -0.45, cfg.rot);
    haze.add(plane);
  });
}

farField.add(new THREE.Points(createParticleGeometry("far"), particleMaterial()));
midField.add(new THREE.Points(createParticleGeometry("mid"), particleMaterial()));
nearField.add(new THREE.Points(createParticleGeometry("near"), particleMaterial()));
createTunnel();
createRails();
createHaze();

function resize() {
  const rect = canvas.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height, false);
  camera.aspect = rect.width / Math.max(rect.height, 1);
  camera.fov = window.innerWidth < 760 ? 43 : 38;
  camera.updateProjectionMatrix();

  if (window.innerWidth < 760) {
    world.scale.setScalar(0.58);
    world.position.set(0.06, -1.22, 0);
  } else if (window.innerWidth < 1120) {
    world.scale.setScalar(0.86);
    world.position.set(0.5, -0.18, 0);
  } else {
    world.scale.setScalar(1.08);
    world.position.set(0.82, -0.04, 0);
  }
}

function onPointerMove(event) {
  const rect = stage.getBoundingClientRect();
  pointer.tx = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * 2 - 1;
  pointer.ty = -(((event.clientY - rect.top) / Math.max(rect.height, 1)) * 2 - 1);
}

function animate() {
  const seconds = clock.getElapsedTime();
  pointer.x += (pointer.tx - pointer.x) * 0.055;
  pointer.y += (pointer.ty - pointer.y) * 0.055;

  uniforms.uTime.value = prefersReducedMotion ? 0 : seconds;
  uniforms.uPointer.value.set(pointer.x, pointer.y);

  if (!prefersReducedMotion) {
    camera.position.x = pointer.x * 0.42;
    camera.position.y = pointer.y * 0.18;
    camera.lookAt(pointer.x * 0.12, pointer.y * 0.08, -1.15);

    world.rotation.y = pointer.x * 0.1;
    world.rotation.x = -pointer.y * 0.04;
    farField.rotation.y = seconds * 0.012 + pointer.x * 0.055;
    midField.rotation.y = Math.sin(seconds * 0.13) * 0.04 + pointer.x * 0.16;
    midField.rotation.x = -pointer.y * 0.065;
    nearField.position.x = -pointer.x * 0.48;
    nearField.position.y = -pointer.y * 0.18;
    tunnel.rotation.y = pointer.x * 0.18 + Math.sin(seconds * 0.11) * 0.035;
    tunnel.rotation.x = -pointer.y * 0.09;
    rails.rotation.y = pointer.x * 0.22;
    rails.rotation.x = -pointer.y * 0.08;
    haze.rotation.z = Math.sin(seconds * 0.1) * 0.018;

    stage.style.setProperty("--mx", pointer.x.toFixed(3));
    stage.style.setProperty("--my", pointer.y.toFixed(3));
  }

  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

window.addEventListener("resize", resize);
window.addEventListener("pointermove", onPointerMove, { passive: true });

document.body.classList.add("webgl-space-ready");
resize();
animate();
