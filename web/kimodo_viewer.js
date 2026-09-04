/**
 * Kimodo 3D Motion Preview — Three.js skeleton animation viewer
 * Renders joint positions + bone connections with frame playback
 */

import { app } from "../../scripts/app.js";

const VIEWER_HTML = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { margin:0; overflow:hidden; background:#1a1a2e; font-family:monospace; }
  #c { width:100%; height:100vh; display:block; }
  #controls {
    position:absolute; bottom:8px; left:8px; right:8px;
    display:flex; align-items:center; gap:6px;
    background:rgba(0,0,0,0.6); padding:6px 10px; border-radius:6px;
  }
  #controls button { background:#334; color:#ccc; border:1px solid #556; border-radius:4px; padding:4px 10px; cursor:pointer; font-size:12px; }
  #controls button:hover { background:#445; }
  #slider { flex:1; }
  #info { position:absolute; top:8px; left:8px; color:#aaa; font-size:11px; line-height:1.5; }
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="info">Waiting for motion data...</div>
<div id="controls" style="display:none">
  <button id="playBtn">▶</button>
  <input id="slider" type="range" min="0" max="1" step="1" value="0">
  <span id="frameLabel" style="color:#aaa;font-size:11px;min-width:60px">0/0</span>
</div>
<script type="importmap">
{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.171.0/build/three.module.js", "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.171.0/examples/jsm/" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias:true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(0x1a1a2e);

const scene = new THREE.Scene();
scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(2, 4, 3);
scene.add(dirLight);

// Ground grid
const grid = new THREE.GridHelper(10, 20, 0x334455, 0x222233);
scene.add(grid);

const camera = new THREE.PerspectiveCamera(50, 1, 0.01, 100);
camera.position.set(0, 1.5, 4);
const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 0.9, 0);
controls.update();

let jointMeshes = [];
let boneMeshes = [];
let motionData = null;
let currentFrame = 0;
let playing = false;
let lastTime = 0;

const slider = document.getElementById('slider');
const frameLabel = document.getElementById('frameLabel');
const playBtn = document.getElementById('playBtn');
const infoEl = document.getElementById('info');
const controlsEl = document.getElementById('controls');

playBtn.onclick = () => { playing = !playing; playBtn.textContent = playing ? '⏸' : '▶'; };
slider.oninput = () => { currentFrame = parseInt(slider.value); updatePose(); };

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== w || canvas.height !== h) {
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
}

function clearScene() {
  jointMeshes.forEach(m => scene.remove(m));
  boneMeshes.forEach(m => scene.remove(m));
  jointMeshes = [];
  boneMeshes = [];
}

function buildSkeleton(numJoints, parents) {
  clearScene();
  const jointGeo = new THREE.SphereGeometry(0.015, 8, 8);
  const jointMat = new THREE.MeshStandardMaterial({ color: 0x00dd77 });
  const boneGeo = new THREE.CylinderGeometry(0.006, 0.006, 1, 6);
  boneGeo.translate(0, 0.5, 0);
  const boneMat = new THREE.MeshStandardMaterial({ color: 0x6688cc });

  for (let j = 0; j < numJoints; j++) {
    const m = new THREE.Mesh(jointGeo, jointMat);
    scene.add(m);
    jointMeshes.push(m);
  }
  for (let j = 0; j < numJoints; j++) {
    if (parents[j] >= 0) {
      const m = new THREE.Mesh(boneGeo, boneMat);
      scene.add(m);
      boneMeshes.push({ mesh: m, child: j, parent: parents[j] });
    }
  }
}

function updatePose() {
  if (!motionData) return;
  const { joints, parents, numJoints, numFrames } = motionData;
  const f = Math.min(currentFrame, numFrames - 1);
  const offset = f * numJoints * 3;

  for (let j = 0; j < numJoints; j++) {
    const x = joints[offset + j * 3];
    const y = joints[offset + j * 3 + 1];
    const z = joints[offset + j * 3 + 2];
    jointMeshes[j].position.set(x, y, z);
  }

  for (const b of boneMeshes) {
    const cp = jointMeshes[b.child].position;
    const pp = jointMeshes[b.parent].position;
    const dir = new THREE.Vector3().subVectors(cp, pp);
    const len = dir.length();
    b.mesh.position.copy(pp);
    b.mesh.scale.set(1, len, 1);
    if (len > 0.001) {
      b.mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    }
  }

  frameLabel.textContent = f + '/' + (numFrames - 1);
  slider.value = f;
}

