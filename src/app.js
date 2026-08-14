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

// Gold marks "needs a website": beacon pins for swept-up businesses, base
// rings on already-listed places whose web presence is weak.
const PROSPECT_GOLD = '#eab308';
const PROSPECT_REASONS = {
  'no-website': 'no website at all',
  'facebook-only': 'Facebook page only',
  'rented-subdomain': 'rented site-builder page',
  'aggregator-listing': "only on other people's sites",
  'dead-site': 'has a domain but effectively no visitors'
};

// Call-status CRM, persisted locally in this browser. {nodeId: {status, sample}}
const CRM_KEY = 'lnm-status-v1';
const STATUSES = ['none', 'called', 'meeting', 'sample', 'won', 'dead'];
const STATUS_LABEL = { none: 'to call', called: 'called', meeting: 'meeting',
  sample: 'sample built', won: 'won', dead: 'dead' };
let crm = {};
try { crm = JSON.parse(localStorage.getItem(CRM_KEY) || '{}'); } catch { crm = {}; }
function crmFor(id) { return crm[id] || { status: 'none' }; }
function setCrm(id, patch) {
  crm[id] = { ...crmFor(id), ...patch };
  try { localStorage.setItem(CRM_KEY, JSON.stringify(crm)); } catch { /* private mode */ }
}

// One color per directory/top-list, used by every linkviz variant: badge
// chips on pins, halo rings, ribbon links, the disc under each directory
// glyph, and the dots in the info panel.
const DIR_COLORS = {
  'livingston-outdoors': '#0f766e',
  'visit-livingston-tn': '#d97706',
  'middle-tn-printers': '#1d4ed8',
  'best-mom-cars': '#db2777'
};

// Radius (scene units) of the regional map edge; recomputed from region.json
// at load. Places beyond the region sit on a single band just past the edge.
let FAR_R = 4300;

const state = {
  mode: 'city', palette: 'dawn', glyph: 'buildings',
  labels: 'focus', motion: 'full',
  linkviz: document.documentElement.getAttribute('data-linkviz') || 'badges'
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
let traffic = null; // parsed data/traffic.json {node_id: {reviews, rating, crux}}
let prospects = null; // parsed data/prospects.json {flagged: {id: {...}}, new: [...]}
let prevTraffic = null; // previous monthly snapshot {node_id: {reviews, crux}} for trend arrows
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

// Small emoji glyph riding the pin head so categories read at a glance.
const GROUP_EMOJI = { eats: '🍽️', town: '🏛️', water: '🌊', land: '🌲' };
const PROSPECT_EMOJI = [
  [/restaurant|bakery|coffee/, '🍽️'], [/hair|barber/, '💈'],
  [/auto|tire|towing/, '🔧'], [/gift|boutique|hardware|florist/, '🛍️'],
  [/dentist|chiropractor|pharmac/, '🩺'], [/veterinar|pet/, '🐾'],
  [/gym/, '🏋️'], [/daycare/, '🧸'], [/plumb|electric|hvac|roof|landscap|lawn/, '🛠️'],
  [/real estate|insurance/, '🏠']
];
const iconCache = {};
function catEmoji(n) {
  if (n.type === 'listed') return GROUP_EMOJI[CAT_GROUP[n.category]] || null;
  const cat = (n.category || '').toLowerCase();
  const hit = PROSPECT_EMOJI.find(([re]) => re.test(cat));
  return hit ? hit[1] : '⭐';
}
function addCatIcon(group, n, y) {
  const em = catEmoji(n);
  if (!em) return;
  if (!iconCache[em]) {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const ctx = c.getContext('2d');
    ctx.font = '48px "Segoe UI Emoji", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(em, 32, 36);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    iconCache[em] = tex;
  }
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: iconCache[em], depthWrite: false, transparent: true }));
  sprite.scale.set(3.4, 3.4, 1);
  sprite.position.y = y;
  sprite.position.z = 0.1;
  group.add(sprite);
}

// Gentle pulse on gold beacons — skipped for reduced-motion/calm, paused
// when the tab is hidden, and absent on won/dead pins (no pulseHead set).
(function pulseLoop() {
  requestAnimationFrame(pulseLoop);
  if (!net || state.motion === 'calm' || document.hidden) return;
  const s = 1 + 0.1 * Math.sin(performance.now() / 320);
  net.nodes.forEach(nn => {
    const h = nn.__threeObj && nn.__threeObj.userData.pulseHead;
    if (h) h.scale.setScalar(s);
  });
})();

