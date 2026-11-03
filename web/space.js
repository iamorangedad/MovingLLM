import * as THREE from "three";

const TYPE_COLOR = {
  wardrobe: 0x6b4c38,
  sofa: 0x3f6f8f,
  bed: 0x8a7058,
  desk: 0x5f8f73,
  table: 0x5f8f73,
  bookshelf: 0x6e5a45,
  chair: 0x4f7f72,
  drawer: 0x4f7f72,
  tv_stand: 0x4f7f72,
  other: 0x4f7f72,
};

const BOX_COLOR = 0xc9a36a;
const FRAGILE_COLOR = 0xd46a8a;
const WALL_COLOR = 0xd9d3cb;
const FLOOR_COLOR = 0xc4b5a0;
const SELECTED_EMISSIVE = 0x8a4b24;

export function createSpace(canvas, hooks = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf3eee7);
  const camera = new THREE.PerspectiveCamera(42, 1, 1, 30000);
  scene.add(new THREE.AmbientLight(0xffffff, 0.72));
  const sun = new THREE.DirectionalLight(0xffffff, 1.15);
  sun.position.set(180, 420, 260);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xfff4e8, 0.35);
  fill.position.set(-220, 180, -80);
  scene.add(fill);

  const root = new THREE.Group();
  scene.add(root);
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  const dragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const hitPoint = new THREE.Vector3();
  const target = new THREE.Vector3();
  let movable = [];
  let selected = null;
  let dragging = null;
  let orbiting = false;
  let lastX = 0;
  let lastY = 0;
  let grabX = 0;
  let grabZ = 0;
  let yaw = -0.85;
  let pitch = 0.62;
  let distance = 900;
  let framedKey = "";
  let lastMode = "";
  let lastLayout = null;

  function resize() {
    const width = canvas.clientWidth || 1;
    const height = canvas.clientHeight || 1;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function updateCamera() {
    const cosPitch = Math.cos(pitch);
    camera.position.set(
      target.x + distance * Math.sin(yaw) * cosPitch,
      target.y + distance * Math.sin(pitch),
      target.z + distance * Math.cos(yaw) * cosPitch
    );
    camera.lookAt(target);
  }

  function frameBox(x, y, z, width, height, depth, key, view = {}) {
    target.set(x + width / 2, y + Math.min(height * 0.28, 80), z + depth / 2);
    distance = Math.max(width, height, depth, 120) * (view.scale || 1.65);
    yaw = view.yaw === undefined ? -0.85 : view.yaw;
    pitch = view.pitch === undefined ? 0.62 : view.pitch;
    framedKey = key;
    updateCamera();
  }

  function clearRoot() {
    root.traverse((node) => {
      if (node.geometry) node.geometry.dispose();
      if (node.material) {
        if (node.material.map) node.material.map.dispose();
        node.material.dispose();
      }
    });
    root.clear();
    movable = [];
    selected = null;
  }

  function colorFor(item) {
    if (item.fragile) return FRAGILE_COLOR;
    if (item.kind === "box") return BOX_COLOR;
    return TYPE_COLOR[item.furniture_type] || TYPE_COLOR.other;
  }

  function addBox(item, options) {
    const material = new THREE.MeshStandardMaterial({
      color: options.color,
      roughness: 0.78,
      metalness: 0.02,
    });
    if (options.polygonOffset) {
      material.polygonOffset = true;
      material.polygonOffsetFactor = 1;
      material.polygonOffsetUnits = 1;
    }
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(item.width_cm, item.height_cm, item.depth_cm),
      material
    );
    mesh.position.set(
      item.x_cm + item.width_cm / 2,
      item.y_cm + item.height_cm / 2,
      item.z_cm + item.depth_cm / 2
    );
    mesh.userData = {
      movable: Boolean(options.movable),
      server: options.server || item,
      width_cm: item.width_cm,
      depth_cm: item.depth_cm,
    };
    if (options.label) {
      const sprite = makeLabel(options.label);
      sprite.position.set(0, item.height_cm / 2 + 14, 0);
      sprite.raycast = () => {};
      mesh.add(sprite);
    }
    root.add(mesh);
    if (options.movable) movable.push(mesh);
    return mesh;
  }

  function showCargo(layout) {
    const keep = selected && selected.userData.server.id;
    clearRoot();
    const width = layout.width_cm;
    const height = layout.height_cm;
    const depth = layout.length_cm;
    addBox(
      { x_cm: 0, y_cm: -2, z_cm: 0, width_cm: width, height_cm: 2, depth_cm: depth },
      { color: 0x8a7563, polygonOffset: true }
    );
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(width, height, depth)),
      new THREE.LineBasicMaterial({ color: 0x3a342e })
    );
    edges.position.set(width / 2, height / 2, depth / 2);
    root.add(edges);
    const door = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.PlaneGeometry(width, height)),
      new THREE.LineBasicMaterial({ color: 0x9a5b32 })
    );
    door.position.set(width / 2, height / 2, depth + 1);
    root.add(door);
    lastMode = "cargo";
    lastLayout = layout;
    for (const item of layout.placements) {
      addBox(item, { color: colorFor(item), movable: true, server: item, label: shortName(item.name) });
    }
    stageHeld(layout.held || [], -36);
    const key = `cargo:${width}:${height}:${depth}`;
    if (key !== framedKey) frameBox(0, 0, 0, width, height, depth, key);
    if (keep) select(keep);
  }

  function showHome(layout) {
    const keep = selected && selected.userData.server.id;
    clearRoot();
    const bounds = emptyBounds();
    for (const solid of layout.shell.solids) {
      addBox(solid, {
        color: solid.kind === "floor" ? FLOOR_COLOR : WALL_COLOR,
        polygonOffset: solid.kind === "floor",
      });
      includeBounds(bounds, solid);
    }
    for (const room of layout.shell.interiors) {
      const sprite = makeLabel(room.name);
      sprite.position.set(room.x_cm + room.width_cm / 2, 24, room.z_cm + room.depth_cm / 2);
      root.add(sprite);
    }
    for (const item of layout.placements) {
      addBox(item, { color: colorFor(item), movable: true, server: item, label: shortName(item.name) });
      includeBounds(bounds, item);
    }
    const anchor = Number.isFinite(bounds.minX) ? bounds.minX - 36 : -36;
    stageHeld(layout.held || [], anchor);
    lastMode = "home";
    lastLayout = layout;
    const key = (layout.shell.rooms || [])
      .map((room) => `${room.name}:${room.x_cm}:${room.z_cm}:${room.width_cm}:${room.depth_cm}`)
      .join("|");
    if (key !== framedKey && Number.isFinite(bounds.minX)) {
      frameBox(
        bounds.minX,
        bounds.minY,
        bounds.minZ,
        bounds.maxX - bounds.minX,
        Math.max(bounds.maxY - bounds.minY, 80),
        bounds.maxZ - bounds.minZ,
        key,
        { scale: 1.25, pitch: 0.95, yaw: -0.65 }
      );
    }
    if (keep) select(keep);
  }

  function stageHeld(items, anchorX) {
    let cursor = 0;
    for (const item of items) {
      const visual = {
        ...item,
        x_cm: anchorX - item.width_cm,
        y_cm: 0,
        z_cm: cursor,
      };
      addBox(visual, {
        color: colorFor(item),
        movable: true,
        server: item,
        label: shortName(item.name),
      });
      cursor += item.depth_cm + 18;
    }
  }

  function select(id) {
    selected = movable.find((mesh) => mesh.userData.server.id === id) || null;
    for (const mesh of movable) {
      const active = mesh === selected;
      mesh.material.emissive.setHex(active ? SELECTED_EMISSIVE : 0x000000);
      mesh.material.emissiveIntensity = active ? 0.45 : 0;
    }
    if (hooks.onSelect) hooks.onSelect(selected ? selected.userData.server : null);
    return selected ? selected.userData.server : null;
  }

  function selectedItem() {
    return selected ? selected.userData.server : null;
  }

  function setPointer(event) {
    const rect = canvas.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  function ownerOf(object) {
    let node = object;
    while (node && node !== root) {
      if (node.userData && node.userData.movable) return node;
      node = node.parent;
    }
    return null;
  }

  function pickHit() {
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(movable, true);
    for (const hit of hits) {
      const mesh = ownerOf(hit.object);
      if (mesh) return { mesh, point: hit.point };
    }
    return null;
  }

  function cursorSpot() {
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(root.children, true);
    for (const hit of hits) {
      const mesh = ownerOf(hit.object);
      if (!mesh || mesh === dragging) continue;
      return { x: hit.point.x, z: hit.point.z, y: hit.point.y };
    }
    dragPlane.constant = 0;
    if (!raycaster.ray.intersectPlane(dragPlane, hitPoint)) return null;
    return { x: hitPoint.x, z: hitPoint.z, y: 0 };
  }

  canvas.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    canvas.setPointerCapture(event.pointerId);
    setPointer(event);
    const picked = pickHit();
    if (picked) {
      const mesh = picked.mesh;
      select(mesh.userData.server.id);
      dragging = mesh;
      grabX = picked.point.x - (mesh.position.x - mesh.userData.width_cm / 2);
      grabZ = picked.point.z - (mesh.position.z - mesh.userData.depth_cm / 2);
      canvas.classList.add("dragging");
      return;
    }
    orbiting = true;
    lastX = event.clientX;
    lastY = event.clientY;
    canvas.classList.add("dragging");
  });

  canvas.addEventListener("pointermove", (event) => {
    setPointer(event);
    if (dragging) {
      const spot = cursorSpot();
      if (!spot) return;
      const width = dragging.userData.width_cm;
      const depth = dragging.userData.depth_cm;
      const height = dragging.userData.server.height_cm;
      dragging.position.x = spot.x - grabX + width / 2;
      dragging.position.z = spot.z - grabZ + depth / 2;
      dragging.position.y = spot.y + height / 2;
      return;
    }
    if (!orbiting) return;
    yaw -= (event.clientX - lastX) * 0.005;
    pitch = clamp(pitch + (event.clientY - lastY) * 0.004, 0.12, 1.35);
    lastX = event.clientX;
    lastY = event.clientY;
    updateCamera();
  });

  function endPointer(event) {
    const mesh = dragging;
    dragging = null;
    orbiting = false;
    canvas.classList.remove("dragging");
    if (event && event.pointerId !== undefined && canvas.hasPointerCapture(event.pointerId)) {
      canvas.releasePointerCapture(event.pointerId);
    }
    if (!mesh || !hooks.onCommit) return;
    const server = mesh.userData.server;
    hooks.onCommit({
      id: server.id,
      x_cm: round(mesh.position.x - mesh.userData.width_cm / 2),
      z_cm: round(mesh.position.z - mesh.userData.depth_cm / 2),
      yaw_quarters: server.yaw_quarters || 0,
      intent: "drag",
    });
  }

  canvas.addEventListener("pointerup", endPointer);
  canvas.addEventListener("pointercancel", endPointer);
  canvas.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      distance = clamp(distance * (event.deltaY > 0 ? 1.08 : 0.92), 80, 9000);
      updateCamera();
    },
    { passive: false }
  );

  window.addEventListener("keydown", (event) => {
    if (event.target && event.target.closest && event.target.closest("input, textarea")) return;
    if (event.key !== "r" && event.key !== "R") return;
    const server = selectedItem();
    if (!server || !hooks.onCommit) return;
    event.preventDefault();
    hooks.onCommit({
      id: server.id,
      x_cm: server.x_cm,
      z_cm: server.z_cm,
      yaw_quarters: ((server.yaw_quarters || 0) + 1) % 4,
      intent: "rotate",
    });
  });

  const observer = new ResizeObserver(() => resize());
  observer.observe(canvas.parentElement || canvas);
  resize();
  updateCamera();

  let running = true;
  function animate() {
    if (!running) return;
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
  }
  animate();

  return {
    showCargo,
    showHome,
    resize,
    select,
    selectedItem,
    frame() {
      framedKey = "";
      if (lastMode === "cargo" && lastLayout) showCargo(lastLayout);
      if (lastMode === "home" && lastLayout) showHome(lastLayout);
    },
  };
}

