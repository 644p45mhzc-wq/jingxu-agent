# 每日更新赛事（不修改网页排版）

## 每日采集与发布规则

每日采集仅生成候选，不直接发布。网站新增赛事必须已核实身份、完整简介以及当届报名起止时间，并且当前处于报名期。未知日期、只有月份、尚未开放、已截止或报名取消的赛事均不展示；原有人工整理目录保持。

`contest_profiles.json` 的 `registration` 必须包含 `edition`、`status=open`、含时区的 `starts_at` 和 `ends_at`、列于 `sources` 的正式通知 `source_url`。北京时间实时判断：包含开放时刻，不包含截止时刻。学校自行确定截止或只有全国最晚截止，不足以判断个人当前可报名。

独立 `review` 记录包含 `status=approved`、`scope=identity_introduction_registration`、`reviewer`、`checked_at`、`content_sha256`。摘要用 `backend.discovered_contests.review_digest` 计算；简介或日期修改后审核自动失效。不得编造时间或自动批准采集结果。截止或撤回审核后，列表与详情接口同步停止展示新增记录。

2026 年 11 月 1 日本地预览从 31 条候选中新增 2 项仍开放的赛道：[数字媒体竞赛国际专项赛](https://www.cmit.cn/uploadfile/2026/1012/45827.html)（11 月 6 日 23:59:59 截止）及[市场调查与分析大赛研究生、在华留学生组](https://newoaa.shisu.edu.cn/3c/b9/c6353a212153/page.htm)（11 月 15 日截止）。数字媒体主赛与市调本科组均已截止，仅上述赛道开放；市调的学校受理时间仍要向本校确认。其他候选继续留待核实。这是本地预览，尚未推送和启用云端任务。

## 这次任务做什么

定时任务配置为每天北京时间中午 12 点，用 MediaCrawler 搜索 B 站和小红书的大学生赛事通知，从标题和正文中提取赛事名称，将去重结果写入 `data/discovered_contests.json` 候选库。只有通过上面的审核与报名期检查，后端才把它加入「全部赛事」。采集失败保留已有候选；人工维护的 15 项赛事不受此过滤影响。

当前采用保守的全称识别：识别以全国、中国、国际开头且包含大学生及竞赛/大赛的完整名称。省级赛事、简称、图片内文字或不符合该格式的名称可能漏收；不承诺覆盖所有平台和所有赛事。搜索结果为发现线索，不代表赛事正在报名、由权威机构举办或适合所有学生。

候选的研究资料单独存放在 `data/contest_profiles.json`，包含比赛概况、适合人群、参赛形式、准备建议、组织信息、信息边界及来源。采集脚本不会覆盖它。新候选若没有经过核实的完整简介和当届报名信息，就留在候选库，不出现在网站；不能靠赛事名称猜测主办方、报名时间或赛制。

新记录沿用原页面的赛事卡片和详情。已核实的开放赛道显示其当届截止时间和通知；无可靠赛程的候选不展示。备赛功能不把未知日期推定为报名倒计时。平台重复、已收录赛事不重复添加；失败或空结果不删除候选线索。

## 本机运行

上游独立安装，不合并进网站依赖。已在本机测试的 MediaCrawler 版本：`68d9ef1c1da22eab75940dfd7cec259907006538`。

1. 为该版本安装其锁定的 uv 依赖，以及 Playwright 浏览器；确保 Node.js 可用。
2. 设置 `MEDIACRAWLER_HOME` 为上游目录、`MEDIACRAWLER_PYTHON` 为上游虚拟环境 Python 的绝对路径。
3. 本机扫码设置 `JINGXU_INTERACTIVE_LOGIN=1`；使用 Edge 时设置 `JINGXU_BROWSER_CHANNEL=msedge`。本人完成扫码，登录状态留在独立浏览器目录，不会同步到 GitHub。
4. 在本项目根目录运行：

```powershell
.\.venv-local\Scripts\python.exe -m research.daily
```

也可以运行 `research/run_daily.ps1`。每个平台最多等待 20 分钟，单并发，目标每关键词 5 条（上游整页返回可能超过），不抓评论和图片视频。只保存赛事名称、脱敏来源链接和发现时间，临时原始数据处理后删除，不转发上游日志。不要同时运行多个本地采集任务。

输出中 `success` 代表收到平台结果；新赛事数量为零也可能是正常结果。`empty` 代表未收到源记录，`failed` 代表采集失败，`not_configured` 代表环境缺失。只有两个平台都成功才返回退出码 0。状态保存在同一个 JSON 中，不为此改动网页。

## 云端每日运行：个人电脑可以关机

已准备 `.github/workflows/daily-resources.yml`，工作流名为 **Daily competition discovery**。Cron `0 4 * * *` 对应北京时间 12:00，GitHub 排队可能延迟。仅有本地配置文件不代表云端已启用。

由负责人一次配置：

1. 将代码合入仓库默认分支，开启 Actions。
2. MediaCrawler 版本已固定为上述 40 位提交号；升级时由维护者修改工作流并重新测试。
3. 在 Secrets 新增 `MEDIACRAWLER_BILI_COOKIE` 和 `MEDIACRAWLER_XHS_COOKIE`。按上游说明取得自己账户的登录配置，直接填到 GitHub Secrets；不要贴到聊天、源码、Variables 或 README。
4. 允许工作流写入仓库。分支保护不允许机器人提交时，需要按团队规则调整为 PR 或单独数据存储，不强推绕过保护。
5. 确认 Render 连接同一仓库和分支，并开启提交后自动部署。可选配置 Secret `RENDER_DEPLOY_HOOK`，用来触发当前服务部署。
6. Actions → Daily competition discovery → Run workflow，手动运行一次。确认数据文件已提交、Render 部署成功、「全部赛事」出现新记录后，才算部署完成。

云端链路：GitHub 采集 → 提交赛事 JSON → Render 部署 → 原页面读取赛事。电脑关闭不影响此链路；若只用本机 Windows 定时任务，电脑必须运行。

平台登录可能过期，云端 IP 也可能受到平台限制。失败会保留旧赛事，需要本人更新 Secrets 或处理平台验证；不自动绕过验证码。必要时改用自己的常开云服务器，个人电脑仍可关闭。小红书链接去掉访问令牌后可能无法直接打开，可复制赛事名称到平台搜索。

## 验证和维护

```powershell
.\.venv-local\Scripts\python.exe -m unittest discover -s tests -p test_discovered_contests.py -v
```

覆盖赛事全称提取、已收录过滤、跨平台去重、失败保留、损坏文件保护、请求时热加载和未知赛程。`DISCOVERED_CONTESTS_PATH` 可设置网站读取的自定义 JSON 路径；采集时对应使用 `--output`，默认不必配置。

前端保持仓库版本，已按要求删除撤回前的本地 UI 备份。MediaCrawler、浏览器目录和原始采集数据不提交。

上游：[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)。使用需遵守上游许可和平台规则；该版本用于非商业学习研究。GitHub、平台 Secrets 和 Render 部署仍需实际配置、验证，不能将本机运行成功等同于云端已上线。
