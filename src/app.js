// Livingston Network Map — 3D scene.
// Uses the vendored 3d-force-graph UMD (its own three r168 internally) plus
// this module's three r168 for custom meshes. Cross-instance is safe: three
// duck-types via .isMesh/.isObject3D flags, never instanceof.
import * as THREE from '../vendor/three.module.min.js';

const PALETTES = {
  midnight: {
    bg: '#0a0f1e', ground: '#111a30', ink: '#1c2942',
    road: '#2a3a5e', roadMain: '#42588a', bldg: '#22304f', water: '#1d3a5f',
    table: '#2b2119', frame: '#c9c2b4',
    hub: '#ffb454', directory: '#2dd4bf', built: '#7aa2ff', listed: '#94a0b4',
    linkLists: 'rgba(45,212,191,0.20)', linkBuilt: 'rgba(255,180,84,0.55)',
    linkOperates: 'rgba(255,180,84,0.85)', linkSister: 'rgba(122,162,255,0.55)',
    label: '#eef2fa', ringLine: 'rgba(160,180,220,0.16)', ringText: '#7f8cab'
  },
  dawn: {
    bg: '#f2ece1', ground: '#e6ddcc', ink: '#d8cdb8',
    road: '#bfb190', roadMain: '#9d8a5e', bldg: '#cfc2a4', water: '#7fa8b4',
    table: '#8a6b48', frame: '#f6f1e6',
    hub: '#b3541e', directory: '#0f766e', built: '#1d4ed8', listed: '#68717f',
    linkLists: 'rgba(15,118,110,0.25)', linkBuilt: 'rgba(179,84,30,0.55)',
    linkOperates: 'rgba(179,84,30,0.85)', linkSister: 'rgba(29,78,216,0.5)',
    label: '#221c14', ringLine: 'rgba(60,50,30,0.18)', ringText: '#8a7f68'
  },
  print: {
    bg: '#faf8f4', ground: '#efeae2', ink: '#e2dbd0',
    road: '#ddd5c9', roadMain: '#c6bcab', bldg: '#e6dfd4', water: '#c9d4da',
    table: '#9b8a72', frame: '#ffffff',
    hub: '#181716', directory: '#00629f', built: '#5c5650', listed: '#8d867e',
    linkLists: 'rgba(0,98,159,0.22)', linkBuilt: 'rgba(24,23,22,0.5)',
    linkOperates: 'rgba(24,23,22,0.8)', linkSister: 'rgba(0,98,159,0.5)',
    label: '#181716', ringLine: 'rgba(24,23,22,0.14)', ringText: '#9a938a'
  }
};

const NODE_DIMS = { hub: { h: 26, w: 7, size: 9 }, directory: { h: 18, w: 5.5, size: 7 },
  built: { h: 12, w: 4.5, size: 5 }, listed: { h: 5, w: 2.6, size: 2.6 } };

// Listed places render as map-pins, colored by category group.
const CAT_GROUP = {
  eats: 'eats',
  square: 'town', printing: 'town', history: 'town', events: 'town', playground: 'town',
  boating: 'water', fishing: 'water', swimming: 'water', waterfall: 'water',
  hiking: 'land', outdoors: 'land', camping: 'land', biking: 'land', overlook: 'land', wildlife: 'land'
};
const CAT_COLORS = { eats: '#c0442e', town: '#8b5cf6', water: '#1990b8', land: '#5b8a2e' };

// Radius (scene units) of the regional map edge; recomputed from region.json
// at load. Places beyond the region sit on a single band just past the edge.
let FAR_R = 4300;

const state = {
  mode: 'city', palette: 'dawn', glyph: 'buildings',
  labels: 'focus', motion: 'full'
};
if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  state.motion = 'calm';
}

function pal() { return PALETTES[state.palette]; }


