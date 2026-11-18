创建「AI 行业动态」的话题追踪设定。

先认真理解用户到底要追什么，不要只拆关键词。S1 负责先根据用户原始需求、当前对话上下文和必要的搜索/浏览，拟定一版可确认的追踪设定；除非缺少无法合理推断的关键信息，否则不要在 S1 反复打断用户。S2 会统一向用户确认设定。

请写入：

/Coze/Drive/扣子/.skills/skill_topic_tracking/sessions_v2/setup_fa5753f8/setup_contract.json

JSON 格式：

```json
{
  "topic": "AI 行业动态",
  "topic_analysis": {
    "definition": "一句话定义这个追踪到底追什么",
    "in_scope": ["明确应该收录的事件类型"],
    "out_of_scope": ["容易误收、但不应该收录的内容"],
    "authority_policy": "这个话题对来源严谨度的要求，例如爆料型/严肃新闻/监管金融医疗安全等"
  },
  "authority_requirement": "high",
  "focus_directions": ["方向1", "方向2"],
  "user_preference": "用户偏好、排除项、写作口味和关注重点",
  "frequency": "建议频率，例如 每天 09:00",
  "tracking_dir": "/Coze/Drive/扣子/热点资讯追踪/AI 行业动态"
}
```

要求：
1. `topic_analysis.definition` 要讲清楚概念边界，例如“黑天鹅”这类词必须先解释判断标准。
2. `in_scope` / `out_of_scope` 要能帮助后续 briefing 判断相关性，不要写空泛词。
3. `authority_requirement` 只能填 `high` 或 `low`：
   - `high`：信息真实性要求高，适用于政策、监管、财经、医疗、安全、企业重大事项、资讯/事实类捕捉、突发事件等；后续每个事件组至少需要 3 个不同来源域名的 support_urls。
   - `low`：信息真实性要求较低或天然难以多源验证，适用于攻略、教程、经验、玩法、如何用 AI 赚钱、路线建议等；后续每个事件组至少需要 1 个 support_url。
4. `topic_analysis.authority_policy` 要解释为什么选择 high 或 low，以及哪些来源可接受。
5. `focus_directions` 是后续搜索的方向，不是最终栏目标题，可以动态服务于搜索。
6. 如果用户没有明确偏好，`user_preference` 写空字符串即可，不要编。
7. 只有当用户明确表达“当 xxx 的时候通知我”“一有变动通知我”“平常没更新不要打扰我”“没变化不用通知”等空结果静默诉求时，才在 JSON 顶层额外写入 `"empty_silent": true`；一般用户不要写这个字段。
8. S1 只是拟定追踪设定，不要创建子会话、不要创建日程、不要开始 briefing 试运行。

完成后运行：

```bash
python '/Coze/Drive/扣子/.skills/skill_topic_tracking/scripts/guide.py' next setup_fa5753f8
```