function nodeObject(n) {
  const p = pal();
  const dims = NODE_DIMS[n.type] || NODE_DIMS.listed;
  const color = p[n.type] || p.listed;
  const h = heightFor(n);
  const group = new THREE.Group();
  if (n.type === 'prospect') {
    // Gold beacon pin: a business worth pitching a Barnraised build. CRM
    // status changes the read: won pins turn built-blue, dead pins grey out.
    const st = crmFor(n.id).status;
    const headColor = st === 'won' ? p.built : (st === 'dead' ? '#8a8578' : PROSPECT_GOLD);
    const peg = new THREE.Mesh(
      new THREE.CylinderGeometry(0.5, 0.95, 7, 10),
      new THREE.MeshLambertMaterial({ color: p.frame })
    );
    peg.position.y = 3.5;
    group.add(peg);
    const pr = n.prospect || {};
    const headR = pr.reviews
      ? 2.2 + 1.5 * Math.min(1, Math.log10(pr.reviews + 1) / 3.3)
      : 2.6;
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(headR, 16, 12),
      new THREE.MeshLambertMaterial({ color: headColor,
        emissive: st === 'won' || st === 'dead' ? '#000000' : '#6b4e00' })
    );
    head.position.y = 8;
    group.add(head);
    if (st !== 'won' && st !== 'dead') {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(3.4, 4.4, 28),
        new THREE.MeshBasicMaterial({ color: PROSPECT_GOLD, side: THREE.DoubleSide,
          transparent: true, opacity: 0.9, depthWrite: false })
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.3;
      group.add(ring);
      group.userData.pulseHead = head;
    }
    addCatIcon(group, n, 8);
    const sprite = makeLabelSprite(n.name, p.label, 0.8);
    sprite.position.y = 14.5;
    sprite.visible = state.labels === 'all';
    group.add(sprite);
    group.userData.labelSprite = sprite;
    group.userData.labelBase = sprite.scale.clone();
    group.userData.nodeType = n.type;
    return group;
  }
  if (n.type === 'listed') {
    // Map-pin: cream peg with a category-colored head — reads as "a place on
    // the map", distinct from our blue/teal buildings. Head size tracks the
    // business's Google review count (log scale, 2.2–3.7).
    const headColor = CAT_COLORS[CAT_GROUP[n.category]] || p.listed;
    const peg = new THREE.Mesh(
      new THREE.CylinderGeometry(0.5, 0.95, 7, 10),
      new THREE.MeshLambertMaterial({ color: p.frame })
    );
    peg.position.y = 3.5;
    group.add(peg);
    const tr = (traffic || {})[n.id];
    const headR = tr && tr.reviews
      ? 2.2 + 1.5 * Math.min(1, Math.log10(tr.reviews + 1) / 3.3)
      : 2.6;
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(headR, 16, 12),
      new THREE.MeshLambertMaterial({ color: headColor })
    );
    head.position.y = 8;
    group.add(head);
    // Weak web presence: gold base ring, same read as the prospect beacons.
    // A won engagement drops the ring; dead drops it too (stop signaling).
    if (n.prospect && !['won', 'dead'].includes(crmFor(n.id).status)) {
      const gold = new THREE.Mesh(
        new THREE.RingGeometry(4.6, 5.4, 28),
        new THREE.MeshBasicMaterial({ color: PROSPECT_GOLD, side: THREE.DoubleSide,
          transparent: true, opacity: 0.9, depthWrite: false })
      );
      gold.rotation.x = -Math.PI / 2;
      gold.position.y = 0.3;
      group.add(gold);
      group.userData.pulseHead = gold;
    }
    addCatIcon(group, n, 8);
    // Directory-membership viz, variant-dependent (data-linkviz).
    const dirs = n.listed_in || [];
    if (state.linkviz === 'badges') {
      // Small color chips stacked beside the peg, one per directory.
      dirs.forEach((d, i) => {
        const chip = new THREE.Sprite(new THREE.SpriteMaterial({
          color: DIR_COLORS[d] || '#888888', depthWrite: false }));
        chip.scale.set(1.7, 1.7, 1);
        chip.position.set(2.6, 3.0 + i * 2.2, 0);
        group.add(chip);
      });
    } else if (state.linkviz === 'halos') {
      // Concentric ground rings under the pin, one per directory.
      dirs.forEach((d, i) => {
        const ring = new THREE.Mesh(
          new THREE.RingGeometry(3.2 + i * 1.6, 4.0 + i * 1.6, 28),
          new THREE.MeshBasicMaterial({ color: DIR_COLORS[d] || '#888888',
            side: THREE.DoubleSide, transparent: true, opacity: 0.85, depthWrite: false })
        );
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.35 + i * 0.05;
        group.add(ring);
      });
    }
    const sprite = makeLabelSprite(n.name, p.label, 0.8);
    sprite.position.y = 14.5;
    sprite.visible = state.labels === 'all';
    group.add(sprite);
    group.userData.labelSprite = sprite;
    group.userData.labelBase = sprite.scale.clone();
    group.userData.nodeType = n.type;
    return group;
  }
  if (state.glyph === 'buildings') {
    const geo = new THREE.BoxGeometry(dims.w, h, dims.w);
    const mat = new THREE.MeshLambertMaterial({ color });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.y = h / 2 - 2;
    group.add(mesh);
    // Each directory building stands on a disc of its color, anchoring the
    // color key the linkviz variants use on the listed pins.
    if (n.type === 'directory' && DIR_COLORS[n.id]) {
      const disc = new THREE.Mesh(
        new THREE.CircleGeometry(dims.w + 2.5, 24),
        new THREE.MeshBasicMaterial({ color: DIR_COLORS[n.id],
          transparent: true, opacity: 0.9, depthWrite: false })
      );
      disc.rotation.x = -Math.PI / 2;
      disc.position.y = 0.3;
      group.add(disc);
    }
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
  group.userData.labelBase = sprite.scale.clone();
  group.userData.nodeType = n.type;
  return group;
}