function fatal(msg) {
  const el = document.getElementById('graph');
  el.innerHTML = '<p class="load-error">' + msg + '</p>';
  throw new Error(msg);
}
if (typeof ForceGraph3D === 'undefined') {
  fatal('The 3D library failed to load — hard-refresh (Ctrl+F5). If this persists, vendor/3d-force-graph.min.js is not being served.');
}
let graph;
try {
  // Orbit controls, not the library's default trackball: trackball tumbles
  // freely and ignores the pan/zoom-only lockdown in applyControls.
  graph = ForceGraph3D({ controlType: 'orbit' })(document.getElementById('graph'));
} catch (e) {
  fatal('WebGL is unavailable in this browser (' + e.message + '). Enable graphics acceleration in the browser settings, or view on another device.');
}
window.__graph = graph; // probe handle for automated verification
let net = null;
let city = null; // parsed data/city.json (vector fallback, unused when imagery loads)
let sat = null; // parsed data/satellite.json bounds (downtown z17 inset)
let satTexture = null; // THREE.Texture of data/satellite.jpg
let region = null; // parsed data/region.json bounds (30-mile z13 base)
let regionTexture = null; // THREE.Texture of data/region.jpg
let visitors = null; // parsed data/visitors.json {domain: {uniques,...}}
let decor = null; // THREE.Group holding the table + map + rings

// Same local frame as scripts/geo.py: scene units east/south of the square.
const LAT0 = 36.3839, LON0 = -85.3227, M_PER_UNIT = 12.0;
function toLocal(lat, lon) {
  return [
    (lon - LON0) * Math.cos(LAT0 * Math.PI / 180) * 111320.0 / M_PER_UNIT,
    -(lat - LAT0) * 110540.0 / M_PER_UNIT
  ];
}

function visitorsFor(n) {
  if (!visitors || !n.url) return null;
  let host;
  try { host = new URL(n.url).hostname.replace(/^www\./, ''); } catch { return null; }
  // Subpath sites on the Obscura host are not obscura's own traffic.
  if (host === 'sites.obscurastudio.design') return null;
  return visitors[host] || null;
}

// Owned-site tower height from weekly unique visitors, log-normalized against
// the busiest site so the whole range differentiates (a sqrt scale saturated:
// 63 and 1152 uniques both hit the cap). Floor keeps zero/no-data sites
// visible; the busiest site defines the 40-unit ceiling.
let maxUniques = 0;
function computeMaxUniques() {
  maxUniques = Math.max(1, ...Object.values(visitors || {})
    .map(v => v.uniques || 0));
}
function heightFor(n) {
  if (n.type === 'listed') return NODE_DIMS.listed.h;
  const v = visitorsFor(n);
  if (!v || v.uniques == null || !v.uniques) return 5;
  return 5 + 35 * (Math.log1p(v.uniques) / Math.log1p(maxUniques));
}

// The online layer stands on the table as a small "campus" southeast of the
// map — bearings 85–168° hold no out-of-town places, so the plot is clear.
// Hub in back, directories mid row, built sites front row, all grounded.
const CAMPUS = { cx: 240, hubZ: 148, dirZ: 180, builtZ: 212, dirGap: 24, builtGap: 19 };

function positionNodes() {
  const virtualDirs = net.nodes.filter(n => n.type === 'directory' && !n.geo);
  const virtualBuilt = net.nodes.filter(n => n.type === 'built' && !n.geo);
  net.nodes.forEach(n => {
    if (state.mode !== 'city') { n.fx = n.fy = n.fz = undefined; return; }
    // Real spot on the city map — glyph base sits on the ground.
    if (n.geo) { n.fx = n.geo[0]; n.fz = n.geo[1]; n.fy = 2; return; }
    if (n.type === 'hub') { n.fx = CAMPUS.cx; n.fz = CAMPUS.hubZ; n.fy = 2; return; }
    let r, angle, y;
    if (n.type === 'directory') {
      const i = virtualDirs.indexOf(n);
      n.fx = CAMPUS.cx + (i - (virtualDirs.length - 1) / 2) * CAMPUS.dirGap;
      n.fz = CAMPUS.dirZ; n.fy = 2; return;
    } else if (n.type === 'built') {
      const i = virtualBuilt.indexOf(n);
      n.fx = CAMPUS.cx + (i - (virtualBuilt.length - 1) / 2) * CAMPUS.builtGap;
      n.fz = CAMPUS.builtZ; n.fy = 2; return;
    } else if ((n.city || '').toLowerCase() === 'livingston') {
      // In-town place that would not geocode: honest fallback ring at the
      // edge of downtown rather than a fake address.
      r = 62; y = 2; angle = n.bearing || 0;
    } else {
      // Beyond the 30-mile map (or failed to geocode): band past the edge.
      r = FAR_R; y = 2; angle = n.bearing || 0;
    }
    const t = angle * Math.PI / 180;
    n.fx = r * Math.sin(t);
    n.fz = -r * Math.cos(t);
    n.fy = y;
  });
}

