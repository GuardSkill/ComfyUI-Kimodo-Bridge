# Kimodo Motion Bridge for ComfyUI

一个面向生产流程的 ComfyUI 节点包：封装 [NVIDIA Kimodo](https://github.com/nv-tlabs/kimodo)，并将动作输出到 Mixamo FBX、Unity Humanoid 和带真实蒙皮的 Rive 2D 角色。本项目基于原始 [ComfyUI-Kimodo](https://github.com/jtydhr88/ComfyUI-Kimodo) 扩展并保留原署名和许可证。

[English](README.md)

## 功能特性

- **文本生成动作** — 用自然语言描述动作，获得 3D 关节位置和旋转
- **多种骨骼类型** — SOMA 人体、SMPLX 和 Unitree G1 人形机器人
- **运动学约束** — 可选的 JSON 约束：姿态关键帧、末端执行器位置、2D 路径
- **多段提示** — 用句号分隔多个动作描述，自动平滑过渡
- **多样本生成** — 从同一提示生成多个动作变体
- **NPZ 导出** — 保存动作数据（关节位置、旋转、足部接触、轨迹）
- **BVH 导出** — 导出 BVH 格式用于动画软件（仅限 SOMA 骨骼）
- **FBX 导出 (Mixamo)** — 将动作重定向到 Mixamo 绑定的 FBX 角色并导出动画 FBX
- **2D 预览** — 骨架简笔画可视化，作为 ComfyUI IMAGE 输出
- **HuggingFace 自动下载** — 首次使用时自动下载模型（约需 17GB 显存）

## 节点说明

### 模块化工作流（推荐）

| 节点 | 分类 | 说明 |
|------|------|------|
| **Kimodo Load Model** | 加载器 | 加载 Kimodo 模型变体（自动从 HuggingFace 下载） |
| **Kimodo Text Encode** | 条件 | 编码文本提示 → 可复用的条件（换 seed 不用重新编码） |
| **Kimodo Sampler** | 采样 | 扩散采样 + 可选约束 → 动作数据 |
| **Kimodo Post Process** | 后处理 | 脚滑修正（可选，需要 motion_correction 模块） |

### 预览 & 导出

| 节点 | 说明 |
|------|------|
| **Kimodo Preview (2D)** | 渲染指定帧的 2D 骨架简笔画 |
| **Kimodo Preview 3D** | 交互式 3D 骨架可视化 |
| **Kimodo Save NPZ** | 保存动作数据为 NPZ 文件 |
| **Kimodo Export BVH** | 导出 BVH 格式（仅限 SOMA 骨骼） |
| **Kimodo Export FBX (Mixamo)** | 将动作重定向并导出到 Mixamo 绑定的 FBX 角色 |
| **Kimodo Export Unity Humanoid Bundle** | 输出动画 FBX、自动 Humanoid 导入脚本和元数据 ZIP |
| **Kimodo Export Rive Runtime Bundle** | 输出 2D 动作 JSON、驱动代码、GIF 和可选 `.riv` 蒙皮包 |
| **Kimodo Render Rive Skinned Character** | 输入真实 `.riv` 蒙皮和骨骼映射，输出 MP4、GIF 与完整资产 ZIP |

## 安装

推荐通过 Comfy Registry 安装：

```bash
comfy node registry-install comfyui-kimodo-bridge
```

也可以在 ComfyUI Manager 搜索 **Kimodo Motion Bridge**，或从 GitHub 安装：

将此仓库克隆到 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/GuardSkill/ComfyUI-Kimodo-Bridge.git
cd ComfyUI-Kimodo-Bridge
python -m pip install -r requirements.txt
python install.py
```

Rive 视频输出还需要 Node.js 18+、npm、ffmpeg/ffprobe 和 Chromium。
`install.py` 会安装内置 Kimodo 包及固定版本的 Rive Canvas Advanced Runtime；
若没有这些可选工具，Kimodo、NPZ、BVH、Mixamo 和 Unity 节点仍可使用。

重启 ComfyUI，**Kimodo** 节点将出现在 `Kimodo` 分类下。

### Rive 蒙皮生产流程

1. 将已经绑定并蒙皮的 `.riv` 放到 `ComfyUI/input/rive/`。
2. 使用 `Load Model → Text Encode → Sampler → Post Process（可选）` 生成动作。
3. 连接 **Kimodo Render Rive Skinned Character**。
4. `rive_skin_path` 填 `rive/角色名.riv`。
5. 新角色在 `bone_mapping_json` 中填写目标 Rive 骨骼到 Kimodo 关节的映射。
6. 执行后得到 MP4、GIF 和包含蒙皮、动作 JSON、映射的 ZIP。

映射示例：

```json
{
  "hips": "pelvis",
  "body": ["spine1", "spine2", "spine3"],
  "Head": ["neck", "head"],
  "Arm_front": ["left_collar", "left_shoulder", "left_elbow"],
  "Leg_front": "left_hip",
  "Knee_front": "left_knee",
  "Foot_front": ["left_ankle", "left_foot"]
}
```

节点通过 Rive 官方 Canvas Advanced Runtime 驱动 `.riv` 中已有的真实网格和权重，
不会伪造或改写 `.riv` 二进制。Rive 是二维系统，转身的前后遮挡仍需要角色美术制作多视图或状态机切换。

### 模型

首次使用时自动从 HuggingFace 下载：

| 模型 | 骨骼 | 数据集 | 说明 |
|------|------|--------|------|
| Kimodo-SOMA-RP-v1 | SOMA (30 关节) | Rigplay (700h) | 人体，推荐使用 |
| Kimodo-SMPLX-RP-v1 | SMPLX (22 关节) | Rigplay (700h) | SMPLX 人体 |
| Kimodo-G1-RP-v1 | G1 (34 关节) | Rigplay (700h) | Unitree G1 机器人 |
| Kimodo-SOMA-SEED-v1 | SOMA | SEED (288h) | 人体，SEED 数据集 |
| Kimodo-G1-SEED-v1 | G1 | SEED (288h) | G1 机器人，SEED 数据集 |

### 手动下载模型

Kimodo 的文本编码器使用 Meta Llama 3 8B，这是 HuggingFace 上的**受限模型**。你需要：

1. 访问 https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct 申请访问权限
2. 在 https://huggingface.co/settings/tokens 创建 token
3. 登录并下载所有需要的模型：

```bash
# 登录 HuggingFace
huggingface-cli login

# 文本编码器：Llama 3 基础模型（受限，需要审批）
huggingface-cli download meta-llama/Meta-Llama-3-8B-Instruct

# 文本编码器：LLM2Vec 适配器
huggingface-cli download McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp
huggingface-cli download McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised

# Kimodo 模型本身（选你要用的）
huggingface-cli download nvidia/Kimodo-SOMA-RP-v1
```

### Motion Correction 动作修正（可选）

`motion_correction` 是一个 C++ 模块，用于脚滑修正等后处理。两种安装方式：

**方式 A：使用预编译文件（仅限 Windows + Python 3.11）**

```bash
# 将预编译文件复制到 Python 环境
cp -r prebuilt/win_amd64_cp311 <你的Python环境>/Lib/site-packages/motion_correction
```

或者将 `prebuilt/win_amd64_cp311` 目录加入 Python 路径。

**方式 B：从源码编译（任意平台）**

需要 CMake 3.15+ 和 C++17 编译器（MSVC / GCC / Clang）。

```bash
cd kimodo/MotionCorrection
pip install -e .
```

验证：`python -c "import motion_correction; print('OK')"`

> 不安装此模块时，将 Generate 节点的 `post_processing` 设为 `False` 即可。动作仍可正常生成，但可能有脚滑现象。

### FBX 导出（可选）

使用 **Kimodo Export FBX (Mixamo)** 节点需要安装 FBX SDK Python 绑定：

```bash
pip install fbxsdkpy --extra-index-url https://gitlab.inria.fr/api/v4/projects/18692/packages/pypi/simple
```

还需要一个 Mixamo 绑定的 FBX 角色文件，可从 [Mixamo](https://www.mixamo.com/) 下载（建议选 T-Pose 导出）。

### 硬件要求

- CUDA GPU，约需 17GB 显存（文本编码器 + 扩散模型）
- 测试硬件：RTX 3090、RTX 4090、A100

## 使用方法

### 模块化工作流（推荐）

```
Load Model → Text Encode → Sampler → Post Process → Export/Preview
                                ↑
                         (constraints_json)
```

1. 添加 **Kimodo Load Model** — 选择模型变体
2. 添加 **Kimodo Text Encode** — 输入文本提示（可在不同 seed 间复用）
3. 添加 **Kimodo Sampler** — 设置时长、seed、扩散步数
4. 添加 **Kimodo Post Process** — 可选的脚滑修正
5. 添加预览/导出节点


### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `prompt` | — | 动作的文本描述 |
| `duration` | 5.0 | 时长（秒） |
| `seed` | 42 | 随机种子 |
| `num_samples` | 1 | 生成的动作变体数量 |
| `diffusion_steps` | 100 | 去噪步数（越多质量越好，速度越慢） |
| `post_processing` | true | 足部滑动修正（推荐开启，G1 机器人会忽略） |
| `constraints_json` | — | 可选的运动学约束 JSON 文件路径 |

### 多段提示

在提示中用句号分隔不同的动作段落：

```
A person walks forward. They stop and wave hello. They turn around and sit down.
```

每段使用指定的时长。

### 输出格式

NPZ 输出包含：
- `posed_joints` — 关节位置 `[T, J, 3]`
- `global_rot_mats` — 关节旋转矩阵 `[T, J, 3, 3]`
- `root_positions` — 根轨迹 `[T, 3]`
- `foot_contacts` — 足部接触标签 `[T, 4]`
- `global_root_heading` — 根朝向角度 `[T]`

## 致谢

本插件封装了 [NVIDIA Toronto AI Lab](https://github.com/nv-tlabs) 的 [Kimodo](https://github.com/nv-tlabs/kimodo) 项目。

## 许可证

Apache-2.0
