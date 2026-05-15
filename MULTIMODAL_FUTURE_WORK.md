# 多模态算法未来工作框架

本文档用于说明 **Learning State Guardian** 从当前“姿态相关学习状态估计”逐步升级为“多模态学习状态感知系统”的路线。

## 1. 当前阶段定位

当前系统已经实现的核心逻辑是：

- 基于姿态与稳定度的 `Behavioral_Alignment`
- 基于姿态漂移与波动的 `Cognitive_Load`
- 基于被动下垂和低运动窗口的 `Fatigue_Risk`
- 基于预热与波动的 `Confidence / Uncertainty`

因此，当前版本更准确的定位是：

**任务模式感知的姿态代理学习状态模型**

而不是完整的多模态学习状态感知系统。

## 2. 为什么需要多模态

仅使用姿态数据存在天然局限：

1. 低头并不一定等于不专注；
2. 姿态稳定也不一定等于理解顺畅；
3. 疲劳、认知负荷与分心可能在姿态层面出现混淆；
4. 对真实课堂学习状态的解释力仍然有限。

因此，后续更合理的方向不是“继续堆一个更复杂的姿态分数”，而是将学习状态拆成多个可解释分支，并逐步引入更多模态。

## 3. 目标框架

建议的多模态框架由 4 个分支组成：

### 3.1 Behavioral Alignment

回答的问题是：

> 当前行为是否与当前学习任务相匹配？

当前可用信号：

- `pitch`
- `variance`
- `stability`
- `task_mode`

后续计划加入：

- `yaw`
- `roll`
- `gaze_target`
- `face_presence`

### 3.2 Cognitive Effort

回答的问题是：

> 学生现在是在费力理解，还是已经明显脱离学习目标？

当前可用信号：

- 姿态漂移代价
- 姿态波动代价
- 行为对齐损失

后续计划加入：

- `pupil_feature`
- `blink_rate`
- `fixation_dwell`
- `reread_pattern`

### 3.3 Fatigue Risk

回答的问题是：

> 当前状态更像“累了”，还是“正在努力理解”？

当前可用信号：

- `passive_drift`
- `low_motion_window`
- `sustained_slump`

后续计划加入：

- `eye_openness`
- `blink_duration_ms`
- `perclos`

### 3.4 Confidence / Uncertainty

回答的问题是：

> 当前估计是否可靠？是否应谨慎解释？

当前可用信号：

- `warmup_window`
- `variance_spike`
- `mode_transition`

后续计划加入：

- `face_confidence`
- `gaze_confidence`
- `tracking_quality`

## 4. 最终状态输出

在多模态阶段，推荐最终不再依赖单一“专注分”，而是输出更可解释的状态标签：

- `Deep Focus`
- `Productive Struggle`
- `Off-Task Risk`
- `Fatigue Risk`
- `Uncertain`

这样的输出更适合智能眼镜 HUD，也更容易向教师或评委解释。

## 5. 面向 Rokid 的接入路线

为了贴合 Rokid 眼镜场景，建议按三阶段推进：

### Phase 1：当前已完成

- 姿态代理模型
- task mode aware 逻辑
- HUD、热力图、难点事件、回补页

### Phase 2：轻量视觉扩展

目标：

- 接入 `face presence`
- 接入 `face confidence`
- 接入 `gaze proxy`
- 接入 `eye openness`

这一步的重点不是一次性做重型视觉系统，而是先把“是否看向合理目标、是否存在可解释疲劳线索”加入状态判断。

### Phase 3：更完整眼部特征

目标：

- `pupil_feature`
- `blink_rate`
- `blink_duration_ms`
- `perclos`

这一阶段才能更接近真正的多模态学习状态估计。

## 6. 当前代码中的未来工作钩子

项目中已经加入了一个轻量的多模态蓝图层：

- [multimodal_schema.py](</C:/Users/11721/Desktop/focus_project_windows/core/multimodal_schema.py>)

并提供了一个说明型 API：

- [app.py](/C:/Users/11721/Desktop/focus_project_windows/app.py:1) 中的 `/api/multimodal_blueprint`

该接口的作用不是立即参与算法推理，而是明确：

- 当前系统已启用哪些信号；
- 后续将扩展哪些模态；
- 多模态融合准备如何分层进行。

这可以作为“未来工作不是空谈”的工程化证据。

## 7. 论文中可直接使用的未来工作表述

下面这段可以直接作为论文“未来工作”部分的基础版本：

> 当前系统主要基于姿态相关特征构建任务模式感知的学习状态代理模型，能够完成行为对齐估计、认知负荷监测、疲劳风险估计以及难点事件标记。然而，仅依赖姿态信息仍存在局限，例如姿态变化无法完全区分分心、疲劳与高认知负荷等状态。后续工作将沿多模态方向展开，在保留当前姿态分支的基础上，逐步引入面部可见性、视线代理、眼睑开合、眨眼时长、PERCLOS 以及瞳孔相关特征，形成行为对齐、认知努力、疲劳风险与置信度四分支融合框架。该路线更符合 Rokid 智能眼镜的真实输入条件，也更有利于提升学习状态判断的可解释性与鲁棒性。

## 8. 答辩可口述版本

你答辩时可以这样说：

> 目前这套系统已经完成了姿态相关的学习状态估计，但我没有把它直接说成真正的多模态系统。下一步我计划以 Rokid 眼镜为载体，在现有姿态分支上继续接入 face presence、gaze proxy、eye openness，再往后接 blink 和 pupil 相关特征。也就是说，当前版本已经完成了后端原型和验证平台，未来工作是把它逐步升级成一个更严谨的多模态学习状态感知系统。