function animate(time) {
  requestAnimationFrame(animate);
  resize();

  if (playing && motionData) {
    const dt = (time - lastTime) / 1000;
    if (dt > 1 / motionData.fps) {
      lastTime = time;
      currentFrame = (currentFrame + 1) % motionData.numFrames;
      updatePose();
    }
  }

  controls.update();
  renderer.render(scene, camera);
}
requestAnimationFrame(animate);

window.addEventListener('message', (e) => {
  if (e.data?.type === 'RESIZE') { resize(); return; }
  if (e.data?.type === 'LOAD_MOTION') {
    const d = e.data.motionData;
    motionData = {
      joints: new Float32Array(d.joints),
      parents: d.parents,
      numJoints: d.num_joints,
      numFrames: d.num_frames,
      fps: d.fps || 30,
      jointNames: d.joint_names || [],
    };

    buildSkeleton(motionData.numJoints, motionData.parents);
    slider.max = motionData.numFrames - 1;
    currentFrame = 0;
    playing = true;
    playBtn.textContent = '⏸';
    lastTime = performance.now();
    updatePose();

    // Center camera on root trajectory
    const midFrame = Math.floor(motionData.numFrames / 2);
    const off = midFrame * motionData.numJoints * 3;
    const cx = motionData.joints[off], cy = motionData.joints[off + 1], cz = motionData.joints[off + 2];
    controls.target.set(cx, cy + 0.3, cz);
    camera.position.set(cx, cy + 1.5, cz + 3.5);
    controls.update();

    controlsEl.style.display = 'flex';
    const text = d.text || '';
    infoEl.textContent = text + '  (' + motionData.numFrames + ' frames, ' + motionData.numJoints + ' joints)';
  }
});

window.parent.postMessage({ type: 'VIEWER_READY' }, '*');
</script>
</body>
</html>`;

app.registerExtension({
  name: "kimodo.motionpreview3d",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name !== "Kimodo_Preview3D") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

      const iframe = document.createElement("iframe");
      iframe.style.width = "100%";
      iframe.style.height = "100%";
      iframe.style.border = "none";
      iframe.style.backgroundColor = "#1a1a2e";
      iframe.style.display = "block";

      const blob = new Blob([VIEWER_HTML], { type: "text/html" });
      const blobUrl = URL.createObjectURL(blob);
      iframe.src = blobUrl;
      iframe.addEventListener("load", () => { iframe._blobUrl = blobUrl; });

      const widget = this.addDOMWidget("preview3d", "KIMODO_3D_PREVIEW", iframe, {
        getValue() { return ""; },
        setValue(v) { },
      });
      widget.computeSize = function (width) {
        const w = width || 512;
        return [w, w * 1.0];
      };
      widget.element = iframe;
      this.motionViewerIframe = iframe;
      this.motionViewerReady = false;

      window.addEventListener("message", (event) => {
        if (event.data?.type === "VIEWER_READY") this.motionViewerReady = true;
      });

      const notifyResize = () => {
        if (iframe.contentWindow) {
          const rect = iframe.getBoundingClientRect();
          iframe.contentWindow.postMessage({ type: "RESIZE", width: rect.width, height: rect.height }, "*");
        }
      };
      this.onResize = function (size) {
        const isVue = iframe.closest("[data-node-id]") !== null;
        if (!isVue && size?.[1]) {
          iframe.style.height = Math.max(200, size[1] - 70) + "px";
        }
        requestAnimationFrame(notifyResize);
      };
      let resizeTimeout = null;
      const ro = new ResizeObserver(() => {
        if (resizeTimeout) clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(notifyResize, 50);
      });
      ro.observe(iframe);
      const origRemoved = this.onRemoved;
      this.onRemoved = function () {
        ro.disconnect();
        if (iframe._blobUrl) URL.revokeObjectURL(iframe._blobUrl);
        origRemoved?.apply(this, arguments);
      };

      this.setSize([512, 582]);

      const onExecuted = this.onExecuted;
      this.onExecuted = function (message) {
        onExecuted?.apply(this, arguments);
        if (message?.motion_json?.[0]) {
          try {
            const motionData = JSON.parse(message.motion_json[0]);
            const send = () => {
              if (iframe.contentWindow) {
                iframe.contentWindow.postMessage({ type: "LOAD_MOTION", motionData, timestamp: Date.now() }, "*");
              }
            };
            if (this.motionViewerReady) send();
            else {
              const iv = setInterval(() => { if (this.motionViewerReady) { clearInterval(iv); send(); } }, 50);
              setTimeout(() => { clearInterval(iv); send(); }, 2000);
            }
          } catch (e) { console.error("[Kimodo] Failed to parse motion:", e); }
        }
      };

      return r;
    };
  },
});

console.log("[Kimodo] 3D viewer extension loaded");
