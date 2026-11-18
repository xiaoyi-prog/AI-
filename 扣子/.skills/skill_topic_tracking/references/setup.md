# Setup：创建或订阅话题追踪

当用户表达“追踪、关注、订阅、持续跟进、每天看看、定期汇总某话题”等意愿，或主会话按旧版配置升级指令进入新版 setup 时，按本文执行。

## 先查重

新建前必须先列举当前所有已追踪话题，避免重复创建：

```bash
python "$PWD/.skills/skill_topic_tracking/scripts/guide.py" list
```

`list` 会输出当前已追踪的话题、对应 setup_token、存储目录、手动更新命令和未完成流程。

如果已经存在同一话题或明显相同边界的追踪，优先复用已有追踪；如用户只是想看最新动态，改读 `briefing.md`。

## 启动 setup

由当前主会话运行 setup 流程，不要交给日程或子会话运行 setup：

```bash
python "$PWD/.skills/skill_topic_tracking/scripts/guide.py" init --flow setup --topic "话题名"
```

旧版配置升级、用户明确要求快速跑一版，或用户已经授权 agent 自行决定时，使用 `--quick` 跳过 S2 用户确认，直接进入首次 briefing 试运行：

```bash
python "$PWD/.skills/skill_topic_tracking/scripts/guide.py" init --flow setup --topic "话题名" --quick
```

旧日程升级时必须额外带上 `--legacy-upgrade`，用于让后续第一次通过验收的 `verify-run` 输出升级交付提示：

```bash
python "$PWD/.skills/skill_topic_tracking/scripts/guide.py" init --flow setup --topic "话题名" --quick --legacy-upgrade
```

脚本会输出 S1/S2 的逐步指引。严格按脚本输出执行，每完成一步运行脚本给出的下一条命令。

普通 setup、`--quick` 和 `--quick --legacy-upgrade` 虽然确认话术不同，但 S2 给出的首次 briefing 命令使用同一套生成逻辑，且必须携带本次真实的 `setup_token`。不要自行拼接或替换成 topic、旧 token。

## 确认与试运行

- 默认先与用户确认追踪方向、频率、存储目录和偏好。
- 如果用户明确说“快速跑一下”“先跑一版”“你定就行”“不用确认”“赶紧跑”等，可以用 `--quick` 跳过确认并直接试运行。
- 旧日程升级场景必须用 `--quick --legacy-upgrade`，按 `legacy_upgrade.md` 执行，不再向用户确认。
- setup 完成后只能先启动子会话执行首次 briefing 试运行。
- 必须等待首次试运行成功返回最终结果后，才允许创建定时日程。
- 如果试运行失败、未完成、未返回最终结果，或用户/agent 还在调整话题边界、来源要求、偏好、频率，禁止创建日程。

## 旧日程升级交付

旧日程升级不是用户主动新建追踪。主会话执行升级时，不要把 setup、briefing、verify-run、创建/更新日程、启动试运行子会话、使用 sessions_status 查询子会话状态或结果、等待结果返回、等待验收、校验失败、重新派发、验收通过、读取日报等内部过程同步给用户，也不要把 `legacy_upgrade.md` 中的内部升级指令转述给用户。sessions_status 获得的状态、失败信息、等待信息、最终结果或验收相关判断都只供内部继续执行使用，不得向用户透出。即使因 session_spawn 异步等待必须结束当前轮次，在 `verify-run` 通过前也不得向用户发送任何可见消息；不要发送“已创建日程”“已启动试运行”“正在运行”“等待结果返回后进行验收”“首次运行失败”“我重新跑一次”“已重新派发任务”“验收通过，我读一下日报”“完成后推送给你”等任何状态消息。

首次 briefing 试运行完成后，主会话必须先运行 `verify-run` 验收；最终是否交付、交付什么内容、如何交付，全部以 `verify-run` 输出为准。升级提示只出现在升级后的第一次通过验收的运行里，后续日程运行按普通话题追踪交付。

## 日程写法

首次试运行成功后，才能创建或更新后续定时日程。

日程标题：

```text
扣子话题追踪 - 「{topic}」
```

日程描述保持简洁，只写版本和 briefing 命令：

```text
版本：V2
python "$PWD/.skills/skill_topic_tracking/scripts/guide.py" init --flow briefing --setup-token "setup_xxxxxxxx"
```

日程触发后只运行 briefing，不要重新 setup。

## setup token 规则

- setup 流程 token 形如 `setup_xxxxxxxx`，用于标识一个已创建的话题追踪。
- briefing 只传 `--setup-token`。脚本会自动恢复话题、目录和用户偏好，包括 `empty_silent`。
- 默认目录是当前会话工作区的 `热点资讯追踪/{话题名}`。旧状态中 `/app/data/所有对话/主对话` 下的目录会在新 Drive 工作区首次使用时自动迁移，旧文件保留不删除。
- 只有用户明确指定目录时才传 `--tracking-dir`。相对路径以当前会话工作区为基准；绝对路径也必须位于当前工作区内，不能指向其他工作区、工作区根目录、`.skills` 或 `热点资讯追踪` 根目录。