function makeLabel(text) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  context.fillStyle = "rgba(28, 25, 21, 0.78)";
  roundRect(context, 8, 8, 240, 48, 12);
  context.fill();
  context.fillStyle = "#fffdf9";
  context.font = "28px sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(String(text).slice(0, 10), 128, 32);
  const material = new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas),
    transparent: true,
    depthTest: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(78, 20, 1);
  sprite.raycast = () => {};
  return sprite;
}

function roundRect(context, x, y, width, height, radius) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.arcTo(x + width, y, x + width, y + height, radius);
  context.arcTo(x + width, y + height, x, y + height, radius);
  context.arcTo(x, y + height, x, y, radius);
  context.arcTo(x, y, x + width, y, radius);
  context.closePath();
}

function shortName(name) {
  return String(name).split("（")[0];
}

function emptyBounds() {
  return { minX: Infinity, minY: Infinity, minZ: Infinity, maxX: -Infinity, maxY: -Infinity, maxZ: -Infinity };
}

function includeBounds(bounds, item) {
  bounds.minX = Math.min(bounds.minX, item.x_cm);
  bounds.minY = Math.min(bounds.minY, item.y_cm);
  bounds.minZ = Math.min(bounds.minZ, item.z_cm);
  bounds.maxX = Math.max(bounds.maxX, item.x_cm + item.width_cm);
  bounds.maxY = Math.max(bounds.maxY, item.y_cm + item.height_cm);
  bounds.maxZ = Math.max(bounds.maxZ, item.z_cm + item.depth_cm);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function round(value) {
  return Math.round(value * 100) / 100;
}
