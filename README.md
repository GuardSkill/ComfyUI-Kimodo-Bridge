# Kimodo Motion Bridge for ComfyUI

A production-oriented ComfyUI node pack that wraps [NVIDIA Kimodo](https://github.com/nv-tlabs/kimodo) and bridges generated motion to **Mixamo FBX**, **Unity Humanoid**, and **Rive skinned 2D characters**. This repository builds on the original [ComfyUI-Kimodo](https://github.com/jtydhr88/ComfyUI-Kimodo) integration and preserves its attribution and license.

[中文说明](README_CN.md)

## Features

- **Text-to-Motion Generation** — Describe a motion in natural language, get 3D joint positions and rotations
- **Multiple Skeleton Types** — SOMA human body, SMPLX, and Unitree G1 humanoid robot
- **Kinematic Constraints** — Optional JSON constraints for pose keyframes, end-effector positions, 2D paths
- **Multi-Prompt Segments** — Chain multiple motion descriptions with smooth transitions
- **Multiple Samples** — Generate batch of motion variations from the same prompt
- **NPZ Export** — Save motion data (joint positions, rotations, foot contacts, trajectories)
- **BVH Export** — Export to BVH format for animation software (SOMA skeletons)
- **FBX Export (Mixamo)** — Retarget motion onto Mixamo-rigged FBX characters and export animated FBX
- **Unity Humanoid Bundle** — Export the same animated FBX with an automatic Unity Humanoid importer and manifest
- **Rive Runtime Bundle** — Export a 2D bone track, preview GIF, runtime driver, mapping template, and optional authored `.riv` skin
- **2D Preview** — Skeleton stick-figure visualization as ComfyUI IMAGE output
- **HuggingFace Auto-Download** — Models download automatically on first use (~17GB VRAM)

## Nodes

### Modular Workflow (Recommended)

| Node | Category | Description |
|------|----------|-------------|
| **Kimodo Load Model** | Loaders | Load a Kimodo model variant (auto-downloads from HuggingFace) |
| **Kimodo Text Encode** | Conditioning | Encode text prompt → reusable conditioning (swap seeds without re-encoding) |
| **Kimodo Sampler** | Sampling | Diffusion sampling with conditioning + optional constraints → motion |
| **Kimodo Post Process** | Post-processing | Foot-skate cleanup (optional, requires motion_correction module) |

### Preview & Export

| Node | Description |
|------|-------------|
| **Kimodo Preview (2D)** | Render 2D skeleton stick-figure for a specific frame |
| **Kimodo Preview 3D** | Interactive 3D skeleton visualization |
| **Kimodo Save NPZ** | Save motion data as NPZ files |
| **Kimodo Export BVH** | Export motion to BVH format (SOMA skeletons only) |
| **Kimodo Export FBX (Mixamo)** | Retarget and export motion to a Mixamo-rigged FBX character |
| **Kimodo Export Unity Humanoid Bundle** | Animated FBX + Unity `AssetPostprocessor` + manifest in a ZIP ready to unpack under the project root |
| **Kimodo Export Rive Runtime Bundle** | Orthographic 2D track JSON + GIF + JS driver + optional authored `.riv` character in a ZIP |
| **Kimodo Render Rive Skinned Character** | Load an authored `.riv` skin, apply Kimodo motion through a bone map, and render MP4/GIF plus a reusable asset ZIP |

## Installation

### Comfy Registry (recommended)

```bash
comfy node registry-install comfyui-kimodo-bridge
```

Restart ComfyUI after installation.

> Registry listing is activated after the repository owner creates the
> `guardskill` publisher at [registry.comfy.org](https://registry.comfy.org),
> generates a publishing API key, and runs the included publish workflow. Until
> then, use the Git installation below.

### ComfyUI Manager

Search for **Kimodo Motion Bridge**, or install the Registry ID:

```bash
comfy node install comfyui-kimodo-bridge
```

### Git

Clone this repository into your ComfyUI `custom_nodes` directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/GuardSkill/ComfyUI-Kimodo-Bridge.git
cd ComfyUI-Kimodo-Bridge
python -m pip install -r requirements.txt
python install.py
```

`install.py` installs the embedded Kimodo package and the pinned Rive Canvas
Advanced runtime. Rive video rendering additionally requires:

- Node.js 18 or newer with `npm`
- `ffmpeg` and `ffprobe` on `PATH`
- a Chromium browser (Playwright Chromium is supported)

Core generation, NPZ, BVH, Mixamo, and Unity still work when the optional Rive
video prerequisites are absent. FBX export requires the Autodesk Python SDK
listed in `requirements.txt`; Linux and Python 3.12 are the tested setup.

Restart ComfyUI. The **Kimodo** nodes will appear under the `Kimodo` category.

### Rive skin upload and production workflow

1. Put the authored, weighted `.riv` file under `ComfyUI/input/rive/`, or use
   an absolute local path.
2. Generate motion with `Load Model → Text Encode → Sampler`.
3. Optionally add `Kimodo Post Process` for foot-contact cleanup.
4. Connect the motion to **Kimodo Render Rive Skinned Character**.
5. Set `rive_skin_path`, for example `rive/MyCharacter.riv`.
6. For a new rig, set `bone_mapping_json` to a JSON file described below.
7. Queue the graph. The node returns MP4, GIF, and a reusable ZIP asset bundle.

Example mapping (target Rive bone names on the left, Kimodo joints on the right):

```json
{
  "hips": "pelvis",
  "body": ["spine1", "spine2", "spine3"],
  "Head": ["neck", "head"],
  "Arm_front": ["left_collar", "left_shoulder", "left_elbow"],
  "Arm_back": ["right_collar", "right_shoulder", "right_elbow"],
  "Leg_front": "left_hip",
  "Knee_front": "left_knee",
  "Foot_front": ["left_ankle", "left_foot"]
}
```

The `.riv` is not rewritten. The included official Rive Canvas Advanced runtime
loads its authored mesh/weights and drives writable bones with the projected
Kimodo track. Because Rive is 2D, front/back depth and self-occlusion require
authored views or state-machine art swaps for production-quality turning.

### Models

Models download automatically from HuggingFace on first use:

| Model | Skeleton | Dataset | Description |
|-------|----------|---------|-------------|
| Kimodo-SOMA-RP-v1 | SOMA (30 joints) | Rigplay (700h) | Human body, recommended |
| Kimodo-SMPLX-RP-v1 | SMPLX (22 joints) | Rigplay (700h) | SMPLX human body |
| Kimodo-G1-RP-v1 | G1 (34 joints) | Rigplay (700h) | Unitree G1 robot |
| Kimodo-SOMA-SEED-v1 | SOMA | SEED (288h) | Human body, SEED dataset |
| Kimodo-G1-SEED-v1 | G1 | SEED (288h) | G1 robot, SEED dataset |

### Manual Model Download

Kimodo's text encoder uses Meta Llama 3 8B, which is a **gated model** on HuggingFace. You need to:

1. Visit https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct and request access
2. Create a token at https://huggingface.co/settings/tokens
3. Log in and download all required models:

```bash
# Log in to HuggingFace
huggingface-cli login

# Text encoder: Llama 3 base model (gated, requires access approval)
huggingface-cli download meta-llama/Meta-Llama-3-8B-Instruct

# Text encoder: LLM2Vec adapters
huggingface-cli download McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp
huggingface-cli download McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised

# Kimodo model (pick the one you want to use)
huggingface-cli download nvidia/Kimodo-SOMA-RP-v1
```

### Motion Correction (Optional)

The `motion_correction` C++ module provides foot-skate cleanup post-processing. You have two options:

**Option A: Use prebuilt binary (Windows + Python 3.11 only)**

```bash
# Copy the prebuilt files into your Python environment
cp -r prebuilt/win_amd64_cp311 <your-python-env>/Lib/site-packages/motion_correction
```

Or add the `prebuilt/win_amd64_cp311` directory to your Python path.

**Option B: Build from source (any platform)**

Requires CMake 3.15+ and a C++17 compiler (MSVC / GCC / Clang).

```bash
cd kimodo/MotionCorrection
pip install -e .
```

Verify: `python -c "import motion_correction; print('OK')"`

> Without this module, set `post_processing = False` in the Generate node. The motion will still work but may have foot-sliding artifacts.

### FBX Export (Optional)

To use the **Kimodo Export FBX (Mixamo)** node, install the FBX SDK Python bindings:

```bash
pip install fbxsdkpy --extra-index-url https://gitlab.inria.fr/api/v4/projects/18692/packages/pypi/simple
```

You also need a Mixamo-rigged FBX character file. Download one from [Mixamo](https://www.mixamo.com/) (select "Without Skin" or "T-Pose" for best results).

## Usage

### Modular Workflow (Recommended)

```
Load Model → Text Encode → Sampler → Post Process → Export/Preview
                                ↑
                         (constraints_json)
```

1. Add **Kimodo Load Model** — select a model variant
2. Add **Kimodo Text Encode** — enter text prompt (reusable across different seeds)
3. Add **Kimodo Sampler** — set duration, seed, diffusion steps
4. Add **Kimodo Post Process** — optional foot-skate cleanup
5. Add **Kimodo Preview** / **Kimodo Export BVH** / **Kimodo Export FBX** — visualize or save

### Unity

Connect the motion to **Kimodo Export Unity Humanoid Bundle**, select a
Mixamo-rigged FBX character and unzip the result into the Unity project root.
The included editor script marks generated FBX files as Humanoid and preserves
the root-motion curves. The bone animation is byte-for-byte equivalent in
meaning to the regular Mixamo FBX output; Unity materials and scene lighting
can still make the rendered image look different.

### Rive

Connect the motion to **Kimodo Export Rive Runtime Bundle** and choose `front`
or `side`. Optionally provide an authored, weighted `.riv` character. The ZIP
contains `motion.json`, `kimodo-rive-driver.js`, `bone-map.json`, a preview GIF,
and the supplied `.riv` file. Edit the map when the artboard bone names differ.

Rive is a 2D runtime, so this output is an orthographic projection rather than
a lossless copy of the 3D render. Depth, body twist, self-occlusion, and fingers
must be authored in the Rive character/state machine. The exporter does not
rewrite the proprietary `.riv` binary; it drives its existing weighted bones
through the supported runtime API.

For a directly viewable character video, use **Kimodo Render Rive Skinned
Character**. `rive_skin_path` accepts an absolute path or a path below
`ComfyUI/input`. Supply `bone_mapping_json` for new rigs; leaving it empty uses
the included coarse mapping for Rive's Zombie example character. The renderer
uses the official Canvas Advanced Runtime locally and returns MP4, GIF, and ZIP.


### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt` | — | Text description of the motion |
| `duration` | 5.0 | Duration in seconds |
| `seed` | 42 | Random seed for reproducibility |
| `num_samples` | 1 | Number of motion variations to generate |
| `diffusion_steps` | 100 | Denoising steps (more = better quality, slower) |
| `post_processing` | true | Foot-skate cleanup (recommended, ignored for G1) |
| `constraints_json` | — | Optional path to kinematic constraints JSON |

### Multi-Prompt

Separate motion segments with periods in the prompt:

```
A person walks forward. They stop and wave hello. They turn around and sit down.
```

Each segment gets the specified duration.

### Output Format

The NPZ output contains:
- `posed_joints` — Joint positions `[T, J, 3]`
- `global_rot_mats` — Joint rotation matrices `[T, J, 3, 3]`
- `root_positions` — Root trajectory `[T, 3]`
- `foot_contacts` — Foot contact labels `[T, 4]`
- `global_root_heading` — Root heading angle `[T]`

## Credits

This plugin wraps [Kimodo](https://github.com/nv-tlabs/kimodo)g.

## License

Apache-2.0
