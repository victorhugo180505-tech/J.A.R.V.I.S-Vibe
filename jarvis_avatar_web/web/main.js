import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

import {
  VRMLoaderPlugin,
  VRMUtils
} from "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@3.4.5/lib/three-vrm.module.min.js";

document.title = "JARVIS_AVATAR__5f3c9e";

const canvas = document.getElementById("c");
const statusEl = document.getElementById("control-status");
const listenIndicator = document.getElementById("listen-indicator");
const listenText = document.getElementById("listen-text");
const toggleMicBtn = document.getElementById("toggle-mic");
const toggleAudioBtn = document.getElementById("toggle-audio");
const toggleVisionBtn = document.getElementById("toggle-vision");
const CONTROL_BASE = "http://127.0.0.1:8780";
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111111);

const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
camera.position.set(0, 1.45, 1.2);
const cameraTarget = new THREE.Vector3(0, 1.45, 0);
let cameraDynamicEnabled = true;
let cameraPresenceState = "IDLE";
let cameraPresenceTarget = "IDLE";
let cameraPresenceBlend = 0;
const cameraBasePose = {
  position: camera.position.clone(),
  target: cameraTarget.clone(),
  fov: camera.fov,
};
const cameraOffset = {
  position: new THREE.Vector3(0, 0, 0),
  target: new THREE.Vector3(0, 0, 0),
  fov: 0,
  yaw: 0,
  pitch: 0,
};

scene.add(new THREE.AmbientLight(0xffffff, 0.8));
const dir = new THREE.DirectionalLight(0xffffff, 1.4);
dir.position.set(1, 2, 2);
scene.add(dir);

// -----------------------------
// Control server UI
// -----------------------------
async function fetchJson(path, options = {}) {
  const res = await fetch(`${CONTROL_BASE}${path}`, options);
  if (!res.ok) {
    throw new Error(`Control server error ${res.status}`);
  }
  return res.json();
}

function applyToggleState(button, enabled) {
  if (!button) return;
  button.classList.toggle("is-on", Boolean(enabled));
  button.classList.toggle("is-off", !enabled);
  button.setAttribute("aria-pressed", String(Boolean(enabled)));
}

function applyListenIndicator(state) {
  if (!listenIndicator || !listenText) return;
  const micOn = Boolean(state?.mic_enabled);
  const wakeActive = Boolean(state?.wake_active);

  listenIndicator.classList.toggle("is-on", micOn);
  listenIndicator.classList.toggle("is-wake", wakeActive);

  if (!micOn) {
    listenText.textContent = "Mic apagado";
  } else if (wakeActive) {
    listenText.textContent = "Wake word detectado";
  } else {
    listenText.textContent = "Escuchando… (Oye Jarvis)";
  }
}

async function refreshControlStatus() {
  if (!statusEl) return;
  try {
    const state = await fetchJson("/state");
    statusEl.textContent = `Mic: ${state.mic_enabled ? "ON" : "OFF"} · Audio: ${state.audio_enabled ? "ON" : "OFF"} · Visión: ${state.vision_enabled ? "ON" : "OFF"}`;
    applyToggleState(toggleMicBtn, state.mic_enabled);
    applyToggleState(toggleAudioBtn, state.audio_enabled);
    applyToggleState(toggleVisionBtn, state.vision_enabled);
    applyListenIndicator(state);
  } catch (err) {
    statusEl.textContent = "Control server offline";
    applyToggleState(toggleMicBtn, false);
    applyToggleState(toggleAudioBtn, false);
    applyToggleState(toggleVisionBtn, false);
    applyListenIndicator({ mic_enabled: false, wake_active: false });
  }
}

async function bindToggle(button, path) {
  if (!button) return;
  button.addEventListener("click", async () => {
    try {
      await fetchJson(path, { method: "POST" });
    } catch (err) {
      console.warn(err);
    } finally {
      refreshControlStatus();
    }
  });
}

bindToggle(toggleMicBtn, "/mic/toggle");
bindToggle(toggleAudioBtn, "/audio/toggle");
bindToggle(toggleVisionBtn, "/vision/toggle");
refreshControlStatus();
setInterval(refreshControlStatus, 1000);

// -----------------------------
// State
// -----------------------------
let vrm = null;
let moodWobbleT = 0;
// Mouse NDC que llega por WS (o por pointer si quieres)
const mouseNDC = new THREE.Vector2(0, 0);

// Head tracking smoothing
let headYaw = 0;
let headPitch = 0;

// Blink
let blinkT = 0;
let nextBlink = 1.5 + Math.random() * 2.5;
let blinkValue = 0;
let blinking = false;
let relaxedBase = 0;
// Micro gaze
let gazeT = 0;
let gazeNext = 0.8 + Math.random() * 1.8;
const gazeOffset = new THREE.Vector3(0, 0, 0);