function linkColor(l) {
  const p = pal();
  if (l.kind === 'lists' && state.linkviz === 'ribbons') {
    // Always-on ribbons tinted by which directory the link comes from;
    // hovering/selecting either end saturates it.
    const s = endNode(l, 'source'), t = endNode(l, 'target');
    const dirId = s.type === 'directory' ? s.id : t.id;
    const c = new THREE.Color(DIR_COLORS[dirId] || p.linkLists);
    const a = listTouched(l) ? 0.9 : 0.22;
    return `rgba(${Math.round(c.r * 255)},${Math.round(c.g * 255)},${Math.round(c.b * 255)},${a})`;
  }
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
const LABEL_REVEAL_DIST = 1600;
let labelTimer = null;

// Keep glyphs a usable on-screen size across the huge zoom range: scale each
// node group with its distance from the camera, like map pins that never
// shrink into invisibility. Buildings cap lower so towers stay plausible.
const SCALE_REF = 300;
// Labels grow far slower than the glyphs they ride on, so pulling back shrinks
// their on-screen size instead of holding it constant (the old label soup).
const LABEL_EXP = 0.7;
function updateNodeScales() {
  if (!net) return;
  const cam = graph.camera();
  net.nodes.forEach(n => {
    const o = n.__threeObj;
    if (!o) return;
    const d = Math.hypot(cam.position.x - (n.x || 0), cam.position.y - (n.y || 0), cam.position.z - (n.z || 0));
    const cap = (n.type === 'listed' || n.type === 'prospect') ? 12 : 5;
    const g = Math.min(cap, Math.max(1, d / SCALE_REF));
    o.scale.setScalar(g);
    const s = o.userData.labelSprite, base = o.userData.labelBase;
    if (s && base) {
      const f = Math.min(cap, Math.pow(Math.max(1, d / SCALE_REF), LABEL_EXP));
      s.scale.set(base.x * f / g, base.y * f / g, 1);
    }
  });
}
// Screen-space declutter: project every candidate label, keep them in priority
// order (selected/hovered, then our sites, then review count), hide any label
// whose rect would overlap one already kept or that would render unreadably
// small. Priority beats proximity, so zooming out keeps the names that matter.
const MIN_LABEL_PX = 8;
function updateLabelVisibility() {
  if (!net) return;
  const cam = graph.camera();
  const W = window.innerWidth, H = window.innerHeight;
  const fovScale = H / (2 * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2));
  const v = new THREE.Vector3();
  const cands = [];
  net.nodes.forEach(n => {
    const obj = n.__threeObj;
    if (!obj || !obj.userData.labelSprite) return;
    const s = obj.userData.labelSprite;
    const d = Math.hypot(cam.position.x - (n.x || 0), cam.position.y - (n.y || 0), cam.position.z - (n.z || 0));
    const listed = obj.userData.nodeType === 'listed' || obj.userData.nodeType === 'prospect';
    if (listed && state.labels !== 'all' && d >= LABEL_REVEAL_DIST) { s.visible = false; return; }
    const tr = (traffic || {})[n.id] || n.prospect;
    let pr = listed ? (tr && tr.reviews ? Math.min(tr.reviews, 5000) : 0)
      : 1e6 + (obj.userData.nodeType === 'hub' ? 2 : 1);
    if ([selected, hovered].some(f => f && f.id === n.id)) pr = 1e9;
    cands.push({ n, obj, s, d, pr });
  });
  cands.sort((a, b) => b.pr - a.pr);
  const kept = [];
  const PAD = 4;
  cands.forEach(c => {
    const g = c.obj.scale.x;
    v.set((c.n.x || 0) + c.s.position.x * g,
          (c.n.y || 0) + c.s.position.y * g,
          (c.n.z || 0) + c.s.position.z * g);
    const dLbl = v.distanceTo(cam.position);
    v.project(cam);
    if (v.z > 1 || v.z < -1) { c.s.visible = false; return; }
    const hPx = c.s.scale.y * g * fovScale / Math.max(1, dLbl);
    if (hPx < MIN_LABEL_PX) { c.s.visible = false; return; }
    const wPx = hPx * (c.s.scale.x / c.s.scale.y);
    const x = (v.x + 1) / 2 * W, y = (1 - v.y) / 2 * H;
    const r = { x0: x - wPx / 2 - PAD, x1: x + wPx / 2 + PAD, y0: y - hPx / 2 - PAD, y1: y + hPx / 2 + PAD };
    const hit = kept.some(k => r.x0 < k.x1 && r.x1 > k.x0 && r.y0 < k.y1 && r.y1 > k.y0);
    if (hit) { c.s.visible = false; return; }
    kept.push(r);
    c.s.visible = true;
  });
}
function scheduleLabelUpdate() {
  if (labelTimer) return;
  labelTimer = setTimeout(() => { labelTimer = null; updateLabelVisibility(); }, 120);
}

