#!/usr/bin/env python3
"""Generates the uncanny werewolf GeckoLib assets.

Outputs (under src/main/resources/assets/uncanny_werewolf/):
  geo/entity/werewolf.geo.json           Bedrock geometry (per-face UV)
  animations/entity/werewolf.animation.json
  textures/entity/werewolf.png           HD texture (TEX_SCALE px per UV unit)
  textures/entity/werewolf_glowmask.png  emissive layer for GeckoLib AutoGlowingGeoLayer

Coordinates are Bedrock model units (16 = 1 block), Y up, the creature faces -Z.
"Left" means +X in Bedrock space. Rotations are Bedrock degrees: +X pitches a bone forward/down.

Run: python3 tools/generate_werewolf.py
"""
import json
import math
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "src/main/resources/assets/uncanny_werewolf")
TEX_SCALE = 4  # texture pixels per UV unit
PAD = 2  # px of edge bleed around every face

# ----------------------------------------------------------------------------
# Model building
# ----------------------------------------------------------------------------

bones = []
bone_by_name = {}


class Bone:
    def __init__(self, name, parent, pivot, rotation=None):
        self.name = name
        self.parent = parent
        self.pivot = [float(v) for v in pivot]
        self.rotation = [float(v) for v in (rotation or [0, 0, 0])]
        self.cubes = []


class Cube:
    def __init__(self, origin, size, mat, opts):
        self.origin = [float(v) for v in origin]
        self.size = [float(v) for v in size]
        self.mat = mat
        self.opts = opts
        self.uv = {}


def bone(name, parent, pivot, rotation=None):
    b = Bone(name, parent, pivot, rotation)
    bones.append(b)
    bone_by_name[name] = b
    return b


def cube(b, origin, size, mat, **opts):
    c = Cube(origin, size, mat, opts)
    b.cubes.append(c)
    return c


def mirror_vec(o, s):
    return [-(o[0] + s[0]), o[1], o[2]]


def bone_pair(name, parent, pivot, rotation=None):
    """Creates <name>_l at pivot and the mirrored <name>_r. Returns (left, right)."""
    rot = rotation or [0, 0, 0]
    # children of a paired bone attach to the same-side twin
    pl = parent + "_l" if parent + "_l" in PAIRED else parent
    pr = parent + "_r" if parent + "_r" in PAIRED else parent
    left = bone(name + "_l", pl, pivot, rot)
    right = bone(name + "_r", pr, [-pivot[0], pivot[1], pivot[2]], [rot[0], -rot[1], -rot[2]])
    PAIRED.add(name + "_l")
    PAIRED.add(name + "_r")
    return left, right


PAIRED = set()


def cube_pair(pair, origin, size, mat, **opts):
    left, right = pair
    cube(left, origin, size, mat, side="l", **opts)
    cube(right, mirror_vec(origin, size), size, mat, side="r", **opts)


def sym_cube(b, origin, size, mat, **opts):
    """Adds a cube and its X-mirrored twin to the same bone."""
    cube(b, origin, size, mat, side="l", **opts)
    cube(b, mirror_vec(origin, size), size, mat, side="r", **opts)


# --- legs: computed first so the hip height puts the paws on the ground -----
L_THIGH, L_SHIN, L_META, PAW_H = 8.0, 7.5, 6.0, 1.5
LEG_ROT = [-28, 62, -52, 18]  # thigh, shin, metatarsal, paw (relative)
_net = np.cumsum(LEG_ROT)
_drop = (L_THIGH * math.cos(math.radians(_net[0])) + L_SHIN * math.cos(math.radians(_net[1]))
         + L_META * math.cos(math.radians(_net[2])) + PAW_H)
H = round(_drop * 4) / 4  # hip height

root = bone("root", None, [0, 0, 0])
body = bone("body", "root", [0, H, 0])
cube(body, [-4.75, H - 2.5, -2.75], [9.5, 5, 5.5], "skin_patchy")
cube(body, [-5, H - 3.5, -3.25], [10, 3, 6.5], "fur", ragged="bottom")

# tail: thin, mangy, segmented
t1 = bone("tail1", "body", [0, H + 1, 2.5], [-35, 0, 0])
cube(t1, [-0.9, H + 0.1, 2.5], [1.8, 1.8, 4.5], "skin_patchy")
cube(t1, [-1.1, H + 0.3, 3.5], [2.2, 1.5, 2], "fur")
t2 = bone("tail2", "tail1", [0, H + 1, 7], [-20, 0, 0])
cube(t2, [-0.75, H + 0.25, 7], [1.5, 1.5, 4.5], "skin_patchy")
t3 = bone("tail3", "tail2", [0, H + 1, 11.5], [-15, 0, 0])
cube(t3, [-0.6, H + 0.4, 11.5], [1.2, 1.2, 4], "skin_patchy")
cube(t3, [-0.9, H + 0.1, 13.25], [1.8, 1.8, 2.75], "fur", ragged="all")

# torso: hunched, starved, pinched waist, ribs pushing through the skin
torso = bone("torso", "body", [0, H + 2, 0], [30, 0, 0])
cube(torso, [-4, H + 2, -2.25], [8, 6, 4.5], "skin_belly")
cube(torso, [-5.5, H + 7.5, -3.25], [11, 8, 6.5], "skin_chest")
for i in range(5):
    y = H + 8.25 + i * 1.4
    w = 4.5 - i * 0.25 if i > 2 else 4.5
    sym_cube(torso, [0.75, y, -3.65], [w, 0.5, 0.75], "rib")
    sym_cube(torso, [5.25, y - 0.25, -2.75], [0.5, 0.5, 5.0], "rib")
cube(torso, [-0.5, H + 8, -3.6], [1, 6.5, 0.6], "rib")
sym_cube(torso, [0.5, H + 15, -3.6], [5, 0.75, 0.75], "rib")
cube(torso, [-6.75, H + 13.5, -1.5], [13.5, 4.5, 5.5], "fur", ragged="bottom")
cube(torso, [-5, H + 7, 2.5], [10, 7.5, 1.75], "fur", ragged="all")
for i in range(3):
    cube(torso, [-0.6, H + 2.5 + i * 1.8, 1.9], [1.2, 1, 1], "rib")
for i in range(4):
    cube(torso, [-0.6, H + 8 + i * 1.8, 3.75], [1.2, 1, 1], "rib")

# neck: long, human adam's apple, stretches during the stare
neck = bone("neck", "torso", [0, H + 16.5, -0.5], [22, 0, 0])
cube(neck, [-2, H + 15.5, -2.5], [4, 5, 4], "skin")
cube(neck, [-3, H + 15.5, -0.5], [6, 3.5, 3.5], "fur", ragged="top")
neck_up = bone("neck_upper", "neck", [0, H + 20, -0.5])
cube(neck_up, [-1.75, H + 16, -2.25], [3.5, 6.5, 3.5], "skin")
cube(neck_up, [-0.5, H + 18.25, -2.6], [1, 1, 0.5], "skin")