// Breathing
let breatheT = 0;

// TTS mouth
let speaking = false;

// Mood / Burst
let mood = "neutral";      // se queda hasta cambiar
let burst = null;          // “micro-emoción” breve
let burstT = 0;
let presenceState = "IDLE";
let presenceTarget = "IDLE";
let presenceBlend = 0;
const presencePose = {
  offset: new THREE.Vector3(0, 0, 0),
  head: new THREE.Euler(),
  neck: new THREE.Euler(),
  chest: new THREE.Euler(),
  spine: new THREE.Euler(),
};
const presencePoseTarget = {
  offset: new THREE.Vector3(0, 0, 0),
  head: new THREE.Euler(),
  neck: new THREE.Euler(),
  chest: new THREE.Euler(),
  spine: new THREE.Euler(),
};
let presenceLastState = "IDLE";

// Expresiones disponibles (auto)
let expressionKeys = [];
const EMO_CHANNELS = ["angry", "relaxed", "happy", "sad", "Surprised"];

// -----------------------------
// Helpers
// -----------------------------
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const degToRad = (deg) => (deg * Math.PI) / 180;

function updateCameraRig(dt, time) {
  if (!cameraDynamicEnabled) return;

  const state = cameraPresenceTarget;
  const yawLimit = degToRad(4);
  const pitchLimit = degToRad(3);
  const fovLimit = 2;

  let targetPos = new THREE.Vector3(0, 0, 0);
  let targetTarget = new THREE.Vector3(0, 0, 0);
  let targetFov = 0;
  let targetYaw = 0;
  let targetPitch = 0;

  if (state === "LISTENING") {
    targetPos.z = -cameraBasePose.position.z * 0.04;
    targetPitch = degToRad(1.5);
  } else if (state === "THINKING") {
    targetYaw = degToRad(Math.sin(time * 0.25) * 3);
    targetFov = Math.sin(time * 0.4) * 1.2;
  } else if (state === "SPEAKING") {
    targetPos.y = Math.sin(time * 1.5) * 0.001;
  } else {
    targetPos.y = Math.sin(time * 0.6) * 0.002;
  }

  targetYaw = clamp(targetYaw, -yawLimit, yawLimit);
  targetPitch = clamp(targetPitch, -pitchLimit, pitchLimit);
  targetFov = clamp(targetFov, -fovLimit, fovLimit);

  const t = Math.min(1, dt * 3);
  cameraOffset.position.lerp(targetPos, t);
  cameraOffset.target.lerp(targetTarget, t);
  cameraOffset.fov = THREE.MathUtils.lerp(cameraOffset.fov, targetFov, t);
  cameraOffset.yaw = THREE.MathUtils.lerp(cameraOffset.yaw, targetYaw, t);
  cameraOffset.pitch = THREE.MathUtils.lerp(cameraOffset.pitch, targetPitch, t);

  cameraBasePose.position.copy(camera.position);
  cameraBasePose.target.copy(cameraTarget);
  cameraBasePose.fov = camera.fov;

  const basePos = cameraBasePose.position;
  const baseTarget = cameraBasePose.target;

  camera.position.copy(basePos).add(cameraOffset.position);
  camera.fov = cameraBasePose.fov + cameraOffset.fov;
  camera.updateProjectionMatrix();

  const lookTarget = baseTarget.clone().add(cameraOffset.target);
  camera.lookAt(lookTarget);

  camera.rotateY(cameraOffset.yaw);
  camera.rotateX(cameraOffset.pitch);
}

function setCameraPresenceState(state) {
  const next = (state || "IDLE").toUpperCase();
  if (next !== cameraPresenceTarget) {
    console.log(`[CAM] state -> ${next}`);
    cameraPresenceTarget = next;
    cameraPresenceBlend = 0;
  }
}

function listExpressions() {
  const em = vrm?.expressionManager;
  if (!em) return [];

  const keys = [];
  for (const exp of em.expressions ?? []) {
    const rawName = exp?.name || "";
    const key = rawName.replace(/^VRMExpression_/, "");
    if (key) keys.push(key);
  }
  return keys;
}

function clearEmotionChannels() {
  const em = vrm?.expressionManager;
  if (!em) return;
  for (const k of EMO_CHANNELS) {
    if (expressionKeys.includes(k)) {
      try { em.setValue(k, 0); } catch {}
    }
  }
}

