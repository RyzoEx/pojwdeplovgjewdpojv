#!/usr/bin/env python3
"""Geometry lint for the werewolf model: z-fighting and broken faces.

Checks, in the rest pose and in every sampled frame of every animation:
  * z-fighting: two faces of different cubes that are (near-)coplanar, face the same way, overlap,
    and whose overlap is not buried inside some other cube.
  * floating caps: a cube with stringy (alpha-cut) side edges whose cap face is still opaque.
  * UV sanity: every face inside the texture, no two faces sharing texels.

Run: python3 tools/check_mesh.py   (exit code 1 if anything is found)
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_werewolf as g  # noqa: E402

PLANE_EPS = 0.03  # model px; closer than this flickers at normal view distances
NORMAL_COS = math.cos(math.radians(0.5))  # steeper crossings are interpenetration, not z-fighting
AREA_EPS = 0.01

FACES = {  # GeckoLib EAST is render +X, i.e. Bedrock -X
    "east": (0, -1), "west": (0, 1),
    "down": (1, -1), "up": (1, 1),
    "north": (2, -1), "south": (2, 1),
}


def bone_matrices(pose):
    """World matrix per bone, following GeckoLib's RenderUtils.translateAndRotateMatrixForBone."""
    mats = {}
    for b in g.bones:  # parents are always declared before children
        parent = mats[b.parent] if b.parent else np.eye(4)
        ch = pose.get(b.name, {})
        r = np.array(b.rotation) + np.array(ch.get("rotation", [0, 0, 0]))
        p = ch.get("position", [0, 0, 0])
        pv = np.array([-b.pivot[0], b.pivot[1], b.pivot[2]])
        T = np.eye(4)
        T[:3, 3] = [-p[0], p[1], p[2]]
        R = np.eye(4)
        R[:3, :3] = g.rot_matrix(*r)
        R[:3, 3] = pv - R[:3, :3] @ pv
        mats[b.name] = parent @ T @ R
    return mats


def cube_corners(c):
    o, s = c.origin, c.size
    x0, x1 = -(o[0] + s[0]), -o[0]  # render space
    return (x0, x1), (o[1], o[1] + s[1]), (o[2], o[2] + s[2])


def face_quad(c, face):
    (x0, x1), (y0, y1), (z0, z1) = cube_corners(c)
    if face == "east":
        pts = [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]
        n = (1, 0, 0)
    elif face == "west":
        pts = [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]
        n = (-1, 0, 0)
    elif face == "up":
        pts = [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)]
        n = (0, 1, 0)
    elif face == "down":
        pts = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]
        n = (0, -1, 0)
    elif face == "north":
        pts = [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)]
        n = (0, 0, -1)
    else:
        pts = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        n = (0, 0, 1)
    return np.array(pts, float), np.array(n, float)


def clip(subject, clipper):
    """Sutherland-Hodgman for convex 2D polygons (counter-clockwise clipper)."""
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9

    def inter(p, q, a, b):
        d1, d2 = q - p, b - a
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-12:
            return p
        t = ((a[0] - p[0]) * d2[1] - (a[1] - p[1]) * d2[0]) / den
        return p + t * d1

    out = list(subject)
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break
        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            if inside(q, a, b):
                if not inside(p, a, b):
                    out.append(inter(p, q, a, b))
                out.append(q)
            elif inside(p, a, b):
                out.append(inter(p, q, a, b))
    return out


def area2d(poly):
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        s += a[0] * b[1] - a[1] * b[0]
    return s / 2


def ccw(poly):
    return poly if area2d(poly) > 0 else poly[::-1]


def world_faces(mats):
    faces = []
    for b in g.bones:
        m = mats[b.name]
        for ci, c in enumerate(b.cubes):
            inv = np.linalg.inv(m)
            for face in FACES:
                if face not in c.uv:  # omitted face
                    continue
                pts, n = face_quad(c, face)
                wp = (m[:3, :3] @ pts.T).T + m[:3, 3]
                wn = m[:3, :3] @ n
                faces.append(dict(bone=b.name, ci=ci, cube=c, face=face, pts=wp, n=wn, d=float(wn @ wp[0]), inv=inv))
    return faces


def inside_cube(pt, f_inv, c, margin=1e-3):
    lp = f_inv[:3, :3] @ pt + f_inv[:3, 3]
    (x0, x1), (y0, y1), (z0, z1) = cube_corners(c)
    return (x0 + margin < lp[0] < x1 - margin and y0 + margin < lp[1] < y1 - margin
            and z0 + margin < lp[2] < z1 - margin)


