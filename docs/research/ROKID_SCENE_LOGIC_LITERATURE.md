# Rokid Scene Logic Literature Notes

This note records the recent-paper rationale behind the current shift from a face-based frame scaffold to a **first-person scene-driven learning-state proxy**.

## Why the logic changed

For an outward-facing Rokid glasses camera, the wearer does not normally appear in the frame.  
That means a "detect face -> estimate wearer posture" approach is not a good long-term fit for the real device path.

The active design now assumes:

- first-person study surfaces are visible
- the wearer face is usually not visible
- frame/video input may be easier to access than rich native eye-tracking or raw IMU

## Recent papers that informed the change

### 1. Engagement should not be reduced to one visible behavior

- Bergdahl et al., 2024  
  *Unpacking student engagement in higher education learning analytics: a systematic review*  
  Link: https://link.springer.com/article/10.1186/s41239-024-00493-y

Use in this project:

- do not describe the current model as "true concentration detection"
- keep the framing as a **learning-state proxy**
- preserve `task_mode` and avoid equating one visible posture pattern with cognition

### 2. Egocentric educational video is strongly tied to scene text and visible content

- Zhou et al., CVPR 2025  
  *EgoTextVQA: Towards Egocentric Scene-Text Aware Video Question Answering*  
  Link: https://openaccess.thecvf.com/content/CVPR2025/html/Zhou_EgoTextVQA_Towards_Egocentric_Scene-Text_Aware_Video_Question_Answering_CVPR_2025_paper.html

Use in this project:

- add `scene_text_score`
- add `scene_content_score`
- treat stable, text-rich study surfaces as a meaningful on-task cue in `reading` / `review`

### 3. Streaming egocentric understanding should use temporal continuity, not frame-by-frame spikes

- Shen et al., CVPR 2024  
  *Progress-Aware Online Action Segmentation for Egocentric Procedural Task Videos*  
  Link: https://openaccess.thecvf.com/content/CVPR2024/papers/Shen_Progress-Aware_Online_Action_Segmentation_for_Egocentric_Procedural_Task_Videos_CVPR_2024_paper.pdf

Use in this project:

- keep hysteresis and warmup logic
- use sustained windows instead of one-frame jumps
- maintain `difficulty events` as merged temporal segments instead of isolated spikes

### 4. Long-form egocentric understanding benefits from scene and relation structure

- Rodin et al., CVPR 2024  
  *Action Scene Graphs for Long-Form Understanding of Egocentric Videos*  
  Link: https://openaccess.thecvf.com/content/CVPR2024/html/Rodin_Action_Scene_Graphs_for_Long-Form_Understanding_of_Egocentric_Videos_CVPR_2024_paper.html

Use in this project:

- do not rely only on raw motion magnitude
- keep explicit scene-context features such as:
  - `scene_stability_score`
  - `scene_switch_rate`
  - content persistence across frames

### 5. Procedural error recognition needs task structure and background separation

- Lee et al., ICCV 2025  
  *Error Recognition in Procedural Videos using Generalized Task Graph*  
  Link: https://openaccess.thecvf.com/content/ICCV2025/html/Lee_Error_Recognition_in_Procedural_Videos_using_Generalized_Task_Graph_ICCV_2025_paper.html

Use in this project:

- separate:
  - `productive_struggle`
  - `off_task_risk`
  - `signal_check`
- treat scene instability and content loss as possible **background / off-task drift**
- keep `difficulty event` semantics closer to "which segment deserves replay"

## What changed in the active Rokid logic

The current frame path is no longer described as a face-driven head-pose recovery layer.

Instead it now derives:

- `scene_content_score`
- `scene_text_score`
- `scene_stability_score`
- `scene_switch_rate`
- `blur_score`
- `brightness_score`
- scene-derived `pitch / yaw / roll` proxies

These are used to adjust:

- `uncertainty_score`
- `behavioral_alignment`
- `cognitive_load`
- `state_hint`

## Safe wording for thesis / defense

Recommended wording:

> The current Rokid frame path is a first-person scene-driven learning-state proxy.  
> It uses scene motion, content density, scene-text richness, blur/brightness quality, and temporal stability cues to support adaptive learning-state estimation under realistic smart-glasses constraints.

Avoid claiming:

- precise gaze estimation
- pupil-based workload measurement
- full eye-tracking
- direct concentration ground truth