function applyCompositeMood(name) {
  const put = (k, v) => {
    if (expressionKeys.includes(k)) setExpression(k, v);
  };

  switch (name) {
    case "sarcastic":
      put("happy", 0.35);
      put("relaxed", 0.55);
      break;

    case "thinking":
      put("relaxed", 0.50);
      put("sad", 0.10);
      break;

    case "confident":
      put("happy", 0.45);
      put("relaxed", 0.25);
      break;

    case "tired":
      put("sad", 0.35);
      put("relaxed", 0.45);
      break;

    case "smug":
      put("happy", 0.25);
      put("relaxed", 0.20);
      break;

    case "annoyed":
      put("angry", 0.35);
      put("relaxed", 0.15);
      break;

    case "scared":
      put("Surprised", 0.35);
      put("sad", 0.25);
      break;

    case "neutral":
    default:
      break;
  }
}

function setExpression(key, value = 1.0) {
  const em = vrm?.expressionManager;
  if (!em) return false;
  if (!expressionKeys.includes(key)) return false;

  try {
    em.setValue(key, value);
    return true;
  } catch {
    return false;
  }
}

function applyPresenceState(state) {
  const next = (state || "IDLE").toUpperCase();
  presenceTarget = next;
  presenceBlend = 0;

  if (!presenceIndicator) return;

  presenceIndicator.classList.remove(
    "state-idle",
    "state-listening",
    "state-thinking",
    "state-speaking",
    "presence-pulse",
  );

  if (next === "IDLE") {
    presenceIndicator.textContent = "";
    presenceIndicator.classList.remove("is-visible");
    return;
  }

  presenceIndicator.classList.add("is-visible");

  if (next === "LISTENING") {
    presenceIndicator.textContent = "Escuchando…";
    presenceIndicator.classList.add("state-listening", "presence-pulse");
  } else if (next === "THINKING") {
    presenceIndicator.textContent = "Pensando…";
    presenceIndicator.classList.add("state-thinking", "presence-pulse");
  } else if (next === "SPEAKING") {
    presenceIndicator.textContent = "Hablando…";
    presenceIndicator.classList.add("state-speaking");
  }
}

function updatePresence(dt) {
  if (presenceState === presenceTarget) return;
  presenceBlend = Math.min(1, presenceBlend + dt * 2.5);
  if (presenceBlend >= 1) {
    presenceLastState = presenceState;
    presenceState = presenceTarget;
  }
}

function setPoseTarget(offset, head, neck, chest, spine) {
  presencePoseTarget.offset.copy(offset);
  presencePoseTarget.head.copy(head);
  presencePoseTarget.neck.copy(neck);
  presencePoseTarget.chest.copy(chest);
  presencePoseTarget.spine.copy(spine);
}

function updatePresencePoseTargets(time) {
  const idleSway = Math.sin(time * 0.6) * 0.003;
  const idleBreath = Math.sin(time * 0.8) * 0.004;
  const listenLean = 0.03;
  const thinkTilt = 0.08;

  if (presenceTarget === "LISTENING") {
    setPoseTarget(
      new THREE.Vector3(0, 0.01, 0.01),
      new THREE.Euler(-0.03, 0.02, 0),
      new THREE.Euler(-0.015, 0.01, 0),
      new THREE.Euler(-0.01, 0, 0),
      new THREE.Euler(-0.005, 0, 0),
    );
  } else if (presenceTarget === "THINKING") {
    setPoseTarget(
      new THREE.Vector3(0, 0.005, 0),
      new THREE.Euler(-0.02, thinkTilt, 0),
      new THREE.Euler(-0.01, 0.03, 0),
      new THREE.Euler(-0.005, 0.01, 0),
      new THREE.Euler(0, 0, 0),
    );
  } else if (presenceTarget === "SPEAKING") {
    const bob = speaking ? Math.sin(time * 6) * 0.01 : 0;
    setPoseTarget(
      new THREE.Vector3(0, 0.005 + bob, 0),
      new THREE.Euler(-0.02 + bob, 0, 0),
      new THREE.Euler(-0.01 + bob * 0.5, 0, 0),
      new THREE.Euler(-0.005, 0, 0),
      new THREE.Euler(0, 0, 0),
    );
  } else {
    setPoseTarget(
      new THREE.Vector3(0, idleBreath, 0),
      new THREE.Euler(idleSway, 0, 0),
      new THREE.Euler(idleSway * 0.5, 0, 0),
      new THREE.Euler(idleSway * 0.3, 0, 0),
      new THREE.Euler(0, 0, 0),
    );
  }
}