function applyMotion() {
  const controls = graph.controls();
  // Table mode never orbits on its own — you lean over a map, it doesn't spin.
  controls.autoRotate = state.motion === 'full' && state.mode !== 'city';
  controls.autoRotateSpeed = 0.35;
  // Particles only on the hovered/selected node's listing links — in ribbons
  // mode every lists link is shown, and particles on all of them is noise.
  graph.linkDirectionalParticles(l => (state.motion === 'full' && l.kind === 'lists' && linkShown(l) && listTouched(l)) ? 2 : 0)
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
  graph.controls().addEventListener('change', scheduleClusterUpdate);
  setTimeout(updateLabelVisibility, 300);
  setTimeout(updateNodeScales, 300);
  setTimeout(updateClusters, 350);
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
const filters = { types: new Set(['hub', 'directory', 'built', 'listed', 'prospect']), band: 'all' };
let selected = null; // clicked node whose 'lists' connections are shown
let hovered = null;  // node under the cursor — its connections light up too

function endNode(l, side) {
  const v = l[side];
  return typeof v === 'object' ? v : net.nodes.find(n => n.id === v);
}

// The 80 directory→listing links are spaghetti when drawn all at once; the
// dozen ownership links carry the structure. Listing links appear only for
// the node you click.
function listTouched(l) {
  const s = endNode(l, 'source'), t = endNode(l, 'target');
  return [selected, hovered].some(f => f && (s.id === f.id || t.id === f.id));
}

function linkShown(l) {
  const s = endNode(l, 'source'), t = endNode(l, 'target');
  if (!nodeVisible(s) || !nodeVisible(t)) return false;
  if (l.kind !== 'lists') return true;
  if (state.linkviz === 'ribbons') return true;
  return listTouched(l);
}

function nodeVisible(n) {
  if (!filters.types.has(n.type)) return false;
  if (clusteredIds.has(n.id)) return false;
  // Unknown distance means "always show" — hiding it would read as a data gap.
  if (filters.band !== 'all' && (n.type === 'listed' || n.type === 'prospect') &&
      n.drive_min != null && n.drive_min > Number(filters.band)) return false;
  return true;
}

// Far-zoom clustering: past CLUSTER_DIST, downtown pins collapse into count
// badges (gold-tinged when the bucket holds prospects); clicking one zooms in.
const CLUSTER_DIST = 2600, CLUSTER_CELL = 150, CLUSTER_MIN = 4;
let clusterLayer = null;
const clusteredIds = new Set();
function clusterBadge(count, hasGold) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d');
  ctx.beginPath();
  ctx.arc(64, 64, 56, 0, Math.PI * 2);
  ctx.fillStyle = hasGold ? '#b8860b' : '#4a5568';
  ctx.fill();
  ctx.lineWidth = 8;
  ctx.strokeStyle = '#ffffff';
  ctx.stroke();
  ctx.fillStyle = '#ffffff';
  ctx.font = '700 52px "Segoe UI", sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(String(count), 64, 66);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthWrite: false, transparent: true }));
}
function updateClusters() {
  if (!net) return;
  const cam = graph.camera();
  const d = cam.position.distanceTo(graph.controls().target);
  if (clusterLayer) {
    clusterLayer.traverse(o => {
      if (o.material) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); }
    });
    graph.scene().remove(clusterLayer);
    clusterLayer = null;
  }
  const had = clusteredIds.size > 0;
  clusteredIds.clear();
  if (d > CLUSTER_DIST) {
    const buckets = {};
    net.nodes.forEach(n => {
      if (n.type !== 'listed' && n.type !== 'prospect') return;
      if (!filters.types.has(n.type)) return;
      const x = n.fx || 0, z = n.fz || 0;
      if (Math.hypot(x, z) >= FAR_R - 10) return; // beyond-region band stays individual
      const key = Math.round(x / CLUSTER_CELL) + '|' + Math.round(z / CLUSTER_CELL);
      (buckets[key] = buckets[key] || []).push(n);
    });
    clusterLayer = new THREE.Group();
    Object.values(buckets).forEach(list => {
      if (list.length < CLUSTER_MIN) return;
      list.forEach(n => clusteredIds.add(n.id));
      const cx = list.reduce((a, n) => a + (n.fx || 0), 0) / list.length;
      const cz = list.reduce((a, n) => a + (n.fz || 0), 0) / list.length;
      const gold = list.some(n => n.type === 'prospect' || (n.prospect && !['won', 'dead'].includes(crmFor(n.id).status)));
      const s = clusterBadge(list.length, gold);
      const k = Math.max(30, d / 40);
      s.scale.set(k, k, 1);
      s.position.set(cx, 24, cz);
      s.userData.clusterAt = { x: cx, z: cz };
      clusterLayer.add(s);
    });
    graph.scene().add(clusterLayer);
  }
  if (clusteredIds.size || had) applyFilters();
}
let clusterTimer = null;
function scheduleClusterUpdate() {
  if (clusterTimer) return;
  clusterTimer = setTimeout(() => { clusterTimer = null; updateClusters(); }, 200);
}