def z_fights(mats):
    faces = world_faces(mats)
    cubes = [(f["inv"], f["cube"]) for f in faces if f["face"] == "up"]
    found = []
    for i in range(len(faces)):
        a = faces[i]
        for j in range(i + 1, len(faces)):
            b = faces[j]
            if a["cube"] is b["cube"]:
                continue
            if a["n"] @ b["n"] < NORMAL_COS or abs(a["d"] - b["d"]) > PLANE_EPS:
                continue
            n = a["n"]
            u = np.cross(n, [0, 1, 0] if abs(n[1]) < 0.9 else [1, 0, 0])
            u /= np.linalg.norm(u)
            v = np.cross(n, u)
            pa = ccw([np.array([p @ u, p @ v]) for p in a["pts"]])
            pb = ccw([np.array([p @ u, p @ v]) for p in b["pts"]])
            poly = clip(pa, pb)
            ar = area2d(poly)
            if ar < AREA_EPS:
                continue
            # sample the overlap and see whether anything covers it from the outside
            lo, hi = np.min(poly, axis=0), np.max(poly, axis=0)
            visible = 0
            total = 0
            for su in np.linspace(lo[0], hi[0], 7)[1:-1]:
                for sv in np.linspace(lo[1], hi[1], 7)[1:-1]:
                    q = np.array([su, sv])
                    if not clip([q + [-1e-4, -1e-4], q + [1e-4, -1e-4], q + [1e-4, 1e-4], q + [-1e-4, 1e-4]], poly):
                        continue
                    total += 1
                    world = su * u + sv * v + a["d"] * n + n * 0.02
                    if not any(inside_cube(world, inv, c) for inv, c in cubes):
                        visible += 1
            if total and visible:
                found.append((a, b, ar, visible / total))
    return found


def describe(f):
    return f"{f['bone']}#{f['ci']}({f['cube'].mat}).{f['face']}"


def floating_caps():
    bad = []
    for b in g.bones:
        for ci, c in enumerate(b.cubes):
            rag = "top" if c.opts.get("torn") else c.opts.get("ragged")
            caps = {"bottom": ["down"], "top": ["up"], "all": ["up", "down"]}.get(rag, [])
            for cap in caps:
                if cap in c.uv:
                    bad.append(f"{b.name}#{ci}({c.mat}).{cap}")
    return bad


def uv_check(tex_w, tex_h):
    errs = []
    rects = []
    for b in g.bones:
        for c in b.cubes:
            for face, uv in c.uv.items():
                x, y = uv["uv"]
                w, h = uv["uv_size"]
                if x < 0 or y < 0 or x + w > tex_w + 1e-6 or y + h > tex_h + 1e-6:
                    errs.append(f"{b.name}.{face} UV out of texture")
                rects.append((x, y, x + w, y + h, f"{b.name}.{face}"))
    rects.sort()
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, bb = rects[i], rects[j]
            if bb[0] >= a[2]:
                break
            if min(a[2], bb[2]) - max(a[0], bb[0]) > 1e-6 and min(a[3], bb[3]) - max(a[1], bb[1]) > 1e-6:
                errs.append(f"UV overlap {a[4]} / {bb[4]}")
    return errs


def poses():
    yield "rest", 0.0, {}
    anims = g.build_animations()["animations"]
    for name, a in anims.items():
        times = sorted({float(k) for ch in a["bones"].values() for keys in ch.values() for k in keys})
        for t in times[::2]:
            pose = {}
            for bn, ch in a["bones"].items():
                pose[bn] = {}
                for chan, keys in ch.items():
                    ks = sorted((float(k), v) for k, v in keys.items())
                    val = ks[-1][1]
                    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
                        if t0 <= t <= t1:
                            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                            val = [v0[k] + (v1[k] - v0[k]) * f for k in range(3)]
                            break
                    if len(ks) == 1:
                        val = ks[0][1]
                    pose[bn][chan] = val
            yield name.split(".")[-1], t, pose


def main():
    _, _, tex_w, tex_h = g.build_texture()
    problems = 0
    for e in uv_check(tex_w, tex_h):
        print("UV:", e)
        problems += 1
    for e in floating_caps():
        print("FLOATING CAP:", e)
        problems += 1
    seen = {}
    for name, t, pose in poses():
        for a, b, ar, vis in z_fights(bone_matrices(pose)):
            key = tuple(sorted((describe(a), describe(b))))
            if key not in seen:
                seen[key] = (name, t, ar, vis)
    for (fa, fb), (name, t, ar, vis) in sorted(seen.items()):
        print(f"Z-FIGHT: {fa} <-> {fb}  area={ar:.2f}px²  visible={vis:.0%}  first in {name}@{t:.2f}s")
        problems += 1
    print(f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