function applyPresencePose(dt, time) {
  if (!vrm) return;
  updatePresencePoseTargets(time);
  const t = Math.min(1, dt * 4);
  presencePose.offset.lerp(presencePoseTarget.offset, t);
  presencePose.head.x = THREE.MathUtils.lerp(presencePose.head.x, presencePoseTarget.head.x, t);
  presencePose.head.y = THREE.MathUtils.lerp(presencePose.head.y, presencePoseTarget.head.y, t);
  presencePose.head.z = THREE.MathUtils.lerp(presencePose.head.z, presencePoseTarget.head.z, t);
  presencePose.neck.x = THREE.MathUtils.lerp(presencePose.neck.x, presencePoseTarget.neck.x, t);
  presencePose.neck.y = THREE.MathUtils.lerp(presencePose.neck.y, presencePoseTarget.neck.y, t);
  presencePose.neck.z = THREE.MathUtils.lerp(presencePose.neck.z, presencePoseTarget.neck.z, t);
  presencePose.chest.x = THREE.MathUtils.lerp(presencePose.chest.x, presencePoseTarget.chest.x, t);
  presencePose.chest.y = THREE.MathUtils.lerp(presencePose.chest.y, presencePoseTarget.chest.y, t);
  presencePose.chest.z = THREE.MathUtils.lerp(presencePose.chest.z, presencePoseTarget.chest.z, t);
  presencePose.spine.x = THREE.MathUtils.lerp(presencePose.spine.x, presencePoseTarget.spine.x, t);
  presencePose.spine.y = THREE.MathUtils.lerp(presencePose.spine.y, presencePoseTarget.spine.y, t);
  presencePose.spine.z = THREE.MathUtils.lerp(presencePose.spine.z, presencePoseTarget.spine.z, t);

  const humanoid = vrm.humanoid;
  if (!humanoid) return;
  const hips = humanoid.getBoneNode("hips");
  const spine = humanoid.getBoneNode("spine");
  const chest = humanoid.getBoneNode("chest") || humanoid.getBoneNode("upperChest");
  const neck = humanoid.getBoneNode("neck");
  const head = humanoid.getBoneNode("head");

  if (hips) {
    hips.position.y = presencePose.offset.y;
    hips.position.z = presencePose.offset.z;
  }
  if (spine) spine.rotation.x = presencePose.spine.x;
  if (chest) chest.rotation.x = presencePose.chest.x;
  if (neck) {
    neck.rotation.x = presencePose.neck.x;
    neck.rotation.y = presencePose.neck.y;
  }
  if (head) {
    head.rotation.x = presencePose.head.x;
    head.rotation.y = presencePose.head.y;
  }
}

// -----------------------------
// Mood logic (persistente)
// -----------------------------
function applyMood() {
  if (!vrm?.expressionManager) return;

  clearEmotionChannels();

  // 1) mood base persistente
  if (mood && mood !== "neutral") {
    const directKey =
      expressionKeys.includes(mood) ? mood :
      expressionKeys.includes(capitalize(mood)) ? capitalize(mood) :
      null;

    if (directKey) {
      setExpression(directKey, 1.0);
    } else {
      applyCompositeMood(mood.toLowerCase());
    }
  }

  // 2) burst encima
  if (burst) {
    const k =
      expressionKeys.includes(burst) ? burst :
      expressionKeys.includes(capitalize(burst)) ? capitalize(burst) : null;

    if (k) setExpression(k, 1.0);
  }

  // Cache relaxed base para wobble
  relaxedBase = vrm?.expressionManager?.getValue("relaxed") ?? 0;
}

function setMood(name) {
  mood = (name || "neutral").trim();
  applyMood();
}

function triggerBurst(name, seconds = 0.8) {
  burst = (name || "").trim();
  burstT = seconds;
  applyMood();
}

function updateBurst(dt) {
  if (!burst) return;
  burstT -= dt;
  if (burstT <= 0) {
    burst = null;
    applyMood();
  }
}

function capitalize(s) {
  if (!s) return s;
  return s[0].toUpperCase() + s.slice(1);
}

// -----------------------------
// Motion (breath / blink / head)
// -----------------------------
function applyMicroGaze(dt) {
  gazeT += dt;
  if (gazeT >= gazeNext) {
    gazeT = 0;
    gazeNext = 0.8 + Math.random() * 1.8;
    gazeOffset.set(
      (Math.random() - 0.5) * 0.15,
      (Math.random() - 0.5) * 0.08,
      0
    );
  }
}

function applyBreathing(vrm, dt) {
  breatheT += dt * 1.2;

  const h = vrm.humanoid;
  const chest = h.getNormalizedBoneNode("chest") || h.getNormalizedBoneNode("spine");
  const upperChest = h.getNormalizedBoneNode("upperChest");
  const head = h.getNormalizedBoneNode("head") || h.getNormalizedBoneNode("neck");

  const chestNode = upperChest || chest;
  const a = Math.sin(breatheT);
  const b = Math.sin(breatheT * 0.5 + 1.7);

  if (chestNode) {
    chestNode.rotation.x = 0.05 + a * 0.03;
    chestNode.rotation.z = b * 0.01;
  }
  if (head) {
    head.rotation.x = 0.02 + a * 0.01;
    head.rotation.y = b * 0.01;
  }
}