F = H + 22  # head pivot height
head_level = bone("head_level", "neck_upper", [0, F, -0.5], [-52, 0, 0])
head_look = bone("head_look", "head_level", [0, F, -0.5])
head = bone("head", "head_look", [0, F, -0.5], [6, 0, 0])

EYE_O = [0.85, F + 2.75, -5.9]
EYE_S = [2.5, 1.5, 0.5]
cube(head, [-4.25, F - 1, -5.5], [8.5, 8, 7.5], "skull")
cube(head, [-4, F + 4.5, -6], [8, 1, 0.75], "skin_brow")
sym_cube(head, [0.75, F + 4.25, -6.0], [2.75, 0.4, 0.6], "skin_lid")
sym_cube(head, [0.75, F + 2.35, -5.8], [2.75, 0.4, 0.4], "skin_bag")
sym_cube(head, [3.25, F + 0.75, -5.75], [1.25, 1.75, 3], "skin_cheek")
cube(head, [-2.5, F + 0.5, -10.5], [5, 2.5, 5], "snout")
cube(head, [-1, F + 3.0, -9.5], [2, 0.5, 4], "skin")
cube(head, [-1, F + 1.25, -11], [2, 2, 1.25], "nose")
cube(head, [-2.4, F - 0.5, -10.25], [4.8, 1, 4.75], "teeth_upper")
cube(head, [-2.2, F - 2, -9.75], [4.4, 1.5, 4.5], "mouth")
sym_cube(head, [4, F - 1.5, -5.25], [1, 3, 4], "fur", ragged="all")
cube(head, [-4.5, F + 5.5, -5.75], [9, 2, 8], "hair")
cube(head, [-4.25, F + 4.75, -5.85], [8.5, 1.25, 0.5], "hair", ragged="bottom")

eye_l = bone("eye_l", "head", [2.1, F + 3.5, -5.6])
eye_r = bone("eye_r", "head", [-2.1, F + 3.5, -5.6])
cube(eye_l, EYE_O, EYE_S, "eye")
cube(eye_r, mirror_vec(EYE_O, EYE_S), EYE_S, "eye")

jaw = bone("jaw", "head", [0, F - 0.5, -4.5])
cube(jaw, [-2.4, F - 2.75, -10.25], [4.8, 1.75, 5.25], "jaw")
cube(jaw, [-2.2, F - 1.5, -10], [4.4, 1, 4.5], "teeth_lower")
cube(jaw, [-1.4, F - 1.6, -9], [2.8, 0.5, 4], "tongue")
cube(jaw, [-1.5, F - 3.25, -10.1], [3, 0.75, 2.25], "skin_chin")

ear_l = bone("ear_l", "head", [3, F + 7, -1.5], [-10, 0, 18])
ear_r = bone("ear_r", "head", [-3, F + 7, -1.5], [-14, 0, -24])
cube(ear_l, [2, F + 7, -2.25], [2.5, 4, 1], "ear")
cube(ear_r, [-4.5, F + 7, -2.25], [2.5, 3, 1], "ear", torn=True)

hair_back = bone("hair_back", "head", [0, F + 6.5, 2])
cube(hair_back, [-4.25, F - 5.5, 1.75], [8.5, 12.5, 0.75], "hair", ragged="bottom")
sym_cube(hair_back, [4.25, F - 3.5, -3.25], [0.6, 10, 5.25], "hair", ragged="bottom")

# arms: far too long, human hands with elongated fingers
arm = bone_pair("arm", "torso", [6, H + 14.5, 0.5], [-40, 0, -4])
cube_pair(arm, [5, H + 5, -0.75], [2.5, 10.5, 2.5], "skin_arm")
cube_pair(arm, [4.5, H + 12, -1.5], [3.5, 4, 4], "fur", ragged="bottom")
cube_pair(arm, [5.25, H + 4.25, 1.25], [2, 1.5, 0.75], "rib")
forearm = bone_pair("forearm", "arm", [6.25, H + 5.5, 0.5], [-14, 0, 0])
cube_pair(forearm, [5.125, H - 4.5, -0.625], [2.25, 10, 2.25], "skin_arm")
cube_pair(forearm, [5, H - 4.75, -0.75], [2.5, 1, 2.5], "rib")
cube_pair(forearm, [5.375, H - 2, 1.5], [1.75, 6, 0.75], "fur", ragged="all")
hand = bone_pair("hand", "forearm", [6.25, H - 4.5, 0.5], [0, 0, 0])
cube_pair(hand, [5.5, H - 8.25, -1.25], [1.5, 3.75, 3.5], "skin_hand")
cube_pair(hand, [5.4, H - 8.75, -1.25], [1.7, 0.75, 3.5], "skin_knuckle")
FINGER_Z = [-0.75, 0.125, 1.0, 1.75]
FINGER_A = [4.0, 4.5, 4.25, 3.25]
FINGER_B = [3.0, 3.5, 3.25, 2.5]
for i, zc in enumerate(FINGER_Z):
    la, lb = FINGER_A[i], FINGER_B[i]
    y0 = H - 8.75
    fa = bone_pair(f"finger{i}a", "hand", [6.25, y0, zc], [0, 0, 8])
    cube_pair(fa, [5.875, y0 - la, zc - 0.375], [0.75, la, 0.75], "skin_finger")
    fb = bone_pair(f"finger{i}b", f"finger{i}a", [6.25, y0 - la, zc], [0, 0, 14])
    cube_pair(fb, [5.9, y0 - la - lb, zc - 0.35], [0.7, lb, 0.7], "skin_finger")
    cube_pair(fb, [5.95, y0 - la - lb - 1.25, zc - 0.3], [0.6, 1.25, 0.6], "nail")
thumb = bone_pair("thumb", "hand", [6, H - 6.75, -1.25], [-20, 0, 10])
cube_pair(thumb, [5.625, H - 10.25, -1.625], [0.75, 3.5, 0.75], "skin_finger")
cube_pair(thumb, [5.7, H - 11.25, -1.55], [0.6, 1, 0.6], "nail")

