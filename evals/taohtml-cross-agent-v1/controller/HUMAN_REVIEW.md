# 黑盒集成人工验收

自动评估只判断可重复的结构、绑定、哈希、编译和 QA 事实。它不能替代审美判断、真实演讲效果、正式阅读体验或企业模板视觉保真。

对每个场景使用控制端答案键列出的四个维度，逐项填写 `PASS | FAIL` 和一条可定位说明。现场演讲场景必须实际走完演讲流；正式阅读场景必须以独立读者身份通读；企业模板场景必须把 1600×900 截图与参考图并排比较。没有完成相应体验时保持 `PENDING`，不得把自动检查结果抄成视觉结论。

人审 JSON 格式：

```json
{
  "review_version": "1.0",
  "scenario_id": "...",
  "run_id": "...",
  "status": "PASS",
  "dimensions": {
    "dimension-name": {
      "status": "PASS",
      "note": "可定位的人工判断"
    }
  },
  "reviewer": "human reviewer",
  "reviewed_at": "2026-07-19T12:00:00Z"
}
```

只有自动结果为 `PASS` 且人审为 `PASS` 的六个 smoke 行都齐全时，full 矩阵才可启用。