function applyAutoBlink(vrm, dt) {
  const em = vrm?.expressionManager;
  if (!em) return;
  if (!expressionKeys.includes("blink")) return;

  blinkT += dt;

  if (!blinking && blinkT >= nextBlink) {
    blinking = true;
    blinkT = 0;
    nextBlink = 1.5 + Math.random() * 2.5;
  }

  if (blinking) {
    const t = blinkT;
    const closeTime = 0.06;
    const openTime = 0.12;

    if (t < closeTime) blinkValue = t / closeTime;
    else if (t < closeTime + openTime) blinkValue = 1 - (t - closeTime) / openTime;
    else {
      blinkValue = 0;
      blinking = false;
      blinkT = 0;
    }

    em.setValue("blink", blinkValue);
  } else {
    em.setValue("blink", 0);
  }
}

function applyHeadTracking(vrm, dt) {
  const h = vrm.humanoid;
  const neck = h.getNormalizedBoneNode("neck");
  const head = h.getNormalizedBoneNode("head");
  const chest = h.getNormalizedBoneNode("chest") || h.getNormalizedBoneNode("spine");

  if (!neck && !head) return;

  const targetYaw = clamp(mouseNDC.x, -1, 1) * 0.45;
  const targetPitch = clamp(mouseNDC.y, -1, 1) * 0.25;

  const k = 1 - Math.pow(0.001, dt);
  headYaw += (targetYaw - headYaw) * k;
  headPitch += (targetPitch - headPitch) * k;

  if (chest) {
    chest.rotation.y = headYaw * 0.12;
    chest.rotation.x = headPitch * 0.08;
  }
  if (neck) {
    neck.rotation.y = headYaw * 0.45;
    neck.rotation.x = headPitch * 0.35;
  }
  if (head) {
    head.rotation.y = headYaw * 0.55;
    head.rotation.x = headPitch * 0.45;
  }
}

// -----------------------------
// LookAt target
// -----------------------------
const lookTarget = new THREE.Object3D();
scene.add(lookTarget);

function updateLookTarget() {
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(mouseNDC, camera);

  const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  const hit = new THREE.Vector3();
  raycaster.ray.intersectPlane(plane, hit);

  hit.y = clamp(hit.y, 1.25, 1.75);
  hit.add(gazeOffset);

  lookTarget.position.copy(hit);
}

// -----------------------------
// VRM load
// -----------------------------
const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));

loader.load(
  "./avatar.vrm",
  (gltf) => {
    VRMUtils.combineSkeletons(gltf.scene);

    vrm = gltf.userData.vrm;
    scene.add(vrm.scene);

    vrm.scene.rotation.y = Math.PI;
    vrm.scene.position.set(0, 0, 0);

    if (vrm.lookAt) vrm.lookAt.target = lookTarget;

    applyRelaxPose(vrm);

    expressionKeys = listExpressions();

    console.log("✅ VRM cargado OK");
    console.log("🎭 Expresiones detectadas:", expressionKeys);

    applyMood();
  },
  undefined,
  (err) => console.error("❌ Error cargando VRM:", err)
);

function applyRelaxPose(vrm) {
  const h = vrm.humanoid;

  const LUA = h.getNormalizedBoneNode("leftUpperArm");
  const RUA = h.getNormalizedBoneNode("rightUpperArm");
  const LLA = h.getNormalizedBoneNode("leftLowerArm");
  const RLA = h.getNormalizedBoneNode("rightLowerArm");
  const CH  = h.getNormalizedBoneNode("chest") || h.getNormalizedBoneNode("spine");
  const HIPS= h.getNormalizedBoneNode("hips");

  if (LUA && RUA) {
    LUA.rotation.x = -0.5;
    RUA.rotation.x = -0.5;
    LUA.rotation.z =  1.20;
    RUA.rotation.z = -1.20;
  }
  if (LLA && RLA) {
    LLA.rotation.x = -0.25;
    RLA.rotation.x = -0.25;
  }
  if (CH) CH.rotation.x = 0.05;
  if (HIPS) HIPS.rotation.x = -0.02;
}

// -----------------------------
// TTS (Fallback WebSpeech)
// -----------------------------
// Nota: lo dejamos como utilidad, pero en FASE B NO lo usamos por defecto.
function speak(text) {
  if (!("speechSynthesis" in window)) return;

  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);

  u.rate = 1.04;
  u.pitch = 1.0;

  u.onstart = () => { speaking = true; };
  u.onend = () => { speaking = false; };
  u.onerror = () => { speaking = false; };

  window.speechSynthesis.speak(u);
}

