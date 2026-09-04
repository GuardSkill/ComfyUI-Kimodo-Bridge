"""Unity and Rive delivery helpers for ComfyUI-Kimodo.

Unity receives the same animated FBX as the Mixamo exporter plus an
AssetPostprocessor that configures it as a Humanoid clip.  Rive receives a
portable 2D bone-track bundle: JSON animation, preview GIF, optional authored
.riv skin and a small web-runtime driver.  A .riv file is an authored binary;
we intentionally do not pretend that arbitrary binary mutation is supported.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def _safe_stem(value: str) -> str:
    value = "".join(c if c.isalnum() or c in "-_" else "_" for c in value.strip())
    return value.strip("_") or "kimodo"


def _resolve_optional_path(value: str, comfy_root: str) -> Path | None:
    if not value or not value.strip():
        return None
    p = Path(value.strip()).expanduser()
    candidates = [p] if p.is_absolute() else [Path(comfy_root) / "input" / p, Path(comfy_root) / p]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Asset not found: {value}")


UNITY_IMPORTER = r'''using UnityEditor;

// Put this file anywhere below Assets/Editor. It configures generated Kimodo
// FBX files as Humanoid clips while preserving their root-motion curves.
public sealed class KimodoHumanoidImporter : AssetPostprocessor
{
    void OnPreprocessModel()
    {
        if (!assetPath.Contains("KimodoGenerated") || !assetPath.EndsWith(".fbx")) return;
        var importer = (ModelImporter)assetImporter;
        importer.animationType = ModelImporterAnimationType.Human;
        importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
        importer.importAnimation = true;
        importer.importBlendShapes = true;
        importer.importCameras = false;
        importer.importLights = false;
        importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
    }
}
'''


UNITY_README = """# Kimodo Unity bundle

Unzip this directory under the Unity project's `Assets/` directory.  The
Editor script configures FBX files inside `KimodoGenerated` as Humanoid.

The FBX motion is the same retargeted keyframe data used by the Mixamo FBX
node. In the Animator, enable **Apply Root Motion** only when the character is
expected to travel through the scene. Kimodo SMPL-X22 has wrists but no finger
joints, so fingers remain in the character's authored/rest pose.
"""


def make_unity_bundle(fbx_path: str, output_dir: str, filename_prefix: str,
                      prompt: str, fps: float, frame_count: int) -> tuple[str, str]:
    source = Path(fbx_path)
    if not source.is_file():
        raise FileNotFoundError(f"Exported FBX not found: {fbx_path}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{_safe_stem(filename_prefix)}_{stamp}_{uuid.uuid4().hex[:8]}"
    staging = Path(output_dir) / f".{stem}_staging"
    asset_dir = staging / "Assets" / "KimodoGenerated" / stem
    editor_dir = staging / "Assets" / "Editor"
    asset_dir.mkdir(parents=True, exist_ok=True)
    editor_dir.mkdir(parents=True, exist_ok=True)
    bundled_fbx = asset_dir / f"{stem}.fbx"
    shutil.copy2(source, bundled_fbx)
    (editor_dir / "KimodoHumanoidImporter.cs").write_text(UNITY_IMPORTER, encoding="utf-8")
    (asset_dir / "README.md").write_text(UNITY_README, encoding="utf-8")
    manifest = {
        "format": "kimodo-unity-humanoid-v1",
        "source_fbx": source.name,
        "clip": {"name": stem, "fps": float(fps), "frames": int(frame_count)},
        "prompt": prompt,
        "rig": "Humanoid/CreateFromThisModel",
        "root_motion_preserved": True,
    }
    (asset_dir / "kimodo_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    zip_path = Path(output_dir) / f"{stem}_unity.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in staging.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(staging))
    shutil.rmtree(staging)
    return str(zip_path), str(source)


RIVE_DRIVER = r'''export async function driveKimodo(rive, track, mapping = {}) {
  const artboard = rive.artboard;
  const rest = new Map();
  const bones = track.bones.map((name) => {
    const target = mapping[name] || name;
    const bone = artboard.bone(target);
    if (bone) rest.set(name, { rotation: bone.rotation, x: bone.x, y: bone.y });
    return bone;
  });
  let index = 0;
  const tick = () => {
    const frame = track.frames[index++ % track.frames.length];
    bones.forEach((bone, i) => {
      if (bone) bone.rotation = rest.get(track.bones[i]).rotation + frame.localAngles[i];
    });
    const root = bones[0];
    if (root) {
      const r = rest.get(track.bones[0]);
      root.x = r.x + frame.root[0] * track.pixelsPerMeter;
      root.y = r.y - frame.root[1] * track.pixelsPerMeter;
    }
    rive.drawFrame?.();
    setTimeout(() => requestAnimationFrame(tick), 1000 / track.fps);
  };
  tick();
}
'''


RIVE_README = """# Kimodo Rive runtime bundle