function makeLabelSprite(text, color, scale) {
  // Rendered at 2x for crispness; world height 7.5 units per unit scale.
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d');
  const font = '600 56px "Segoe UI", system-ui, sans-serif';
  ctx.font = font;
  const w = Math.ceil(ctx.measureText(text).width) + 40;
  c.width = w; c.height = 88;
  ctx.font = font;
  ctx.textBaseline = 'middle';
  // Heavy halo for legibility on satellite imagery.
  ctx.strokeStyle = state.palette === 'midnight' ? 'rgba(5,8,18,0.95)' : 'rgba(255,255,255,0.95)';
  ctx.lineWidth = 14;
  ctx.lineJoin = 'round';
  ctx.strokeText(text, 20, 44);
  ctx.fillStyle = color;
  ctx.fillText(text, 20, 44);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthWrite: false }));
  sprite.scale.set(w / 88 * 7.5 * scale, 7.5 * scale, 1);
  return sprite;
}

function nodeObject(n) {
  const p = pal();
  const dims = NODE_DIMS[n.type] || NODE_DIMS.listed;
  const color = p[n.type] || p.listed;
  const h = heightFor(n);
  const group = new THREE.Group();
  if (n.type === 'listed') {
    // Map-pin: cream peg with a category-colored head — reads as "a place on
    // the map", distinct from our blue/teal buildings.
    const headColor = CAT_COLORS[CAT_GROUP[n.category]] || p.listed;
    const peg = new THREE.Mesh(
      new THREE.CylinderGeometry(0.5, 0.95, 7, 10),
      new THREE.MeshLambertMaterial({ color: p.frame })
    );
    peg.position.y = 3.5;
    group.add(peg);
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(2.6, 16, 12),
      new THREE.MeshLambertMaterial({ color: headColor })
    );
    head.position.y = 8;
    group.add(head);
    const sprite = makeLabelSprite(n.name, p.label, 0.8);
    sprite.position.y = 14.5;
    sprite.visible = state.labels === 'all';
    group.add(sprite);
    group.userData.labelSprite = sprite;
    group.userData.nodeType = n.type;
    return group;
  }
  if (state.glyph === 'buildings') {
    const geo = new THREE.BoxGeometry(dims.w, h, dims.w);
    const mat = new THREE.MeshLambertMaterial({ color });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.y = h / 2 - 2;
    group.add(mesh);
  } else {
    const geo = new THREE.SphereGeometry(dims.size, 16, 12);
    const mat = new THREE.MeshLambertMaterial({ color });
    group.add(new THREE.Mesh(geo, mat));
  }
  // Every node gets a label sprite; listed-node labels in "focus" density are
  // revealed by camera proximity (updateLabelVisibility) instead of never built.
  const scale = n.type === 'listed' ? 0.55 : (n.type === 'hub' ? 1.15 : 0.85);
  const sprite = makeLabelSprite(n.name, p.label, scale);
  sprite.position.y = (state.glyph === 'buildings' ? h + 3 : dims.size + 5);
  sprite.visible = state.labels === 'all' || n.type !== 'listed';
  group.add(sprite);
  group.userData.labelSprite = sprite;
  group.userData.nodeType = n.type;
  return group;
}

function linkColor(l) {
  const p = pal();
  return { lists: p.linkLists, built: p.linkBuilt, operates: p.linkOperates, sister: p.linkSister }[l.kind] || p.linkLists;
}