// -----------------------------
// TTS (Azure WAV + visemes)
// -----------------------------
let audioCtx = null;
let masterGain = null;

// Playback control (para evitar “uno sí / uno no”)
let currentSrc = null;
let currentVisemeTimers = [];

function clearVisemeTimers() {
  for (const id of currentVisemeTimers) clearTimeout(id);
  currentVisemeTimers = [];
}

// Estado boca (targets que se interpolan en animate)
const mouth = { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 };
const mouthTarget = { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 };

function ensureAudio() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    masterGain = audioCtx.createGain();
    masterGain.gain.value = 1.0;
    masterGain.connect(audioCtx.destination);

    audioCtx.onstatechange = () => {
      console.log("[AUDIO] state:", audioCtx.state);
    };
  }
  return audioCtx;
}

function resetMouthTargets() {
  mouthTarget.aa = 0;
  mouthTarget.ih = 0;
  mouthTarget.ou = 0;
  mouthTarget.ee = 0;
  mouthTarget.oh = 0;
}

function setMouthTargetsOnly(key, v) {
  resetMouthTargets();
  if (key) mouthTarget[key] = v;
}

// Viseme id -> mouth key
const VISEME_MAP = {
  aa: [1, 2, 3, 4],
  ih: [5, 6, 7, 8],
  ou: [9, 10, 11, 12],
  ee: [13, 14, 15, 16],
  oh: [17, 18, 19, 20, 21],
};

function visemeToMouth(id) {
  for (const [k, arr] of Object.entries(VISEME_MAP)) {
    if (arr.includes(id)) return k;
  }
  return null;
}

// Programa visemes basados en timestamps (ms) desde inicio de audio
function scheduleVisemes(visemes, startAtAudioTime) {
  if (!audioCtx) return;
  if (!Array.isArray(visemes)) return;

  clearVisemeTimers();

  const sorted = [...visemes].sort((a, b) => (a.t ?? 0) - (b.t ?? 0));

  for (const v of sorted) {
    const mouthKey = visemeToMouth(v.id);
    if (!mouthKey) continue;

    const tSec = (v.t || 0) / 1000;
    const fireAt = startAtAudioTime + tSec;
    const delayMs = Math.max(0, (fireAt - audioCtx.currentTime) * 1000);

    // Ataque
    currentVisemeTimers.push(setTimeout(() => {
      setMouthTargetsOnly(mouthKey, 1.0);
    }, delayMs));

    // Release
    currentVisemeTimers.push(setTimeout(() => {
      setMouthTargetsOnly(null, 0.0);
    }, delayMs + 90));
  }
}

async function playAzureTTS(audioB64, visemes = []) {
  ensureAudio();

  // Re-resume agresivo (Chrome a veces suspende)
  if (audioCtx.state !== "running") {
    try { await audioCtx.resume(); } catch (e) { console.log("[AUDIO] resume fail:", e); }
  }

  // ✅ STOP del audio anterior (esto suele arreglar el “alternado”)
  if (currentSrc) {
    try { currentSrc.onended = null; currentSrc.stop(0); } catch {}
    currentSrc = null;
  }
  clearVisemeTimers();
  setMouthTargetsOnly(null, 0.0);

  // Decode base64 -> ArrayBuffer
  let audioBuffer;
  try {
    const bin = Uint8Array.from(atob(audioB64), c => c.charCodeAt(0));
    audioBuffer = await audioCtx.decodeAudioData(bin.buffer);
  } catch (e) {
    console.log("[TTS] decodeAudioData FAIL:", e);
    speaking = false;
    return;
  }

  const src = audioCtx.createBufferSource();
  src.buffer = audioBuffer;
  src.connect(masterGain);
  currentSrc = src;

  speaking = true;

  // Pequeño offset para scheduling consistente
  const startAt = audioCtx.currentTime + 0.03;
  scheduleVisemes(visemes, startAt);

  src.onended = () => {
    if (currentSrc === src) currentSrc = null;
    speaking = false;
    clearVisemeTimers();
    setMouthTargetsOnly(null, 0.0);
    handleAvatarSpeechEnd();
    if (currentTtsChunk?.is_last && ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "tts_ended", tts_session_id: currentTtsChunk.tts_session_id }));
    }
    currentTtsChunk = null;
    playNextFromQueue();
  };

  try {
    src.start(startAt);
  } catch (e) {
    console.log("[TTS] src.start FAIL:", e);
    speaking = false;
    currentSrc = null;
  }
}