This bundle contains a 2D projection of the original Kimodo motion. Load the
optional `.riv` skin with Rive's Web Advanced Runtime, load `motion.json`, and
call `driveKimodo(rive, track, mapping)` from `kimodo-rive-driver.js`.

The `.riv` character must already contain weighted bones. Bone names can be
adapted in `bone-map.json`. A front or side orthographic projection necessarily
loses out-of-plane depth, body twist and self-occlusion; use authored views or
state-machine art swaps when those are important.
"""


def _project(points: np.ndarray, view: str) -> np.ndarray:
    if view == "side":
        return np.stack((-points[..., 2], points[..., 1]), axis=-1)
    return points[..., :2].copy()


def _unwrap_angles(values: np.ndarray) -> np.ndarray:
    return np.unwrap(values, axis=0)


def build_rive_track(motion, sample_index: int, view: str,
                     pixels_per_meter: float, include_root_motion: bool) -> dict:
    output = motion.output_dict
    posed = np.asarray(output["posed_joints"])
    index = min(max(0, int(sample_index)), posed.shape[0] - 1)
    points3 = posed[index].astype(np.float64)  # T,J,3, already FK'd by Kimodo
    parents = list(motion.joint_parents or [-1] + list(range(points3.shape[1] - 1)))
    names = list(motion.joint_names or [f"joint_{i}" for i in range(points3.shape[1])])
    points2 = _project(points3, view)
    root = points2[:, 0].copy()
    relative = points2 - root[:, None, :]
    absolute_angles = np.zeros((points2.shape[0], points2.shape[1]), dtype=np.float64)
    for joint, parent in enumerate(parents):
        if parent < 0:
            continue
        delta = points2[:, joint] - points2[:, parent]
        absolute_angles[:, joint] = np.arctan2(delta[:, 1], delta[:, 0])
    local = absolute_angles.copy()
    for joint, parent in enumerate(parents):
        if parent >= 0 and parents[parent] >= 0:
            local[:, joint] -= absolute_angles[:, parent]
    local = _unwrap_angles(local)
    if not include_root_motion:
        root[:] = root[0]
    frames = []
    for frame in range(points2.shape[0]):
        frames.append({
            "frame": frame + 1,
            "root": root[frame].round(7).tolist(),
            "localAngles": local[frame].round(7).tolist(),
            "points": relative[frame].round(7).tolist(),
        })
    return {
        "format": "kimodo-rive-track-v2",
        "version": 2,
        "fps": float(motion.fps),
        "view": view,
        "pixelsPerMeter": float(pixels_per_meter),
        "bones": names,
        "parents": parents,
        "frames": frames,
        "source": {"skeleton": motion.skeleton_name, "model": motion.model_name,
                   "prompt": " ".join(motion.texts or [])},
        "limitations": ["orthographic-2d-projection", "no-generated-finger-motion"],
    }


def render_rive_preview(track: dict, output_path: str, width: int = 720,
                        height: int = 720) -> None:
    all_points = np.asarray([f["points"] for f in track["frames"]], dtype=float)
    min_xy = all_points.min(axis=(0, 1))
    max_xy = all_points.max(axis=(0, 1))
    span = np.maximum(max_xy - min_xy, 1e-3)
    scale = min((width - 100) / span[0], (height - 120) / span[1])
    parents = track["parents"]
    palette = ((57, 224, 199), (94, 160, 255), (255, 183, 77))
    images = []
    for frame in track["frames"]:
        pts = np.asarray(frame["points"], dtype=float)
        xy = np.empty_like(pts)
        xy[:, 0] = 50 + (pts[:, 0] - min_xy[0]) * scale
        xy[:, 1] = height - 55 - (pts[:, 1] - min_xy[1]) * scale
        image = Image.new("RGB", (width, height), (7, 13, 29))
        draw = ImageDraw.Draw(image)
        for joint, parent in enumerate(parents):
            if parent >= 0:
                draw.line((*xy[parent], *xy[joint]), fill=palette[joint % 3], width=8)
        for x, y in xy:
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(235, 245, 255))
        draw.text((18, 16), f"Rive projection / {track['view']} / frame {frame['frame']}",
                  fill=(220, 235, 250))
        images.append(image)
    duration = max(1, round(1000 / track["fps"]))
    images[0].save(output_path, save_all=True, append_images=images[1:],
                   duration=duration, loop=0, optimize=True)


def make_rive_bundle(motion, output_dir: str, filename_prefix: str,
                     sample_index: int, view: str, pixels_per_meter: float,
                     include_root_motion: bool, template_path: str = "",
                     comfy_root: str = "") -> tuple[str, str, str]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{_safe_stem(filename_prefix)}_{stamp}_{uuid.uuid4().hex[:8]}"
    staging = Path(output_dir) / f".{stem}_staging"
    staging.mkdir(parents=True, exist_ok=True)
    track = build_rive_track(motion, sample_index, view, pixels_per_meter, include_root_motion)
    json_path = staging / "motion.json"
    gif_path = staging / "preview.gif"
    json_path.write_text(json.dumps(track, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    render_rive_preview(track, str(gif_path))
    (staging / "kimodo-rive-driver.js").write_text(RIVE_DRIVER, encoding="utf-8")
    (staging / "README.md").write_text(RIVE_README, encoding="utf-8")
    (staging / "bone-map.json").write_text(
        json.dumps({name: name for name in track["bones"]}, indent=2), encoding="utf-8")
    template = _resolve_optional_path(template_path, comfy_root) if template_path else None
    if template:
        shutil.copy2(template, staging / template.name)
    final_json = Path(output_dir) / f"{stem}_rive.json"
    final_gif = Path(output_dir) / f"{stem}_rive.gif"
    shutil.copy2(json_path, final_json)
    shutil.copy2(gif_path, final_gif)
    zip_path = Path(output_dir) / f"{stem}_rive.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in staging.iterdir():
            zf.write(file, file.name)
    shutil.rmtree(staging)
    return str(zip_path), str(final_json), str(final_gif)


ZOMBIE_MAP = {
    "hips": "pelvis", "body": ["spine1", "spine2", "spine3"],
    "Head": ["neck", "head"],
    "Leg_front": "left_hip", "Knee_front": "left_knee",
    "Foot_front": ["left_ankle", "left_foot"],
    "Leg_back": "right_hip", "Knee_back": "right_knee",
    "Foot_back": ["right_ankle", "right_foot"],
    "Arm_front": ["left_collar", "left_shoulder", "left_elbow"],
    "Arm_back": ["right_collar", "right_shoulder", "right_elbow"],
}


def render_rive_skin_video(motion, output_dir: str, filename_prefix: str,
                           sample_index: int, view: str, pixels_per_meter: float,
                           include_root_motion: bool, template_path: str,
                           mapping_path: str, comfy_root: str,
                           width: int = 720, height: int = 720) -> tuple[str, str, str]:
    """Render an authored, weighted .riv skin through the official web runtime."""
    plugin_dir = Path(__file__).resolve().parent
    if not template_path or template_path.startswith("builtin:"):
        builtin_name = template_path.partition(":")[2] or "Zombie_Character.riv"
        template = (plugin_dir / "assets" / "rive" / builtin_name).resolve()
    else:
        template = _resolve_optional_path(template_path, comfy_root)
    if template is None or template.suffix.lower() != ".riv":
        raise ValueError("A valid authored .riv skin is required")
    if mapping_path.startswith("builtin:"):
        mapping_file = (plugin_dir / "assets" / "rive" / mapping_path.partition(":")[2]).resolve()
    else:
        mapping_file = _resolve_optional_path(mapping_path, comfy_root) if mapping_path else None
    mapping = json.loads(mapping_file.read_text(encoding="utf-8")) if mapping_file else ZOMBIE_MAP
    track = build_rive_track(motion, sample_index, view, pixels_per_meter, include_root_motion)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{_safe_stem(filename_prefix)}_{stamp}_{uuid.uuid4().hex[:8]}"
    work = Path(output_dir) / f".{stem}_render"
    frames = work / "frames"
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, work / "skin.riv")
    shutil.copy2(plugin_dir / "rive_renderer.html", work / "renderer.html")
    (work / "motion.json").write_text(json.dumps(track, separators=(",", ":")), encoding="utf-8")
    (work / "bone-map.json").write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    (work / "render-config.json").write_text(json.dumps({"width": width, "height": height}), encoding="utf-8")
    subprocess.run(["node", str(plugin_dir / "render_rive_skin.js"), str(work), str(frames),
                    str(width), str(height)], check=True, cwd=plugin_dir)
    mp4 = Path(output_dir) / f"{stem}_rive_skin.mp4"
    gif = Path(output_dir) / f"{stem}_rive_skin.gif"
    subprocess.run(["ffmpeg", "-y", "-framerate", str(float(motion.fps)),
                    "-i", str(frames / "frame_%04d.png"), "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "16", str(mp4)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["ffmpeg", "-y", "-framerate", str(float(motion.fps)),
                    "-i", str(frames / "frame_%04d.png"), "-vf", "fps=15,scale=480:-1:flags=lanczos",
                    "-loop", "0", str(gif)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    zip_path = Path(output_dir) / f"{stem}_rive_skin.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("skin.riv", "motion.json", "bone-map.json"):
            zf.write(work / name, name)
        zf.write(mp4, mp4.name)
        zf.write(gif, gif.name)
        zf.writestr("README.md", RIVE_README)
    shutil.rmtree(work)
    return str(mp4), str(gif), str(zip_path)