const MAIN_ROADS = new Set(['motorway', 'trunk', 'primary', 'secondary', 'tertiary',
  'primary_link', 'secondary_link', 'tertiary_link']);
const ROAD_WIDTH = { motorway: 1.2, trunk: 1.1, primary: 1.0, secondary: 0.8, tertiary: 0.65 };

// Flat ribbon mesh along a ground polyline (for main roads; lesser streets
// stay 1px lines). Naive per-point perpendicular is fine at this scale.
function ribbonGeometry(pts, width) {
  const half = width / 2;
  const verts = [], idx = [];
  const dir = [];
  for (let i = 0; i < pts.length; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
    const dx = b[0] - a[0], dz = b[1] - a[1];
    const len = Math.hypot(dx, dz) || 1;
    dir.push([-dz / len, dx / len]);
  }
  pts.forEach((pt, i) => {
    verts.push(pt[0] + dir[i][0] * half, 0, pt[1] + dir[i][1] * half);
    verts.push(pt[0] - dir[i][0] * half, 0, pt[1] - dir[i][1] * half);
    if (i > 0) {
      const k = i * 2;
      idx.push(k - 2, k - 1, k, k - 1, k + 1, k);
    }
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

function buildDecor() {
  if (decor) {
    // Dispose GPU buffers before dropping the group — buildDecor re-runs on
    // every axis change and orphaned geometries leak WebGL memory.
    decor.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        if (o.material.map) o.material.map.dispose();
        o.material.dispose();
      }
    });
    graph.scene().remove(decor);
    decor = null;
  }
  if (state.mode !== 'city' || !sat || !satTexture) return;
  const p = pal();
  decor = new THREE.Group();

  // The table everything lies on, out past the far band.
  // Layer heights are spread several units apart: at region scale the depth
  // buffer z-fights on sub-unit gaps (striping), and a few units of height
  // are invisible from any viewing angle.
  const table = new THREE.Mesh(
    new THREE.CircleGeometry(FAR_R + 450, 96),
    new THREE.MeshLambertMaterial({ color: p.table, side: THREE.DoubleSide })
  );
  table.rotation.x = -Math.PI / 2;
  table.position.y = -8;
  decor.add(table);

  // 30-mile regional base map (z13), framed like a paper map on the table.
  if (region && regionTexture) {
    const [rxw, rzn] = toLocal(region.north, region.west);
    const [rxe, rzs] = toLocal(region.south, region.east);
    const rframe = new THREE.Mesh(
      new THREE.PlaneGeometry(rxe - rxw + 60, rzs - rzn + 60),
      new THREE.MeshLambertMaterial({ color: p.frame })
    );
    rframe.rotation.x = -Math.PI / 2;
    rframe.position.set((rxw + rxe) / 2, -5, (rzn + rzs) / 2);
    decor.add(rframe);
    const rmap = new THREE.Mesh(
      new THREE.PlaneGeometry(rxe - rxw, rzs - rzn),
      new THREE.MeshBasicMaterial({ map: regionTexture })
    );
    rmap.rotation.x = -Math.PI / 2;
    rmap.position.set((rxw + rxe) / 2, -3, (rzn + rzs) / 2);
    decor.add(rmap);
  }

  // Crisp downtown inset (z17) layered just above the regional imagery.
  const [xw, zn] = toLocal(sat.north, sat.west);
  const [xe, zs] = toLocal(sat.south, sat.east);
  const w = xe - xw, hgt = zs - zn;
  const cx = (xw + xe) / 2, cz = (zn + zs) / 2;
  if (!region || !regionTexture) {
    const frame = new THREE.Mesh(
      new THREE.PlaneGeometry(w + 8, hgt + 8),
      new THREE.MeshLambertMaterial({ color: p.frame })
    );
    frame.rotation.x = -Math.PI / 2;
    frame.position.set(cx, -0.35, cz);
    decor.add(frame);
  }
  const map = new THREE.Mesh(
    new THREE.PlaneGeometry(w, hgt),
    new THREE.MeshBasicMaterial({ map: satTexture })
  );
  map.rotation.x = -Math.PI / 2;
  map.position.set(cx, -0.1, cz);
  decor.add(map);

  // The campus plot: a paper card under the online-layer buildings.
  const plotW = Math.max((5 - 1) * CAMPUS.builtGap, (4 - 1) * CAMPUS.dirGap) + 34;
  const plotH = CAMPUS.builtZ - CAMPUS.hubZ + 40;
  const plot = new THREE.Mesh(
    new THREE.PlaneGeometry(plotW, plotH),
    new THREE.MeshLambertMaterial({ color: p.frame })
  );
  plot.rotation.x = -Math.PI / 2;
  plot.position.set(CAMPUS.cx, -1.2, (CAMPUS.hubZ + CAMPUS.builtZ) / 2);
  decor.add(plot);
  const plotLbl = makeLabelSprite('The online layer — our sites', p.ringText, 0.75);
  plotLbl.position.set(CAMPUS.cx, 2.5, CAMPUS.builtZ + 26);
  decor.add(plotLbl);

  // Single band past the map edge for places beyond the 30-mile region.
  const pts = [];
  for (let i = 0; i <= 160; i++) {
    const t = (i / 160) * Math.PI * 2;
    pts.push(new THREE.Vector3(FAR_R * Math.sin(t), 0.2, -FAR_R * Math.cos(t)));
  }
  decor.add(new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color: new THREE.Color(p.ringText), transparent: true, opacity: 0.35 })
  ));
  const lbl = makeLabelSprite('beyond 30 miles', p.ringText, 8);
  lbl.position.set(0, 30, -FAR_R - 120);
  decor.add(lbl);

  graph.scene().add(decor);
}