// -----------------------------
// WebSocket
// -----------------------------
const WS_URL = "ws://127.0.0.1:8765";
let ws = null;
const subtitleContainer = document.getElementById("subtitle-overlay");
const presenceIndicator = document.getElementById("presence-indicator");
const subtitleQueue = [];
const subtitleTimers = new Map();
let subtitleId = 0;
const subtitleFadeDelayMs = 4000;
const subtitleRemoveDelayMs = 5000;

function clearSubtitleTimers(id) {
  const timers = subtitleTimers.get(id);
  if (!timers) return;
  clearTimeout(timers.fadeTimer);
  clearTimeout(timers.removeTimer);
  subtitleTimers.delete(id);
}

function renderSubtitleQueue() {
  if (!subtitleContainer) return;
  subtitleContainer.innerHTML = "";
  subtitleQueue.forEach((item) => {
    const line = document.createElement("div");
    line.className = `subtitle-line role-${item.role || "user"} is-visible`;
    line.dataset.subtitleId = String(item.id);
    line.textContent = item.text;
    subtitleContainer.appendChild(line);
  });
}

function removeSubtitle(id) {
  clearSubtitleTimers(id);
  const idx = subtitleQueue.findIndex((item) => item.id === id);
  if (idx >= 0) subtitleQueue.splice(idx, 1);
  renderSubtitleQueue();
}

function removeSubtitlesByRole(role, { fade = false, delay = 0 } = {}) {
  const roleNorm = (role || "").toLowerCase();
  const items = subtitleQueue.filter((item) => item.role === roleNorm);
  if (!items.length) return;

  items.forEach((item) => {
    clearSubtitleTimers(item.id);
    if (fade) {
      const fadeTimer = setTimeout(() => {
        const el = subtitleContainer?.querySelector(`[data-subtitle-id="${item.id}"]`);
        if (el) el.classList.add("is-fading");
      }, delay);

      const removeTimer = setTimeout(() => {
        removeSubtitle(item.id);
      }, delay + 500);

      subtitleTimers.set(item.id, { fadeTimer, removeTimer });
      return;
    }
    removeSubtitle(item.id);
  });
}

function handleAvatarSpeechStart() {
  removeSubtitlesByRole("user", { fade: true });
}

function handleAvatarSpeechEnd() {
  removeSubtitlesByRole("jarvis", { fade: true, delay: 700 });
}

function enqueueSubtitle(role, text) {
  if (!subtitleContainer) return;
  const cleaned = (text || "").trim();
  if (!cleaned) return;

  const id = subtitleId++;
  const roleNorm = (role || "user").toLowerCase();
  subtitleQueue.push({ id, role: roleNorm, text: cleaned });

  while (subtitleQueue.length > 2) {
    const removed = subtitleQueue.shift();
    if (removed) clearSubtitleTimers(removed.id);
  }

  renderSubtitleQueue();

  if (roleNorm !== "user" && roleNorm !== "jarvis") {
    const fadeTimer = setTimeout(() => {
      const el = subtitleContainer.querySelector(`[data-subtitle-id="${id}"]`);
      if (el) el.classList.add("is-fading");
    }, subtitleFadeDelayMs);

    const removeTimer = setTimeout(() => {
      removeSubtitle(id);
    }, subtitleRemoveDelayMs);

    subtitleTimers.set(id, { fadeTimer, removeTimer });
  }
}

// -----------------------------
// TTS queue (chunked playback)
// -----------------------------
const ttsQueue = [];
let currentTtsSession = null;
let currentTtsChunk = null;

function clearTtsQueue() {
  ttsQueue.length = 0;
}

function stopCurrentAudio() {
  if (currentSrc) {
    try { currentSrc.stop(); } catch {}
    currentSrc = null;
  }
  speaking = false;
  currentTtsChunk = null;
  clearVisemeTimers();
  setMouthTargetsOnly(null, 0.0);
}

function playNextFromQueue() {
  if (speaking || ttsQueue.length === 0) return;
  const next = ttsQueue.shift();
  if (!next) return;
  currentTtsChunk = next;
  if (next.subtitle) enqueueSubtitle("jarvis", next.subtitle);
  playAzureTTS(next.audio_b64, Array.isArray(next.visemes) ? next.visemes : []);
}