# legs: digitigrade wolf legs
leg = bone_pair("leg", "body", [3, H, 0], [LEG_ROT[0], 0, -3])
cube_pair(leg, [1, H - 8.5, -2.75], [4.5, 9, 5], "fur", ragged="bottom")
shin = bone_pair("shin", "leg", [3.25, H - L_THIGH, 0], [LEG_ROT[1], 0, 0])
cube_pair(shin, [1.75, H - L_THIGH - L_SHIN, -1.25], [3, L_SHIN, 3], "fur")
cube_pair(shin, [2, H - 12, 1.5], [2.5, 4, 1], "fur", ragged="all")
y_ankle = H - L_THIGH - L_SHIN
meta = bone_pair("meta", "shin", [3.25, y_ankle, 0], [LEG_ROT[2], 0, 0])
cube_pair(meta, [2, y_ankle - L_META, -1], [2.5, L_META, 2.25], "skin_patchy")
y_paw = y_ankle - L_META
paw = bone_pair("paw", "meta", [3.25, y_paw, 0], [LEG_ROT[3], 0, 0])
cube_pair(paw, [1.5, y_paw - PAW_H, -3.25], [3.5, PAW_H, 4.25], "paw")
for i in range(4):
    x = 1.5 + i * 0.95
    cube_pair(paw, [x, y_paw - PAW_H, -4.25], [0.75, 1, 1], "paw")
    cube_pair(paw, [x + 0.05, y_paw - PAW_H, -5.0], [0.65, 0.75, 0.75], "claw")

# ----------------------------------------------------------------------------
# Forward kinematics (sanity printout + bounding box), Bedrock -> three-style space
# ----------------------------------------------------------------------------


def rot_matrix(rx, ry, rz):
    # Bedrock -> render: X and Y angles negated, applied in Z*Y*X order (as Blockbench / GeckoLib)
    ax, ay, az = math.radians(-rx), math.radians(-ry), math.radians(rz)
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def world_matrix(b, extra=None):
    extra = extra or {}
    m = np.eye(4)
    chain = []
    while b:
        chain.append(b)
        b = bone_by_name.get(b.parent) if b.parent else None
    for bb in reversed(chain):
        p = np.array([-bb.pivot[0], bb.pivot[1], bb.pivot[2]])
        r = np.array(bb.rotation) + np.array(extra.get(bb.name, [0, 0, 0]))
        T = np.eye(4)
        T[:3, :3] = rot_matrix(*r)
        T[:3, 3] = p - T[:3, :3] @ p
        m = m @ T
    return m


def to_world(bname, point_b, extra=None):
    m = world_matrix(bone_by_name[bname], extra)
    p = np.array([-point_b[0], point_b[1], point_b[2], 1.0])
    return m @ p


def model_bounds(extra=None):
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for b in bones:
        m = world_matrix(b, extra)
        for c in b.cubes:
            o, s = c.origin, c.size
            for dx in (0, s[0]):
                for dy in (0, s[1]):
                    for dz in (0, s[2]):
                        p = m @ np.array([-(o[0] + dx), o[1] + dy, o[2] + dz, 1.0])
                        lo, hi = np.minimum(lo, p[:3]), np.maximum(hi, p[:3])
    return lo, hi


# ----------------------------------------------------------------------------
# Texture painting
# ----------------------------------------------------------------------------

rng_master = np.random.default_rng(1666)


def value_noise(h, w, cell_y, cell_x, rng):
    gh, gw = int(h / cell_y) + 3, int(w / cell_x) + 3
    g = rng.random((gh, gw))
    ys = np.arange(h) / cell_y
    xs = np.arange(w) / cell_x
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    fy = (ys - y0)[:, None]
    fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy


def fbm(h, w, cell, rng, octaves=3):
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * value_noise(h, w, max(cell / 2 ** o, 1), max(cell / 2 ** o, 1), rng)
        tot += amp
        amp *= 0.5
    return out / tot


def solid(h, w, rgb):
    a = np.zeros((h, w, 4))
    a[..., :3] = rgb
    a[..., 3] = 1
    return a


def shade_vertical(img, face, amount=0.18):
    """Fake ambient occlusion: darken the lower part of side faces."""
    h = img.shape[0]
    if face in ("north", "south", "east", "west") and h > 1:
        g = np.linspace(0, 1, h)[:, None] ** 1.5
        img[..., :3] *= (1 - amount * g)[..., None]
    elif face == "down":
        img[..., :3] *= 1 - amount * 1.2
    elif face == "up":
        img[..., :3] *= 1 + amount * 0.25
    return img


SKIN = np.array([0.80, 0.73, 0.68])
SKIN_SICK = np.array([0.70, 0.70, 0.64])