// Focus-density labels: reveal listed-node names as the camera gets close.
const LABEL_REVEAL_DIST = 450;
let labelTimer = null;

// Keep glyphs a usable on-screen size across the huge zoom range: scale each
// node group with its distance from the camera, like map pins that never
// shrink into invisibility. Buildings cap lower so towers stay plausible.
const SCALE_REF = 300;
function updateNodeScales() {
  if (!net) return;
  const cam = graph.camera();
  net.nodes.forEach(n => {
    const o = n.__threeObj;
    if (!o) return;
    const d = Math.hypot(cam.position.x - (n.x || 0), cam.position.y - (n.y || 0), cam.position.z - (n.z || 0));
    const cap = n.type === 'listed' ? 12 : 5;
    o.scale.setScalar(Math.min(cap, Math.max(1, d / SCALE_REF)));
  });
}
function updateLabelVisibility() {
  if (!net) return;
  const cam = graph.camera();
  net.nodes.forEach(n => {
    const obj = n.__threeObj;
    if (!obj || !obj.userData.labelSprite) return;
    if (obj.userData.nodeType !== 'listed') { obj.userData.labelSprite.visible = true; return; }
    if (state.labels === 'all') { obj.userData.labelSprite.visible = true; return; }
    const d = Math.hypot(cam.position.x - (n.x || 0), cam.position.y - (n.y || 0), cam.position.z - (n.z || 0));
    obj.userData.labelSprite.visible = d < LABEL_REVEAL_DIST;
  });
}
function scheduleLabelUpdate() {
  if (labelTimer) return;
  labelTimer = setTimeout(() => { labelTimer = null; updateLabelVisibility(); }, 250);
}

function applyMotion() {
  const controls = graph.controls();
  // Table mode never orbits on its own — you lean over a map, it doesn't spin.
  controls.autoRotate = state.motion === 'full' && state.mode !== 'city';
  controls.autoRotateSpeed = 0.35;
  graph.linkDirectionalParticles(l => (state.motion === 'full' && l.kind === 'lists' && linkShown(l)) ? 2 : 0)
    .linkDirectionalParticleSpeed(0.004)
    .linkDirectionalParticleWidth(1.2);
}