function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => console.log("[WS] conectado:", WS_URL);
  ws.onclose = () => setTimeout(connectWS, 1000);
  ws.onerror = (e) => console.log("[WS] error:", e);

  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }

    console.log("[WS IN]", msg.type, msg);

    // Estado inicial (mood + opcional mouse)
    if (msg.type === "state") {
      if (typeof msg.emotion === "string") setMood(msg.emotion);
      if (msg.mouse && typeof msg.mouse.x === "number" && typeof msg.mouse.y === "number") {
        mouseNDC.x = msg.mouse.x;
        mouseNDC.y = msg.mouse.y;
      }
      if (typeof msg.conversation_state === "string") {
        applyPresenceState(msg.conversation_state);
        setCameraPresenceState(msg.conversation_state);
      }
      if (msg.conversation_state === "LISTENING") {
        clearTtsQueue();
        stopCurrentAudio();
      }
      return;
    }

    // Mood persistente
    if (msg.type === "emotion" && typeof msg.emotion === "string") {
      const emo = msg.emotion.trim();
      if (emo.toLowerCase() === "surprised") {
        triggerBurst("Surprised", 0.9);
      } else {
        setMood(emo);
      }
      return;
    }

    if (msg.type === "mouse" && typeof msg.x === "number" && typeof msg.y === "number") {
      mouseNDC.x = msg.x;
      mouseNDC.y = msg.y;
      return;
    }

    // Compat: si alguien manda speak, no usamos WebSpeech en FASE B
    if (msg.type === "speak" && typeof msg.text === "string") {
      console.log("[WS] SPEAK recibido, WebSpeech desactivado en FASE B:", msg.text);
      return;
    }

    // say: lo tratamos como fallback/debug (NO hablar por WebSpeech)
    if (msg.type === "say") {
      if (typeof msg.emotion === "string") {
        const emo = msg.emotion.trim();
        if (emo.toLowerCase() === "surprised") triggerBurst("Surprised", 0.9);
        else setMood(emo);
      }
      if (typeof msg.text === "string") {
        console.log("[WS] SAY recibido (sin WebSpeech en FASE B):", msg.text);
        // Si algún día quieres fallback:
        // speak(msg.text);
      }
      return;
    }

    // ✅ tts: Azure WAV + visemes
    if (msg.type === "tts") {
      if (typeof msg.emotion === "string") {
        const emo = msg.emotion.trim();
        if (emo.toLowerCase() === "surprised") triggerBurst("Surprised", 0.9);
        else setMood(emo);
      }

      if (typeof msg.tts_session_id === "string") {
        if (currentTtsSession !== msg.tts_session_id) {
          currentTtsSession = msg.tts_session_id;
          clearTtsQueue();
          stopCurrentAudio();
        }
      }

      if (typeof msg.audio_b64 === "string") {
        ttsQueue.push({
          audio_b64: msg.audio_b64,
          visemes: msg.visemes,
          subtitle: typeof msg.subtitle === "string" ? msg.subtitle : "",
          tts_session_id: msg.tts_session_id,
          is_last: Boolean(msg.is_last),
        });
        handleAvatarSpeechStart();
        if (!speaking) playNextFromQueue();
      }
      return;
    }

    if (msg.type === "tts_cancel") {
      clearTtsQueue();
      stopCurrentAudio();
      return;
    }

    if (msg.type === "subtitle" && typeof msg.text === "string") {
      enqueueSubtitle(msg.role, msg.text);
      return;
    }
  };
}

connectWS();

window.addEventListener("keydown", (event) => {
  if (event.key?.toLowerCase() === "c") {
    cameraDynamicEnabled = !cameraDynamicEnabled;
    console.log(`[CAM] dynamic ${cameraDynamicEnabled ? "ON" : "OFF"}`);
  }
});

// -----------------------------
// Resize + loop
// -----------------------------
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();

  applyMicroGaze(dt);
  updateLookTarget();
  updateBurst(dt);
  updatePresence(dt);
  applyPresencePose(dt, clock.elapsedTime);
  updateCameraRig(dt, clock.elapsedTime);

  if (vrm) {
    applyBreathing(vrm, dt);
    applyAutoBlink(vrm, dt);
    applyHeadTracking(vrm, dt);

    // Boca (visemes Azure) - smoothing por frame
    const em = vrm.expressionManager;
    if (em) {
      const k = 1 - Math.pow(0.001, dt);

      for (const key of ["aa", "ih", "ou", "ee", "oh"]) {
        if (!expressionKeys.includes(key)) continue;
        mouth[key] += (mouthTarget[key] - mouth[key]) * k;
        em.setValue(key, clamp(mouth[key], 0, 1));
      }
    }

    // micro variación del mood
    if (vrm?.expressionManager && mood !== "neutral") {
      moodWobbleT += dt;
      const w = 0.03 * Math.sin(moodWobbleT * 1.1);

      const em2 = vrm.expressionManager;

      if (expressionKeys.includes("relaxed")) {
        em2.setValue("relaxed", clamp(relaxedBase + w, 0, 1));
      }
    }

    vrm.update(dt);
  }

  renderer.render(scene, camera);
}
animate();