def paint_skin(h, w, face, rng, base=SKIN, veins=True, bruise=True):
    img = solid(h, w, base)
    n = fbm(h, w, 6, rng)
    sick = fbm(h, w, 10, rng)[..., None]
    img[..., :3] = img[..., :3] * (0.9 + 0.2 * n[..., None])
    img[..., :3] = img[..., :3] * (1 - sick * 0.5) + SKIN_SICK * sick * 0.5
    if bruise:
        b = fbm(h, w, 8, rng)
        m = np.clip((b - 0.62) * 4, 0, 1)[..., None]
        img[..., :3] = img[..., :3] * (1 - m * 0.45) + np.array([0.45, 0.36, 0.45]) * m * 0.45
    if veins and h * w > 30:
        count = max(1, (h * w) // 260)
        for _ in range(count):
            y, x = rng.integers(0, h), rng.integers(0, w)
            for _s in range(rng.integers(6, 18)):
                if 0 <= y < h and 0 <= x < w:
                    img[y, x, :3] = img[y, x, :3] * 0.7 + np.array([0.42, 0.50, 0.62]) * 0.3
                y += rng.integers(-1, 2)
                x += rng.choice([-1, 0, 1, 1])
    dirt = rng.random((h, w)) < 0.025
    img[dirt, :3] *= 0.82
    return img


FUR = np.array([0.36, 0.32, 0.29])


def paint_fur(h, w, face, rng, patchy=True):
    img = solid(h, w, FUR)
    if face in ("up", "down"):
        streak = value_noise(h, w, 2, 2, rng)
    else:
        streak = value_noise(h, w, 7, 1, rng)
    fine = rng.random((h, w))
    v = 0.65 + 0.55 * streak + 0.15 * fine
    img[..., :3] *= v[..., None]
    tips = np.clip(streak - 0.75, 0, 1)[..., None] * 2.5
    img[..., :3] = img[..., :3] * (1 - tips) + np.array([0.52, 0.49, 0.46]) * tips
    if patchy:
        holes = fbm(h, w, 6, rng)
        m = holes > 0.66
        sk = paint_skin(h, w, face, rng, base=np.array([0.78, 0.60, 0.58]), veins=False, bruise=False)
        img[m] = sk[m]
        edge = (holes > 0.62) & ~m
        img[edge, :3] *= 0.6
    return img


def paint_hair(h, w, face, rng):
    img = solid(h, w, np.array([0.075, 0.065, 0.065]))
    streak = value_noise(h, w, 12, 1, rng) if face not in ("up", "down") else value_noise(h, w, 1, 6, rng)
    img[..., :3] *= (0.6 + 0.9 * streak)[..., None]
    gloss = (streak > 0.8)[..., None]
    img[..., :3] = np.where(gloss, img[..., :3] + 0.12, img[..., :3])
    return img


def apply_ragged(img, rng, where, depth_frac=0.35):
    """Cuts transparent strands into an edge so hair / fur looks stringy."""
    h, w = img.shape[:2]
    if where in ("bottom", "all"):
        for x in range(w):
            d = int(rng.random() ** 2 * h * depth_frac)
            if d:
                img[h - d:, x, 3] = 0
    if where in ("top", "all"):
        for x in range(w):
            d = int(rng.random() ** 3 * h * depth_frac * 0.7)
            if d:
                img[:d, x, 3] = 0
    return img


def paint_teeth(h, w, face, rng, upper):
    img = solid(h, w, np.array([0.18, 0.05, 0.06]))
    if face in ("up", "down"):
        inner = (face == "down") == upper  # biting surface
        if not inner:
            return solid(h, w, np.array([0.55, 0.30, 0.32]))
        tooth = solid(h, w, np.array([0.86, 0.82, 0.68]))
        tooth[..., :3] *= (0.9 + 0.15 * rng.random((h, w)))[..., None]
        return tooth
    tw = 4  # one tooth per UV unit, flat and human
    gum = max(1, h // 4)
    for x0 in range(0, w, tw):
        col = np.array([0.90, 0.86, 0.72]) * (0.88 + 0.16 * rng.random())
        if rng.random() < 0.12:
            col = np.array([0.66, 0.58, 0.38])  # rotten one
        for x in range(x0, min(x0 + tw - 1, w)):
            for y in range(h):
                yy = y if upper else h - 1 - y
                if yy < gum:
                    continue
                shade = 1 - 0.25 * (yy - gum) / max(h - gum, 1) if upper else 1
                img[y, x, :3] = col * shade
    gum_rows = slice(0, gum) if upper else slice(h - gum, h)
    img[gum_rows, :, :3] = np.array([0.62, 0.36, 0.38]) * (0.9 + 0.1 * rng.random((gum, w, 1)))
    return img


def paint_eye(h, w, face, rng, side):
    img = solid(h, w, np.array([0.93, 0.90, 0.84]))
    if face != "north":
        return solid(h, w, np.array([0.80, 0.70, 0.66]))
    for _ in range(2):  # bloodshot veins from the corners
        y = rng.integers(0, h)
        x = 0 if rng.random() < 0.5 else w - 1
        for _s in range(4):
            if 0 <= y < h and 0 <= x < w:
                img[y, x, :3] = np.array([0.78, 0.35, 0.33])
            x += 1 if x < w / 2 else -1
            y += rng.integers(-1, 2)
    cy, cx = (h - 1) / 2 + 0.3, (w - 1) / 2 + (0.6 if side == "l" else -0.6)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((yy - cy) ** 2 + ((xx - cx) * 0.95) ** 2)
    r = h * 0.48
    iris = d < r
    img[iris, :3] = np.array([0.50, 0.62, 0.64])
    ring = (d >= r * 0.75) & iris
    img[ring, :3] = np.array([0.30, 0.40, 0.44])
    pupil = d < r * 0.28  # pinpoint pupil
    img[pupil, :3] = np.array([0.04, 0.03, 0.03])
    hy, hx = int(cy - 1), int(cx + 1)
    if 0 <= hy < h and 0 <= hx < w:
        img[hy, hx, :3] = 1.0
    img[0, :, :3] *= 0.55  # lid shadow
    return img


def paint_skull(h, w, face, rng, cube_obj):
    img = paint_skin(h, w, face, rng)
    if face == "north":
        o = cube_obj.origin
        s = cube_obj.size
        for ex in (EYE_O[0] + EYE_S[0] / 2, -(EYE_O[0] + EYE_S[0] / 2)):
            # north face: column 0 is the max-X (render) side; symmetric so either mapping works
            cx = (ex - o[0]) * TEX_SCALE
            cy = (o[1] + s[1] - (EYE_O[1] + EYE_S[1] / 2)) * TEX_SCALE
            yy, xx = np.mgrid[0:h, 0:w]
            d = ((xx - cx) / (EYE_S[0] * TEX_SCALE * 0.85)) ** 2 + ((yy - cy) / (EYE_S[1] * TEX_SCALE * 1.2)) ** 2
            m = np.clip(1.4 - d, 0, 1)[..., None]
            img[..., :3] = img[..., :3] * (1 - m * 0.55) + np.array([0.30, 0.22, 0.28]) * m * 0.55
        for row in (int(h * 0.12), int(h * 0.2)):
            img[row, int(w * 0.25):int(w * 0.75), :3] *= 0.84  # forehead creases
    if face == "up":
        img = paint_hair(h, w, face, rng)
    return shade_vertical(img, face, 0.12)


def paint_blood(img, rng, amount=0.3, bottom_bias=True):
    h, w = img.shape[:2]
    n = fbm(h, w, 3, rng)
    if bottom_bias:
        n = n * 0.6 + np.linspace(0, 0.5, h)[:, None]
    m = np.clip((n - (1 - amount)) * 5, 0, 1)[..., None]
    img[..., :3] = img[..., :3] * (1 - m) + np.array([0.30, 0.06, 0.05]) * m
    return img


def paint_material(c, face, h, w, rng):
    mat = c.mat
    side = c.opts.get("side", "l")
    if mat == "skin":
        img = shade_vertical(paint_skin(h, w, face, rng), face)
    elif mat == "skin_patchy":
        img = paint_fur(h, w, face, rng, patchy=True)
        img = shade_vertical(img, face)
    elif mat in ("skin_belly", "skin_chest"):
        img = paint_skin(h, w, face, rng)
        if face == "north" and mat == "skin_chest":
            for i in range(5):
                y = int(h * (0.12 + i * 0.17))
                if y + 2 < h:
                    img[y + 2:y + 3, :, :3] *= 0.72  # shadow under each rib
        if face == "north" and mat == "skin_belly":
            g = np.abs(np.linspace(-1, 1, w))[None, :]
            img[..., :3] *= (0.78 + 0.22 * g)[..., None]  # sunken stomach
        img = shade_vertical(img, face, 0.25)
    elif mat == "rib":
        img = shade_vertical(paint_skin(h, w, face, rng, base=np.array([0.88, 0.82, 0.76]), veins=False), face, 0.3)
    elif mat in ("skin_brow", "skin_lid", "skin_cheek", "skin_chin"):
        img = paint_skin(h, w, face, rng, veins=False)
        if mat == "skin_lid":
            img[..., :3] *= 0.86
        img = shade_vertical(img, face, 0.3)
    elif mat == "skin_bag":
        img = paint_skin(h, w, face, rng, base=np.array([0.55, 0.45, 0.50]), veins=False)
    elif mat in ("skin_arm", "skin_hand"):
        img = shade_vertical(paint_skin(h, w, face, rng), face, 0.2)
        if mat == "skin_arm":
            img = paint_blood(img, rng, 0.08)
    elif mat == "skin_knuckle":
        img = paint_skin(h, w, face, rng, veins=False)
        img[:, ::3, :3] *= 0.85
    elif mat == "skin_finger":
        img = paint_skin(h, w, face, rng, veins=False)
        for y in range(2, h, 5):
            img[y, :, :3] *= 0.75  # knuckle creases
        img = paint_blood(img, rng, 0.22)
    elif mat == "nail":
        img = solid(h, w, np.array([0.70, 0.64, 0.48]))
        img[..., :3] *= (0.85 + 0.2 * rng.random((h, w)))[..., None]
        img[-max(1, h // 3):, :, :3] *= 0.55
        img = paint_blood(img, rng, 0.25)
    elif mat == "fur":
        img = shade_vertical(paint_fur(h, w, face, rng, patchy=True), face, 0.25)
    elif mat == "hair":
        img = paint_hair(h, w, face, rng)
    elif mat == "skull":
        img = paint_skull(h, w, face, rng, c)
    elif mat == "snout":
        img = paint_skin(h, w, face, rng, veins=False)
        if face == "up":
            img[:, w // 2 - 1:w // 2 + 1, :3] *= 0.9
        if face in ("north", "east", "west"):
            img[-2:, :, :3] = np.array([0.50, 0.36, 0.38])  # thin human lips
        img = shade_vertical(img, face, 0.2)
    elif mat == "nose":
        img = paint_skin(h, w, face, rng, veins=False, base=np.array([0.82, 0.68, 0.66]))
        if face in ("north", "down"):
            for nx in (1, w - 3):
                img[h - 3:h - 1 if face == "north" else h - 1, nx:nx + 2, :3] = np.array([0.15, 0.08, 0.08])
        img = shade_vertical(img, face, 0.2)
    elif mat == "teeth_upper":
        img = paint_teeth(h, w, face, rng, True)
    elif mat == "teeth_lower":
        img = paint_teeth(h, w, face, rng, False)
    elif mat == "mouth":
        img = solid(h, w, np.array([0.16, 0.04, 0.05]))
        img[..., :3] *= (0.8 + 0.4 * rng.random((h, w)))[..., None]
    elif mat == "tongue":
        img = solid(h, w, np.array([0.58, 0.36, 0.40]))
        img[..., :3] *= (0.85 + 0.25 * fbm(h, w, 3, rng))[..., None]
    elif mat == "jaw":
        img = paint_skin(h, w, face, rng, veins=False)
        if face in ("north", "east", "west"):
            img[:2, :, :3] = np.array([0.50, 0.36, 0.38])
        img = paint_blood(img, rng, 0.25)
        img = shade_vertical(img, face, 0.3)
    elif mat == "eye":
        img = paint_eye(h, w, face, rng, side)
    elif mat == "ear":
        img = paint_fur(h, w, face, rng, patchy=False)
        if face == "north":
            inner = paint_skin(h, w, face, rng, base=np.array([0.66, 0.48, 0.50]), veins=True, bruise=False)
            img[1:, 1:-1] = inner[1:, 1:-1]
        if c.opts.get("torn"):
            for x in range(w):
                d = int((math.sin(x * 1.7) * 0.5 + 0.5) * h * 0.3 + rng.random() * 2)
                img[:d, x, 3] = 0
                if d < h:
                    img[d, x, :3] = np.array([0.45, 0.15, 0.13])
    elif mat == "paw":
        img = shade_vertical(paint_fur(h, w, face, rng, patchy=False), face, 0.3)
        if face == "down":
            img = solid(h, w, np.array([0.17, 0.13, 0.13]))
    elif mat == "claw":
        img = solid(h, w, np.array([0.10, 0.09, 0.09]))
        img[..., :3] += (np.linspace(0, 0.12, h)[:, None] * np.ones((1, w)))[..., None]
    else:
        raise ValueError(mat)
    rag = c.opts.get("ragged")
    if rag and face in ("north", "south", "east", "west"):
        img = apply_ragged(img, rng, rag)
    return np.clip(img, 0, 1)


def glow_material(c, face, h, w, img):
    """Eyes reflect light like an animal's (tapetum) even though they look human."""
    out = np.zeros((h, w, 4))
    if c.mat == "eye" and face == "north":
        iris = (np.abs(img[..., 0] - 0.5) < 0.12) & (img[..., 2] > 0.5)
        ring = (np.abs(img[..., 0] - 0.30) < 0.05) & (img[..., 2] > 0.38) & (img[..., 2] < 0.5)
        m = iris | ring
        out[m, :3] = np.array([0.85, 0.95, 0.70])
        out[m, 3] = 0.55
    return out


# ----------------------------------------------------------------------------
# UV packing
# ----------------------------------------------------------------------------

FACE_DIMS = {
    "north": (0, 1), "south": (0, 1), "east": (2, 1), "west": (2, 1), "up": (0, 2), "down": (0, 2),
}


def pack():
    rects = []
    for b in bones:
        for c in b.cubes:
            for face, (iw, ih) in FACE_DIMS.items():
                w, h = c.size[iw], c.size[ih]
                if w <= 0 or h <= 0:
                    continue
                pw, ph = max(1, int(round(w * TEX_SCALE))), max(1, int(round(h * TEX_SCALE)))
                rects.append((c, face, w, h, pw, ph))
    rects.sort(key=lambda r: (-r[5], -r[4]))
    width = 1024
    x = y = row_h = 0
    placements = []
    for r in rects:
        pw, ph = r[4] + 2 * PAD, r[5] + 2 * PAD
        if x + pw > width:
            x, y, row_h = 0, y + row_h, 0
        placements.append((r, x + PAD, y + PAD))
        x += pw
        row_h = max(row_h, ph)
    height = y + row_h
    tex_h = 1
    while tex_h < height:
        tex_h *= 2
    return placements, width, tex_h


def build_texture():
    placements, width, height = pack()
    tex = np.zeros((height, width, 4))
    glow = np.zeros((height, width, 4))
    for idx, ((c, face, w, h, pw, ph), px, py) in enumerate(placements):
        rng = np.random.default_rng(1000 + idx)
        img = paint_material(c, face, ph, pw, rng)
        g = glow_material(c, face, ph, pw, img)
        # edge bleed so mip/linear sampling and float UVs never show seams
        padded = np.pad(img, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
        tex[py - PAD:py + ph + PAD, px - PAD:px + pw + PAD] = padded
        glow[py:py + ph, px:px + pw] = g
        c.uv[face] = {"uv": [px / TEX_SCALE, py / TEX_SCALE], "uv_size": [pw / TEX_SCALE, ph / TEX_SCALE]}
    return tex, glow, width // TEX_SCALE, height // TEX_SCALE


# ----------------------------------------------------------------------------
# Animations (sampled at 20 fps = one keyframe per game tick)
# ----------------------------------------------------------------------------

FPS = 20
TAU = 2 * math.pi


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def window(t, a, b, rise=0.05, fall=0.05):
    """1 inside [a,b] with short ramps; jerky when rise/fall are tiny."""
    if t < a - rise or t > b + fall:
        return 0.0
    if t < a:
        return smooth((t - (a - rise)) / rise)
    if t > b:
        return 1 - smooth((t - b) / fall)
    return 1.0


def bump(t, center, width):
    d = (t - center) / width
    return math.exp(-d * d * 4)


def anim_idle():
    L = 6.0
    w = TAU / L

    def tilt(t):
        return 28 * window(t, 2.45, 4.25, 0.05, 0.35)

    def jerk(t):
        return 3 * (window(t, 1.1, 1.15, 0.01, 0.05) - window(t, 5.2, 5.25, 0.01, 0.05))

    eye_steps = [(0.0, 0.0), (0.9, 0.12), (1.6, -0.1), (2.5, 0.0), (3.4, -0.14), (4.6, 0.08), (5.4, 0.0)]

    def eye_x(t):
        v = 0.0
        for ts, val in eye_steps:
            if t >= ts:
                v = val
        return v

    tracks = {
        "body": {"position": lambda t: [0, 0.15 * math.sin(2 * w * t), 0]},
        "torso": {"rotation": lambda t: [1.5 * math.sin(2 * w * t), 0, 0]},
        "neck": {"rotation": lambda t: [-1.0 * math.sin(2 * w * t), 0, 0]},
        "head": {"rotation": lambda t: [-6 * tilt(t) / 28 - 0.5 * math.sin(2 * w * t),
                                        6 * math.sin(w * t) + jerk(t),
                                        3 * math.sin(2 * w * t + 1) + tilt(t)]},
        "jaw": {"rotation": lambda t: [3 * window(t, 0.5, 1.8) * abs(math.sin(TAU * 3 * t))
                                       + 2 * window(t, 3.6, 4.0) * abs(math.sin(TAU * 4 * t)), 0, 0]},
        "eye_l": {"position": lambda t: [eye_x(t), 0, 0]},
        "eye_r": {"position": lambda t: [eye_x((t - 0.2) % L), 0, 0]},  # lags behind the other eye
        "ear_l": {"rotation": lambda t: [-15 * window(t, 3.0, 3.1, 0.03, 0.2), 0, 0]},
        "ear_r": {"rotation": lambda t: [-10 * window(t, 5.0, 5.1, 0.03, 0.2), 0, 4 * window(t, 5.0, 5.1, 0.03, 0.2)]},
        "hair_back": {"rotation": lambda t: [1.5 + 1.5 * math.sin(w * t), 0, 1 * math.sin(2 * w * t)]},
        "tail1": {"rotation": lambda t: [2 * math.sin(2 * w * t), 10 * math.sin(w * t), 0]},
        "tail2": {"rotation": lambda t: [0, 8 * math.sin(w * t - 0.8), 0]},
        "tail3": {"rotation": lambda t: [0, 8 * math.sin(w * t - 1.6), 0]},
    }
    for s, sgn, ph in (("l", 1, 0), ("r", -1, 2.0)):
        tracks[f"arm_{s}"] = {"rotation": lambda t, ph=ph, sgn=sgn: [2 * math.sin(w * t + ph), 0, -1.5 * sgn * math.sin(2 * w * t + ph)]}
        tracks[f"forearm_{s}"] = {"rotation": lambda t, ph=ph: [-1.5 * math.sin(w * t + ph + 0.6), 0, 0]}
        for i in range(4):
            start = (0.8 if s == "l" else 4.0) + i * 0.12

            def fa(t, start=start, sgn=sgn, i=i):
                return [0, 0, sgn * (25 * window(t, start, start + 0.1, 0.04, 0.3) + 3 * math.sin(w * t + i))]

            def fb(t, start=start, sgn=sgn):
                return [0, 0, sgn * 30 * window(t, start + 0.03, start + 0.12, 0.04, 0.3)]

            tracks[f"finger{i}a_{s}"] = {"rotation": fa}
            tracks[f"finger{i}b_{s}"] = {"rotation": fb}
    return "animation.werewolf.idle", L, True, tracks


def anim_walk():
    L = 1.6
    tracks = {}

    def P(t):
        return TAU * t / L

    def leg_tracks(s, off):
        def swing(t):
            return 24 * math.sin(P(t) + off)

        def flex(t):
            return max(0.0, -math.cos(P(t) + off))

        tracks[f"leg_{s}"] = {"rotation": lambda t: [swing(t), 0, 0]}
        tracks[f"shin_{s}"] = {"rotation": lambda t: [28 * flex(t), 0, 0]}
        tracks[f"meta_{s}"] = {"rotation": lambda t: [-18 * flex(t), 0, 0]}
        tracks[f"paw_{s}"] = {"rotation": lambda t: [-(swing(t) + 10 * flex(t)) * 0.8, 0, 0]}

    leg_tracks("l", 0)
    leg_tracks("r", math.pi)
    tracks["body"] = {
        "position": lambda t: [0, 0.35 * math.cos(2 * P(t)) - 0.3, 0],
        "rotation": lambda t: [0, 4 * math.sin(P(t)), 2.5 * math.sin(P(t))],
    }
    tracks["torso"] = {"rotation": lambda t: [3 + 1.5 * math.cos(2 * P(t)), -3 * math.sin(P(t)), -1 * math.sin(P(t))]}
    # the head is stabilised against the gait: it glides while everything else lurches
    tracks["head"] = {"rotation": lambda t: [-3 - 1.5 * math.cos(2 * P(t)), -1 * math.sin(P(t)), -1.5 * math.sin(P(t))]}
    tracks["jaw"] = {"rotation": lambda t: [3, 0, 0]}
    tracks["hair_back"] = {"rotation": lambda t: [3 + 2 * math.sin(2 * P(t)), 0, 2 * math.sin(P(t))]}
    tracks["tail1"] = {"rotation": lambda t: [3 * math.cos(2 * P(t)), 15 * math.sin(P(t)), 0]}
    tracks["tail2"] = {"rotation": lambda t: [0, 12 * math.sin(P(t) - 0.9), 0]}
    tracks["tail3"] = {"rotation": lambda t: [0, 12 * math.sin(P(t) - 1.8), 0]}
    for s, sgn, off in (("l", 1, math.pi), ("r", -1, 0)):
        tracks[f"arm_{s}"] = {"rotation": lambda t, off=off, sgn=sgn: [-8 * math.sin(P(t) + off - 0.6), 0, sgn * 2 * math.sin(P(t))]}
        tracks[f"forearm_{s}"] = {"rotation": lambda t, off=off: [-4 - 6 * math.sin(P(t) + off - 1.2), 0, 0]}
        tracks[f"hand_{s}"] = {"rotation": lambda t, off=off: [-4 * math.sin(P(t) + off - 1.8), 0, 0]}
        for i in range(4):
            tracks[f"finger{i}a_{s}"] = {"rotation": lambda t, off=off, sgn=sgn, i=i: [-3 * math.sin(P(t) + off - 2.2 - i * 0.2), 0, sgn * 4]}
    return "animation.werewolf.walk", L, True, tracks


def anim_run():
    """Drops onto all fours and gallops; the arms become front legs."""
    L = 0.7
    tracks = {}

    def P(t):
        return TAU * t / L

    tracks["body"] = {
        "position": lambda t: [0, -3 + 1.2 * math.sin(P(t) + 0.8), 0],
        "rotation": lambda t: [50 + 6 * math.sin(P(t)), 0, 0],
    }
    tracks["torso"] = {"rotation": lambda t: [-4 * math.sin(P(t) + 0.5), 0, 0]}
    tracks["neck"] = {"rotation": lambda t: [-18 + 3 * math.sin(P(t) + 1), 0, 0]}
    tracks["head"] = {"rotation": lambda t: [-34 - 6 * math.sin(P(t) + 0.5), 0, 0]}
    tracks["jaw"] = {"rotation": lambda t: [16 + 6 * math.sin(2 * P(t)), 0, 0]}
    tracks["ear_l"] = {"rotation": lambda t: [-35, 0, -8]}
    tracks["ear_r"] = {"rotation": lambda t: [-35, 0, 8]}
    tracks["hair_back"] = {"rotation": lambda t: [40 + 8 * math.sin(2 * P(t)), 0, 0]}
    tracks["tail1"] = {"rotation": lambda t: [10 + 8 * math.sin(P(t)), 0, 0]}
    tracks["tail2"] = {"rotation": lambda t: [12 + 8 * math.sin(P(t) - 0.8), 0, 0]}
    tracks["tail3"] = {"rotation": lambda t: [10 + 8 * math.sin(P(t) - 1.6), 0, 0]}
    for s, off in (("l", 0.0), ("r", 0.45)):
        tracks[f"leg_{s}"] = {"rotation": lambda t, off=off: [-50 + 38 * math.sin(P(t) + off), 0, 0]}
        tracks[f"shin_{s}"] = {"rotation": lambda t, off=off: [30 * max(0.0, -math.cos(P(t) + off)), 0, 0]}
        tracks[f"meta_{s}"] = {"rotation": lambda t, off=off: [-20 * max(0.0, -math.cos(P(t) + off)), 0, 0]}
        tracks[f"paw_{s}"] = {"rotation": lambda t, off=off: [-25 * math.sin(P(t) + off), 0, 0]}
    for s, sgn, off in (("l", 1, math.pi), ("r", -1, math.pi + 0.5)):
        tracks[f"arm_{s}"] = {"rotation": lambda t, off=off: [-42 + 42 * math.sin(P(t) + off), 0, 0]}
        tracks[f"forearm_{s}"] = {"rotation": lambda t, off=off: [-8 + 30 * max(0.0, math.cos(P(t) + off)), 0, 0]}
        tracks[f"hand_{s}"] = {"rotation": lambda t, off=off: [-20 * math.sin(P(t) + off), 0, 0]}
        for i in range(4):
            tracks[f"finger{i}a_{s}"] = {"rotation": lambda t, sgn=sgn: [-35, 0, sgn * -4]}
            tracks[f"finger{i}b_{s}"] = {"rotation": lambda t, sgn=sgn: [-25, 0, 0]}
    return "animation.werewolf.run", L, True, tracks


def anim_attack():
    L = 1.0

    def k(t, pts):
        """Piecewise smooth interpolation through (time, value) points."""
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t0 <= t <= t1:
                return v0 + (v1 - v0) * smooth((t - t0) / (t1 - t0))
        return pts[-1][1]

    tracks = {
        "body": {"position": lambda t: [0, 0, k(t, [(0, 0), (0.25, 1.5), (0.4, -4), (0.6, -4), (1.0, 0)])]},
        "torso": {"rotation": lambda t: [k(t, [(0, 0), (0.25, -14), (0.4, 22), (0.65, 18), (1.0, 0)]), 0, 0]},
        "neck_upper": {"position": lambda t: [0, k(t, [(0, 0), (0.3, 1), (0.42, 3.5), (0.7, 3), (1.0, 0)]), 0]},
        "head": {"rotation": lambda t: [k(t, [(0, 0), (0.25, -18), (0.4, 8), (1.0, 0)]),
                                        0, k(t, [(0, 0), (0.3, 0), (0.42, 12), (0.8, 10), (1.0, 0)])]},
        # the jaw unhinges far past anything natural
        "jaw": {"rotation": lambda t: [k(t, [(0, 0), (0.2, 30), (0.3, 75), (0.6, 75), (1.0, 0)]), 0, 0]},
        "ear_l": {"rotation": lambda t: [k(t, [(0, 0), (0.25, -30), (0.8, -30), (1, 0)]), 0, 0]},
        "ear_r": {"rotation": lambda t: [k(t, [(0, 0), (0.25, -30), (0.8, -30), (1, 0)]), 0, 0]},
        "hair_back": {"rotation": lambda t: [k(t, [(0, 0), (0.4, 25), (0.6, 10), (1, 0)]), 0, 0]},
    }
    for s, sgn, delay in (("l", 1, 0.0), ("r", -1, 0.06)):
        tracks[f"arm_{s}"] = {"rotation": lambda t, d=delay, sgn=sgn: [
            k(t, [(0, 0), (0.25 + d, -115), (0.42 + d, 15), (0.7, 5), (1.0, 0)]), 0,
            sgn * k(t, [(0, 0), (0.25 + d, -20), (0.42 + d, 10), (1.0, 0)])]}
        tracks[f"forearm_{s}"] = {"rotation": lambda t, d=delay: [k(t, [(0, 0), (0.25 + d, -30), (0.42 + d, 0), (1.0, 0)]), 0, 0]}
        for i in range(4):
            tracks[f"finger{i}a_{s}"] = {"rotation": lambda t, sgn=sgn, i=i: [0, 0, sgn * k(t, [(0, 0), (0.25, -18 + i * 4), (0.45, 30), (0.8, 10), (1.0, 0)])]}
            tracks[f"finger{i}b_{s}"] = {"rotation": lambda t, sgn=sgn: [0, 0, sgn * k(t, [(0, 0), (0.25, -14), (0.45, 35), (1.0, 0)])]}
    return "animation.werewolf.attack", L, False, tracks


def anim_stare():
    """Played while a player looks at it: it freezes, stands taller, the neck lengthens and the head
    lolls sideways at an impossible angle while it smiles."""
    L = 4.0
    w = TAU / L

    tracks = {
        "body": {"position": lambda t: [0, 1.0, 0]},
        "leg_l": {"rotation": lambda t: [8, 0, 0]},
        "leg_r": {"rotation": lambda t: [8, 0, 0]},
        "shin_l": {"rotation": lambda t: [-14, 0, 0]},
        "shin_r": {"rotation": lambda t: [-14, 0, 0]},
        "meta_l": {"rotation": lambda t: [8, 0, 0]},
        "meta_r": {"rotation": lambda t: [8, 0, 0]},
        "paw_l": {"rotation": lambda t: [-2, 0, 0]},
        "paw_r": {"rotation": lambda t: [-2, 0, 0]},
        "torso": {"rotation": lambda t: [-12, 0, 0]},
        "neck": {"rotation": lambda t: [-4, 0, 0]},
        "neck_upper": {"position": lambda t: [0, 3.5 + 0.3 * math.sin(w * t), 0]},
        "head": {"rotation": lambda t: [10, 4 * math.sin(w * t),
                                        68 + 5 * math.sin(w * t) + 9 * window(t, 2.0, 2.1, 0.02, 0.05)]},
        "jaw": {"rotation": lambda t: [5 + 1.5 * math.sin(2 * w * t), 0, 0]},
        "ear_l": {"rotation": lambda t: [12, 0, 0]},
        "ear_r": {"rotation": lambda t: [12, 0, 0]},
        "hair_back": {"rotation": lambda t: [0, 0, -40]},  # hangs down with gravity, not with the head
        "tail1": {"rotation": lambda t: [-15, 0, 0]},
        "tail2": {"rotation": lambda t: [-10, 0, 0]},
    }
    for s, sgn, ph in (("l", 1, 0.0), ("r", -1, 1.3)):
        tracks[f"arm_{s}"] = {"rotation": lambda t, ph=ph, sgn=sgn: [-6 + 2 * math.sin(w * t + ph), 0, sgn * 3]}
        tracks[f"forearm_{s}"] = {"rotation": lambda t: [-10, 0, 0]}
        for i in range(4):
            tracks[f"finger{i}a_{s}"] = {"rotation": lambda t, ph=ph, sgn=sgn, i=i: [0, 0, sgn * (15 + 15 * math.sin(w * t + ph - i * 0.5))]}
            tracks[f"finger{i}b_{s}"] = {"rotation": lambda t, ph=ph, sgn=sgn, i=i: [0, 0, sgn * (10 + 20 * math.sin(w * t + ph - i * 0.5 - 0.4))]}
    return "animation.werewolf.stare", L, True, tracks


def r2(v):
    v = round(v, 2)
    return 0.0 if v == 0 else v


def build_animations():
    out = {"format_version": "1.8.0", "animations": {}}
    for fn in (anim_idle, anim_walk, anim_run, anim_attack, anim_stare):
        name, L, loop, tracks = fn()
        frames = int(round(L * FPS))
        anim = {"loop": loop, "animation_length": L, "bones": {}}
        for bname, chans in tracks.items():
            assert bname in bone_by_name, bname
            bd = {}
            for chan, f in chans.items():
                keys = {}
                for i in range(frames + 1):
                    t = i / FPS
                    v = [r2(x) for x in f(t)]
                    keys[f"{t:.2f}".rstrip("0").rstrip(".") if t else "0.0"] = v
                vals = list(keys.values())
                if all(v == vals[0] for v in vals):
                    if (chan == "scale" and vals[0] == [1, 1, 1]) or (chan != "scale" and vals[0] == [0, 0, 0]):
                        continue
                    keys = {"0.0": vals[0]}
                bd[chan] = keys
            if bd:
                anim["bones"][bname] = bd
        out["animations"][name] = anim
    return out


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------


def build_geo(tex_w, tex_h):
    lo, hi = model_bounds()
    out_bones = []
    for b in bones:
        jb = {"name": b.name, "pivot": [r2(v) for v in b.pivot]}
        if b.parent:
            jb["parent"] = b.parent
        if any(b.rotation):
            jb["rotation"] = [r2(v) for v in b.rotation]
        if b.cubes:
            jb["cubes"] = [{
                "origin": [r2(v) for v in c.origin],
                "size": [r2(v) for v in c.size],
                "uv": c.uv,
            } for c in b.cubes]
        out_bones.append(jb)
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": "geometry.werewolf",
                "texture_width": tex_w,
                "texture_height": tex_h,
                "visible_bounds_width": 4,
                "visible_bounds_height": 4,
                "visible_bounds_offset": [0, 1.5, 0],
            },
            "bones": out_bones,
        }],
    }, lo, hi


def save_png(arr, path):
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGBA").save(path, optimize=True)


def main():
    tex, glow, tex_w, tex_h = build_texture()
    geo, lo, hi = build_geo(tex_w, tex_h)
    anims = build_animations()
    os.makedirs(f"{ASSETS}/geo/entity", exist_ok=True)
    os.makedirs(f"{ASSETS}/animations/entity", exist_ok=True)
    os.makedirs(f"{ASSETS}/textures/entity", exist_ok=True)
    with open(f"{ASSETS}/geo/entity/werewolf.geo.json", "w") as f:
        json.dump(geo, f, separators=(",", ":"))
    with open(f"{ASSETS}/animations/entity/werewolf.animation.json", "w") as f:
        json.dump(anims, f, separators=(",", ":"))
    save_png(tex, f"{ASSETS}/textures/entity/werewolf.png")
    save_png(glow, f"{ASSETS}/textures/entity/werewolf_glowmask.png")

    n_cubes = sum(len(b.cubes) for b in bones)
    print(f"bones={len(bones)} cubes={n_cubes} texture={tex.shape[1]}x{tex.shape[0]}px uv={tex_w}x{tex_h}")
    print(f"hip height H={H} (leg drop {_drop:.3f})")
    print(f"bounds min={np.round(lo, 2)} max={np.round(hi, 2)}  -> height {hi[1] / 16:.2f} blocks")
    pf = to_world("paw_l", [3.25, y_paw - PAW_H, 0])
    ft = to_world("finger1b_l", [6.25, H - 8.75 - FINGER_A[1] - FINGER_B[1] - 1.25, FINGER_Z[1]])
    print(f"paw bottom y={pf[1]:.2f}  longest fingertip y={ft[1]:.2f}")


if __name__ == "__main__":
    main()