function applyControls() {
  const c = graph.controls();
  if (state.mode === 'city') {
    // Fixed-angle map: pan and zoom only. The view never tilts or spins —
    // any drag slides the map, the wheel zooms at the cursor.
    c.enableRotate = false;
    c.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
    c.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_PAN };
    c.screenSpacePanning = false;   // panning stays in the table plane
    c.zoomToCursor = true;
    c.minDistance = 25;
    c.maxDistance = 9000; // far enough to frame the whole 30-mile region
  } else {
    c.enableRotate = true;
    c.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
    c.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
    c.screenSpacePanning = true;
    c.zoomToCursor = false;
    c.minPolarAngle = 0;
    c.maxPolarAngle = Math.PI;
    c.minDistance = 0;
    c.maxDistance = Infinity;
  }
  c.update();
}

function applyAll() {
  const p = pal();
  document.documentElement.style.setProperty('--bg', p.bg);
  document.documentElement.style.setProperty('--label', p.label);
  positionNodes();
  graph.backgroundColor(p.bg)
    .nodeThreeObject(nodeObject)
    .linkColor(linkColor)
    .linkWidth(l => l.kind === 'lists' ? 0.6 : 1.4)
    .linkCurvature(l => state.mode === 'city' ? (l.kind === 'lists' ? 0.18 : 0.28) : 0)
    .linkOpacity(0.9);
  graph.controls().addEventListener('change', scheduleLabelUpdate);
  graph.controls().addEventListener('change', updateNodeScales);
  setTimeout(updateLabelVisibility, 300);
  setTimeout(updateNodeScales, 300);
  const cam = graph.camera();
  cam.far = 40000; // region map + table extend past the default far plane
  cam.near = 5;    // default 0.1 wrecks depth precision at region distances
  cam.updateProjectionMatrix();
  buildDecor();
  applyMotion();
  applyControls();
  if (state.mode === 'city') {
    graph.cooldownTicks(0);
  } else {
    graph.cooldownTicks(Infinity);
    graph.d3ReheatSimulation();
  }
}

function defaultCamera(ms) {
  if (state.mode === 'city') {
    // Over the town with the surrounding region in view.
    graph.cameraPosition({ x: 0, y: 520, z: 380 }, { x: 0, y: 0, z: 0 }, ms || 0);
  } else {
    graph.cameraPosition({ x: 0, y: 150, z: 290 }, { x: 0, y: 10, z: 0 }, ms || 0);
  }
}

// ---- Filters, search, info panel ----
const filters = { types: new Set(['hub', 'directory', 'built', 'listed']), band: 'all' };
let selected = null; // clicked node whose 'lists' connections are shown
let hovered = null;  // node under the cursor — its connections light up too

function endNode(l, side) {
  const v = l[side];
  return typeof v === 'object' ? v : net.nodes.find(n => n.id === v);
}

// The 80 directory→listing links are spaghetti when drawn all at once; the
// dozen ownership links carry the structure. Listing links appear only for
// the node you click.
function linkShown(l) {
  const s = endNode(l, 'source'), t = endNode(l, 'target');
  if (!nodeVisible(s) || !nodeVisible(t)) return false;
  if (l.kind !== 'lists') return true;
  return [selected, hovered].some(f => f && (s.id === f.id || t.id === f.id));
}

function nodeVisible(n) {
  if (!filters.types.has(n.type)) return false;
  // Unknown distance means "always show" — hiding it would read as a data gap.
  if (filters.band !== 'all' && n.type === 'listed' &&
      n.drive_min != null && n.drive_min > Number(filters.band)) return false;
  return true;
}

function applyFilters() {
  graph.nodeVisibility(nodeVisible).linkVisibility(linkShown);
  updateStats();
}

function updateStats() {
  const vis = net.nodes.filter(nodeVisible);
  const c = t => vis.filter(n => n.type === t).length;
  document.getElementById('stats').textContent =
    `${c('directory')} directories · ${c('built')} sites built · ${c('listed')} businesses & places connected — hover or click anything to light up its connections`;
}

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