function applyFilters() {
  // linkColor re-set with a fresh closure so hover saturation recomputes.
  graph.nodeVisibility(nodeVisible).linkVisibility(linkShown).linkColor(l => linkColor(l));
  updateStats();
}

function updateStats() {
  const vis = net.nodes.filter(nodeVisible);
  const c = t => vis.filter(n => n.type === t).length;
  const needSite = vis.filter(n => n.type === 'prospect' || n.prospect).length;
  const drawerOpen = !document.getElementById('drawer').hidden;
  document.getElementById('stats').innerHTML =
    `${c('directory')} directories · ${c('built')} sites built · ${c('listed')} businesses & places connected · ` +
    `<button class="stats-link" id="open-drawer" aria-expanded="${drawerOpen}">${needSite} need a website (gold) — open the call list</button>`;
}

function prospectInfo(n) {
  const pr = n.prospect || {};
  const tr = (traffic || {})[n.id] || {};
  return {
    reviews: pr.reviews || tr.reviews || 0,
    rating: pr.rating || tr.rating || null,
    reason: pr.reason,
    phone: pr.phone || null
  };
}

let drawerFilter = 'all';
function prospectRows() {
  return net.nodes.filter(n => n.type === 'prospect' || n.prospect)
    .map(n => ({ n, i: prospectInfo(n), c: crmFor(n.id) }))
    .sort((a, b) => (STATUSES.indexOf(a.c.status) - STATUSES.indexOf(b.c.status))
      || (b.i.reviews - a.i.reviews));
}
function buildDrawer() {
  const rows = prospectRows();
  const counts = {};
  rows.forEach(r => { counts[r.c.status] = (counts[r.c.status] || 0) + 1; });
  document.getElementById('drawer-filters').innerHTML =
    ['all', ...STATUSES].map(s => `<button class="chip drawer-filter ${drawerFilter === s ? 'is-on' : ''}"
      data-f="${s}" aria-pressed="${drawerFilter === s}">${s === 'all' ? `all (${rows.length})` : `${STATUS_LABEL[s]} (${counts[s] || 0})`}</button>`).join(' ');
  const shown = rows.filter(r => drawerFilter === 'all' || r.c.status === drawerFilter);
  document.getElementById('drawer-list').innerHTML = shown.map(({ n, i, c }) => `
    <li>
      <button class="drawer-row" data-id="${esc(n.id)}">
        <strong>${esc(n.name)}</strong>
        <span class="drawer-meta">${esc(n.city || '')}${i.reviews ? ` · ${i.reviews.toLocaleString()} reviews` : ''}${i.rating ? ` · ${i.rating}★` : ''}${c.status !== 'none' ? ` · <em class="st-${esc(c.status)}">${STATUS_LABEL[c.status]}</em>` : ''}</span>
        <span class="drawer-why">${esc(PROSPECT_REASONS[i.reason] || i.reason || '')}</span>
      </button>
      ${i.phone ? `<a class="drawer-call" href="tel:${esc(i.phone.replace(/[^+\d]/g, ''))}">${esc(i.phone)}</a>` : ''}
    </li>`).join('');
}
function exportCsv() {
  const q = v => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`;
  const lines = [['Business', 'Town', 'Category', 'Phone', 'Google reviews', 'Rating',
    'Why they need a site', 'Status', 'Sample URL'].join(',')];
  prospectRows().forEach(({ n, i, c }) => {
    lines.push([q(n.name), q(n.city), q(n.category), q(i.phone), i.reviews || '',
      i.rating || '', q(PROSPECT_REASONS[i.reason] || i.reason),
      q(STATUS_LABEL[c.status]), q(c.sample)].join(','));
  });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' }));
  a.download = 'livingston-call-list.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

const TYPE_LABEL = { hub: 'The studio', directory: 'Our directory', built: 'Built by Barnraised', listed: 'Listed business / place', prospect: 'Needs a website' };
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
  if (n.type === 'prospect') {
    const pr = n.prospect || {};
    const bits = [];
    if (pr.reviews) bits.push(`Google reviews: ${pr.reviews.toLocaleString()}${pr.rating ? ` · ${pr.rating}★` : ''}`);
    bits.push(`Why talk to them: ${PROSPECT_REASONS[pr.reason] || pr.reason}` +
      (pr.reviews ? ' — customers are looking, there is nowhere to send them' : ''));
    if (n.geo_method === 'town-approx') bits.push('(map spot approximate)');
    vEl.textContent = bits.join(' · ');
  } else if (n.type === 'listed') {
    const tr = (traffic || {})[n.id];
    const bits = [];
    if (tr && tr.reviews) bits.push(`Google reviews: ${tr.reviews.toLocaleString()} · ${tr.rating}★`);
    // CrUX inclusion needs ~1k+ monthly visits — the closest thing to a real
    // traffic number that exists publicly for sites this small.
    if (tr && tr.crux === true) bits.push('website: ~1,000+ visits/mo (est. from Chrome usage data)');
    else if (tr && tr.crux === false) bits.push('website: under ~1,000 visits/mo (est.)');
    const pv = prevTraffic && prevTraffic[n.id];
    if (tr && tr.reviews && pv && pv.reviews && pv.reviews !== tr.reviews) {
      const dlt = tr.reviews - pv.reviews;
      bits.push(`${dlt > 0 ? '▲' : '▼'} ${Math.abs(dlt)} reviews since last snapshot`);
    }
    if (n.prospect) bits.push(`Website prospect: ${PROSPECT_REASONS[n.prospect.reason] || n.prospect.reason}`);
    vEl.textContent = bits.length ? bits.join(' · ') : 'No public traffic data';
  } else {
    const v = visitorsFor(n);
    vEl.textContent = (v && v.uniques != null)
      ? `Weekly visitors: ${v.uniques.toLocaleString()} (${v.source})`
      : 'Weekly visitors: no data yet';
  }
  const phEl = document.getElementById('panel-phone');
  const phone = n.prospect && n.prospect.phone;
  phEl.innerHTML = phone
    ? `<a href="tel:${esc(phone.replace(/[^+\d]/g, ''))}">${esc(phone)}</a>`
    : '';
  const crmEl = document.getElementById('panel-crm');
  if (n.type === 'prospect' || n.prospect) {
    const st = crmFor(n.id);
    crmEl.innerHTML = `<label>Status: <select id="crm-status" aria-label="Call status">` +
      STATUSES.map(s => `<option value="${s}" ${s === st.status ? 'selected' : ''}>${STATUS_LABEL[s]}</option>`).join('') +
      `</select></label>` +
      (st.sample ? ` <a href="${esc(st.sample)}" target="_blank" rel="noopener">sample site ↗</a>` : '');
    crmEl.querySelector('#crm-status').addEventListener('change', e => {
      const v = e.target.value;
      const patch = { status: v };
      if ((v === 'sample' || v === 'won') && !crmFor(n.id).sample) {
        const u = window.prompt('Sample/live site URL (optional):') || '';
        if (/^https?:\/\//.test(u)) patch.sample = u;
      }
      setCrm(n.id, patch);
      graph.nodeThreeObject(x => nodeObject(x));
      setTimeout(() => { updateNodeScales(); updateLabelVisibility(); }, 100);
      openPanel(n);
      buildDrawer();
    });
  } else {
    crmEl.innerHTML = '';
  }
  const listedEl = document.getElementById('panel-listed');
  const dirIds = n.listed_in || [];
  if (dirIds.length) {
    listedEl.innerHTML = 'On our directories: ' + dirIds.map(id =>
      `<span class="dir-tag"><span class="dir-dot" style="background:${DIR_COLORS[id] || '#888'}"></span>${esc(DIR_NAMES[id] || id)}</span>`
    ).join(' · ');
  } else {
    listedEl.textContent = '';
  }
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

  // Call-list drawer: opened from the stats line (delegated — the stats line
  // is re-rendered on every filter change), rows fly to their node.
  const drawer = document.getElementById('drawer');
  document.getElementById('stats').addEventListener('click', e => {
    if (e.target.id === 'open-drawer') {
      buildDrawer();
      drawer.hidden = false;
      e.target.setAttribute('aria-expanded', 'true');
      drawer.focus({ preventScroll: true });
    }
  });
  document.getElementById('drawer-close').addEventListener('click', () => {
    drawer.hidden = true;
    const b = document.getElementById('open-drawer');
    if (b) b.setAttribute('aria-expanded', 'false');
  });
  document.getElementById('drawer-list').addEventListener('click', e => {
    const row = e.target.closest('.drawer-row');
    if (!row) return;
    const n = net.nodes.find(x => x.id === row.dataset.id);
    if (n) { selectNode(n); openPanel(n); }
  });
  document.getElementById('drawer-filters').addEventListener('click', e => {
    const b = e.target.closest('.drawer-filter');
    if (!b) return;
    drawerFilter = b.dataset.f;
    buildDrawer();
  });
  document.getElementById('drawer-csv').addEventListener('click', exportCsv);

  // Escape closes whatever is open, top-most first.
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    const panel = document.getElementById('panel');
    if (!panel.hidden) { clearSelection(); return; }
    if (!drawer.hidden) { document.getElementById('drawer-close').click(); }
  });

  // Cluster badges live outside the graph's node picking — raycast manually.
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  graph.renderer().domElement.addEventListener('click', e => {
    if (!clusterLayer || !clusterLayer.children.length) return;
    const r = graph.renderer().domElement.getBoundingClientRect();
    mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1;
    mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(mouse, graph.camera());
    const hit = ray.intersectObjects(clusterLayer.children)[0];
    if (hit) {
      const { x, z } = hit.object.userData.clusterAt;
      graph.cameraPosition({ x, y: 620, z: z + 450 }, { x, y: 0, z }, 800);
    }
  });

  // First-visit hint.
  const hint = document.getElementById('hint');
  if (!localStorage.getItem('lnm-hint')) hint.hidden = false;
  document.getElementById('hint-close').addEventListener('click', () => {
    hint.hidden = true;
    try { localStorage.setItem('lnm-hint', '1'); } catch { /* private mode */ }
  });

  const input = document.getElementById('search');
  const results = document.getElementById('search-results');
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    results.innerHTML = '';
    if (q.length < 2) { results.hidden = true; return; }
    const hits = net.nodes.filter(n => nodeVisible(n) && (
      n.name.toLowerCase().includes(q) ||
      (n.category || '').toLowerCase().includes(q) ||
      (n.city || '').toLowerCase().includes(q)
    )).slice(0, 8);
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
  history.replaceState(null, '', '#' + encodeURIComponent(n.id));
  applyFilters();
  applyMotion();
  updateLabelVisibility();
  focusNode(n);
}

function clearSelection() {
  selected = null;
  history.replaceState(null, '', location.pathname + location.search);
  document.getElementById('panel').hidden = true;
  applyFilters();
  applyMotion();
}

// Hover mini-card: name + the numbers that matter, following the cursor.
const tipEl = () => document.getElementById('tip');
function showTip(n) {
  const t = tipEl();
  if (!n) { t.hidden = true; return; }
  const i = prospectInfo(n);
  const bits = [];
  if (i.reviews) bits.push(`${i.reviews.toLocaleString()} reviews${i.rating ? ` · ${i.rating}★` : ''}`);
  if (n.type === 'prospect' || n.prospect) bits.push(PROSPECT_REASONS[i.reason] || i.reason || '');
  else bits.push(TYPE_LABEL[n.type] || '');
  t.innerHTML = `<strong>${esc(n.name)}</strong><span>${esc(bits.filter(Boolean).join(' · '))}</span>`;
  t.hidden = false;
}
document.addEventListener('mousemove', e => {
  const t = tipEl();
  if (t && !t.hidden) {
    t.style.left = Math.min(window.innerWidth - 240, e.clientX + 14) + 'px';
    t.style.top = (e.clientY + 16) + 'px';
  }
});

Promise.all([
  fetch('./data/network.json').then(r => r.json()),
  fetch('./data/satellite.json').then(r => r.json()),
  new THREE.TextureLoader().loadAsync('./data/satellite.jpg'),
  fetch('./data/visitors.json').then(r => r.json()).catch(() => null),
  fetch('./data/region.json').then(r => r.json()).catch(() => null),
  new THREE.TextureLoader().loadAsync('./data/region.jpg?v=2').catch(() => null),
  fetch('./data/traffic.json').then(r => r.json()).catch(() => null),
  fetch('./data/prospects.json').then(r => r.json()).catch(() => null),
  fetch('./data/history/index.json').then(r => r.json()).catch(() => null)
])
  .then(([data, satMeta, tex, vis, regionMeta, regionTex, traf, pros, hist]) => {
    // Trend arrows need two monthly snapshots; until then prevTraffic stays null.
    if (Array.isArray(hist) && hist.length >= 2) {
      fetch('./data/history/' + hist[hist.length - 2].file).then(r => r.json())
        .then(prev => { prevTraffic = prev; }).catch(() => {});
    }
    traffic = traf;
    prospects = pros;
    if (prospects) {
      Object.entries(prospects.flagged || {}).forEach(([id, f]) => {
        const n = data.nodes.find(x => x.id === id);
        if (n) n.prospect = f;
      });
      (prospects.new || []).forEach(r => {
        data.nodes.push({
          id: 'p-' + r.id, name: r.name, type: 'prospect',
          category: r.category, city: r.city,
          blurb: [r.address, 'Found in a county-wide sweep for businesses without a real website of their own.']
            .filter(Boolean).join(' — '),
          url: null,
          geo: r.lat != null ? toLocal(r.lat, r.lon) : null,
          geo_method: r.geo_method || null,
          drive_min: r.drive_min != null ? r.drive_min : null,
          bearing: Math.abs([...String(r.id)].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 7)) % 360,
          prospect: { reason: r.reason, reviews: r.reviews, rating: r.rating, address: r.address, phone: r.phone }
        });
      });
    }
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
        showTip(h);
        applyFilters();
        applyMotion();
        updateLabelVisibility();
      })
      .onBackgroundClick(() => { clearSelection(); })
      .showNavInfo(false);
    applyAll();
    wireHud();
    applyFilters();
    buildDrawer(); // populated up-front so printing always has the call list
    defaultCamera(0);
    // Deep link: #<node-id> flies straight to that node.
    const hashId = decodeURIComponent((location.hash || '').slice(1));
    if (hashId) {
      const target = net.nodes.find(x => x.id === hashId);
      if (target) setTimeout(() => { selectNode(target); openPanel(target); }, 700);
    }
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
  if (dirty && net) { applyAll(); applyFilters(); }
}).observe(document.documentElement, { attributes: true, attributeFilter: ['data-mode', 'data-palette', 'data-glyph', 'data-labels', 'data-motion', 'data-linkviz'] });

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