const TYPE_LABEL = { hub: 'The studio', directory: 'Our directory', built: 'Built by Barnraised', listed: 'Listed business / place' };
const DIR_NAMES = { 'livingston-outdoors': 'Livingston Outdoors', 'visit-livingston-tn': 'Visit Livingston TN', 'middle-tn-printers': 'Middle TN Printers', 'best-mom-cars': 'Best Mom Cars' };

function openPanel(n) {
  const p = document.getElementById('panel');
  document.getElementById('panel-kicker').textContent = TYPE_LABEL[n.type] || n.type;
  document.getElementById('panel-name').textContent = n.name;
  document.getElementById('panel-meta').textContent = [
    n.city, n.county && n.county + ' County',
    n.drive_min != null ? n.drive_min + ' min from the square' : null
  ].filter(Boolean).join(' · ');
  document.getElementById('panel-blurb').textContent = n.blurb || '';
  const vEl = document.getElementById('panel-visitors');
  if (n.type === 'listed') {
    vEl.textContent = '';
  } else {
    const v = visitorsFor(n);
    vEl.textContent = (v && v.uniques != null)
      ? `Weekly visitors: ${v.uniques.toLocaleString()} (${v.source})`
      : 'Weekly visitors: no data yet';
  }
  const listedIn = (n.listed_in || []).map(id => DIR_NAMES[id] || id);
  document.getElementById('panel-listed').textContent =
    listedIn.length ? 'On our directories: ' + listedIn.join(' · ') : '';
  const visit = document.getElementById('panel-visit');
  visit.href = n.url || '#';
  visit.style.display = n.url ? '' : 'none';
  p.hidden = false;
  p.dataset.type = n.type;
  document.getElementById('panel-close').focus({ preventScroll: true });
}

function focusNode(n) {
  // Slide toward the node keeping the current bearing and tilt — the camera
  // never swings onto a new axis just because a node was clicked.
  const cam = graph.camera(), tgt = graph.controls().target;
  const off = { x: cam.position.x - tgt.x, y: cam.position.y - tgt.y, z: cam.position.z - tgt.z };
  const len = Math.hypot(off.x, off.y, off.z) || 1;
  const dist = 110;
  const pos = {
    x: (n.x || 0) + off.x / len * dist,
    y: (n.y || 0) + off.y / len * dist,
    z: (n.z || 0) + off.z / len * dist
  };
  // Stay comfortably above the table even if the view was near-flat.
  pos.y = Math.max(pos.y, (n.y || 0) + dist * 0.4);
  graph.cameraPosition(pos, { x: n.x || 0, y: n.y || 0, z: n.z || 0 }, 900);
  openPanel(n);
}

function wireHud() {
  document.querySelectorAll('#legend .chip[data-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      const t = btn.dataset.filter;
      if (filters.types.has(t)) { filters.types.delete(t); btn.classList.remove('is-on'); }
      else { filters.types.add(t); btn.classList.add('is-on'); }
      applyFilters();
    });
  });
  document.querySelectorAll('#legend .chip.band').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#legend .chip.band').forEach(b => b.classList.remove('is-on'));
      btn.classList.add('is-on');
      filters.band = btn.dataset.band;
      applyFilters();
    });
  });
  document.getElementById('panel-close').addEventListener('click', clearSelection);

  const input = document.getElementById('search');
  const results = document.getElementById('search-results');
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    results.innerHTML = '';
    if (q.length < 2) { results.hidden = true; return; }
    const hits = net.nodes.filter(n => nodeVisible(n) && n.name.toLowerCase().includes(q)).slice(0, 8);
    hits.forEach(n => {
      const li = document.createElement('li');
      li.textContent = n.name;
      li.tabIndex = -1;
      li.setAttribute('role', 'option');
      li.addEventListener('click', () => {
        results.hidden = true; input.value = n.name;
        selectNode(n);
      });
      li.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); li.click(); }
        else if (e.key === 'ArrowDown' && li.nextSibling) { e.preventDefault(); li.nextSibling.focus(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); (li.previousSibling || input).focus(); }
        else if (e.key === 'Escape') { results.hidden = true; input.focus(); }
      });
      results.appendChild(li);
    });
    results.hidden = hits.length === 0;
  });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && results.firstChild) results.firstChild.click();
    else if (e.key === 'ArrowDown' && !results.hidden && results.firstChild) { e.preventDefault(); results.firstChild.focus(); }
    else if (e.key === 'Escape') { results.hidden = true; }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !document.getElementById('panel').hidden) {
      clearSelection();
      input.focus();
    }
  });
}

function selectNode(n) {
  selected = n;
  applyFilters();
  applyMotion();
  focusNode(n);
}

function clearSelection() {
  selected = null;
  document.getElementById('panel').hidden = true;
  applyFilters();
  applyMotion();
}

Promise.all([
  fetch('./data/network.json').then(r => r.json()),
  fetch('./data/satellite.json').then(r => r.json()),
  new THREE.TextureLoader().loadAsync('./data/satellite.jpg'),
  fetch('./data/visitors.json').then(r => r.json()).catch(() => null),
  fetch('./data/region.json').then(r => r.json()).catch(() => null),
  new THREE.TextureLoader().loadAsync('./data/region.jpg').catch(() => null)
])
  .then(([data, satMeta, tex, vis, regionMeta, regionTex]) => {
    sat = satMeta;
    tex.colorSpace = THREE.SRGBColorSpace;
    satTexture = tex;
    if (regionMeta && regionTex) {
      region = regionMeta;
      regionTex.colorSpace = THREE.SRGBColorSpace;
      regionTexture = regionTex;
      const [rxw, rzn] = toLocal(region.north, region.west);
      const [rxe, rzs] = toLocal(region.south, region.east);
      FAR_R = Math.max(Math.abs(rxw), Math.abs(rxe), Math.abs(rzn), Math.abs(rzs)) + 260;
    }
    document.querySelector('.hud-credit').textContent = sat.credit || '';
    visitors = vis;
    computeMaxUniques();
    net = { nodes: data.nodes, links: data.edges.map(e => ({ ...e })) };
    graph.graphData(net)
      .nodeLabel(n => `<div class="tip"><strong>${esc(n.name)}</strong><br>${esc(n.type === 'listed' ? (n.category || '') : n.type)}${n.city ? ' · ' + esc(n.city) : ''}${n.drive_min != null ? ' · ' + esc(n.drive_min) + ' min out' : ''}</div>`)
      .onNodeClick(selectNode)
      .onNodeHover(n => {
        const h = n || null;
        if (h === hovered) return;
        hovered = h;
        document.body.style.cursor = h ? 'pointer' : '';
        applyFilters();
        applyMotion();
      })
      .onBackgroundClick(() => { clearSelection(); })
      .showNavInfo(false);
    applyAll();
    wireHud();
    applyFilters();
    defaultCamera(0);
    window.__mapReady = true;
  })
  .catch(err => {
    document.getElementById('graph').innerHTML = '<p class="load-error">Could not load map data — run scripts/build_network.py and scripts/fetch_satellite.py first. (' + err.message + ')</p>';
  });

// The preset switcher writes data-* attributes on <html>; watch and re-apply.
new MutationObserver(muts => {
  let dirty = false;
  muts.forEach(m => {
    const key = m.attributeName.replace(/^data-/, '');
    const val = document.documentElement.getAttribute(m.attributeName);
    if (key in state && val && state[key] !== val) { state[key] = val; dirty = true; }
  });
  if (dirty && net) applyAll();
}).observe(document.documentElement, { attributes: true, attributeFilter: ['data-mode', 'data-palette', 'data-glyph', 'data-labels', 'data-motion'] });

// Adopt the combo baked onto <html> (or applied by a switcher before this
// module ran). A reduced-motion preference beats the baked motion axis.
['mode', 'palette', 'glyph', 'labels', 'motion'].forEach(key => {
  if (key === 'motion' && window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  let val = document.documentElement.getAttribute('data-' + key);
  if (val === 'rings') val = 'city'; // legacy name for the map view
  if (val && val !== state[key]) state[key] = val;
});

window.addEventListener('resize', () => graph.width(window.innerWidth).height(window.innerHeight));
