"""Curated competition data. Dates belong to a specific edition and source."""
from urllib.parse import quote

VERIFIED_AT = '2026-10-09'
MCM = 'https://www.mcm.edu.cn/'
INNOVATION = 'https://www.moe.gov.cn/srcsite/A08/s5672/202607/t20260731_1445670.html'
CHALLENGE = 'https://www.tiaozhanbei.net/'
CHALLENGE_NEWS = 'https://old.tiaozhanbei.net/tzb'
LANQIAO = 'https://dasai.lanqiao.cn/'
LANQIAO_NOTICE = 'https://xxxy.shou.edu.cn/_upload/article/files/eb/69/c11cdb134d8e9d738aec36b5c54f/cd230a84-3af0-419c-acd2-6459164328aa.pdf'
ELECTRONICS = 'https://www.nuedc-training.com.cn/'
ELECTRONICS_NOTICE = 'https://www.nuedc-training.com.cn/index/news/details/new_id/353'
COMPUTER = 'https://jsjds.blcu.edu.cn/'
COMPUTER_GUIDE = 'https://jsjds.blcu.edu.cn/info/1041/2734.htm'


def resource(id, title, type, url, note):
    return dict(id=id, title=title, type=type, url=url, note=note)


def video(id, title, keyword):
    return resource(id, title, 'B站搜索', 'https://search.bilibili.com/all?keyword=' + quote(keyword), '课程搜索入口；请自行核对讲师、目录与更新时间。')


def papers(keyword):
    return resource('papers', '文献检索 · ' + keyword, '文献入口', 'https://www.cnki.net/', f'建议检索：{keyword} + 具体研究领域；全文可能需要学校权限。')


def event(label, year, start, end, date, detail, source, kind='competition', precision='day', source_label='官方通知'):
    return dict(label=label, year=year, start=start, end=end, date=date, detail=detail, source=source, kind=kind, precision=precision, source_label=source_label)


def contest(id, name, short, tags, description, scope, source, resources, topics, events, pending, defaults):
    return dict(id=id, name=name, short=short, tags=tags, description=description, scope=scope, source=source,
                resources=resources, topics=topics, timeline=events, pending=pending, defaults=defaults, verified_at=VERIFIED_AT)


CONTESTS = [
    contest('cumcm', '全国大学生数学建模竞赛', '数学建模 · CUMCM', ['数学建模', '数据分析', '论文写作'],
        '用数学理解问题，用代码验证思路，用论文表达答案。',
        '先练问题拆解、模型验证与论文表达；报名资格、组队要求及校内选拔以当届规则为准。', MCM,
        [resource('official', '全国大学生数学建模竞赛官网', '官方通知', MCM, '当届规则、报名入口与赛事动态。'),
         resource('problems', '历年赛题与评奖', '官方资料', MCM + 'html_cn/section/033046c1b33c2ea9c1d6bd4c5a4020fb.html', '官方栏目入口，查看历年赛题和结果。'),
         video('bili-python', 'Python 数据分析入门', 'Python pandas 数据分析 入门'),
         video('bili-model', '数学建模：优化与评价模型', '数学建模 优化模型 评价模型'), papers('数学建模'),
         resource('ai-rule', 'AI 工具使用规定（2026年试行）', '官方规则', MCM + 'html_cn/node/fef94648f2836ab6cc81586f4c38512b.html', '核对适用版本，记录 AI 使用与人工核验。')],
        [('基础与工具', '清洗一份公开数据', '提交可运行的 Notebook，说明缺失值与异常值处理。', 'bili-python'),
         ('常用模型', '实现优化或评价模型', '提交模型假设、代码和结果图，解释适用条件。', 'bili-model'),
         ('真题训练', '复现一道历年赛题的基础方案', '提交问题拆解、基线模型、检验结果与局限。', 'problems'),
         ('论文与复盘', '整理建模报告并组内讲解', '提交摘要、假设、方法、检验及参考文献，列出三项改进。', 'papers')],
        [event('赛题发布', 2026, '2026-09-10', '2026-09-10', '9月10日 18:00', '2026 届赛题发布节点；不是下一届比赛日期。', MCM)],
        '校内报名、选拔及下一届赛程尚未收录，请联系教务处并查看当届通知。',
        {'skills': 'Python 入门，学过高等数学', 'interest': '数据分析、实际问题建模'}),

    contest('innovation', '中国国际大学生创新大赛', '创新大赛', ['创新创业', '产品验证', '项目路演'],
        '从真实需求出发，把一个想法做成可验证的项目。',
        '覆盖不同赛道；先核对赛道和团队资格，再组织调研、原型、成果证据与路演材料。', 'https://cy.ncss.cn/',
        [resource('official', '2026 年大赛通知与赛道附件', '教育部通知', INNOVATION, '报名、初复赛、总决赛及各赛道要求。'),
         resource('projects', '全国大学生创业服务网', '项目与报名入口', 'https://cy.ncss.cn/', '官方报名、资料下载与项目展示入口；部分内容需登录。'),
         video('bili-research', '需求调研与产品验证', '用户访谈 需求分析 MVP 产品验证'),
         video('bili-pitch', '创新大赛计划书与路演', '中国国际大学生创新大赛 商业计划书 路演'), papers('创新创业 用户需求')],
        [('问题与用户', '确定场景并访谈目标用户', '整理真实访谈记录、痛点和现有替代方案，提出可验证假设。', 'bili-research'),
         ('方案与原型', '制作最小可用原型', '提交一条完整使用流程和原型，记录目标用户试用反馈。', 'projects'),
         ('证据与价值', '验证价值主张与实现条件', '整理测试证据、成本估算、竞争分析；明确事实和假设。', 'papers'),
         ('材料与路演', '完成项目材料和演示', '提交项目说明、演示稿与答辩问题清单，对照所选赛道检查。', 'bili-pitch')],
        [event('报名系统开放至截止', 2026, '2026-08-10', '2026-09-25', '8月10日—9月25日 12:00', '全国报名系统窗口；校内可能提前截止。', INNOVATION, 'registration'),
         event('校赛 / 省级复赛', 2026, '2026-08', '2026-10', '8—10月', '省级复赛须于10月25日前完成，10月31日前完成推荐；校内安排单独确认。', INNOVATION, 'selection', 'month'),
         event('全国总决赛', 2026, '2026-11', '2026-11', '11月（通知安排）', '通知仅明确月份，具体日期需查看后续安排。', INNOVATION, 'final', 'month')],
        '全国报名窗口不能代替学校截止日期；不同赛道的条件请查阅通知附件。',
        {'skills': '有一个项目想法，尚未制作原型', 'interest': '产品创新、解决真实需求'}),

    contest('challenge-academic', '“挑战杯”全国大学生课外学术科技作品竞赛', '挑战杯 · 学术科技', ['学术研究', '科技发明', '调查报告'],
        '提出一个值得研究的问题，用证据和作品回答它。',
        '与创业计划竞赛分开举办；按自然科学研究、社科调查或科技发明方向准备，具体分类以当届规则为准。', CHALLENGE,
        [resource('official', '挑战杯官网与赛事规则', '官方通知', CHALLENGE, '确认主体赛届次；勿将专项赛日期套用到主体赛。'),
         resource('projects', '挑战杯人才项目库', '官方项目库', 'https://xmk.tiaozhanbei.net/', '查阅公开项目；具体奖项和完整作品需逐项核对。'),
         video('bili-method', '研究设计与调查方法', '科研选题 研究设计 调查研究 方法'),
         video('bili-defense', '学术作品答辩与展示', '挑战杯 学术科技 作品 答辩'), papers('科技创新 研究方法')],
        [('研究问题', '梳理文献并确定研究问题', '提交文献矩阵、研究空白和可检验的问题，注明来源。', 'papers'),
         ('研究设计', '设计实验或调查方案', '说明样本、变量、对照方法与数据获取方式，评估可行性。', 'bili-method'),
         ('证据与作品', '完成小规模实验或原型验证', '提交原始记录、结果分析与局限，不编造调查和实验数据。', 'projects'),
         ('报告与答辩', '完成研究报告和展示材料', '提交完整报告、创新点证据、演示及模拟答辩记录。', 'bili-defense')],
        [event('第十九届终审决赛开赛', 2025, '2025-11-02', '2025-11-02', '2025年11月2日', '往届参考：官网动态记录的开赛日，不代表2026或下一届安排。', CHALLENGE_NEWS, 'final')],
        '主体赛与创业计划赛交叉轮流举办。本站未收录下一届主体赛日期；2026 年专项赛不等同于主体赛。',
        {'skills': '读过专业文献，尚无完整研究项目', 'interest': '学术研究、技术创新或社会调查'}),

    contest('challenge-business', '“挑战杯”中国大学生创业计划竞赛', '挑战杯 · 创业计划', ['创业计划', '市场调研', '商业模式'],
        '验证需求、算清成本，让创业计划有据可依。',
        '区别于学术科技作品竞赛，围绕真实实践和创业方案准备；不同组别按当届章程确认。', CHALLENGE,
        [resource('official', '挑战杯赛事动态', '官方通知', CHALLENGE_NEWS, '查看第十五届创业计划竞赛通知和后续安排。'),
         resource('projects', '挑战杯人才项目库', '官方项目库', 'https://xmk.tiaozhanbei.net/', '用于方向研究；公开条目不等于可下载的完整获奖作品。'),
         video('bili-business', '商业模式与市场调研', '商业模式画布 创业 市场调研'),
         video('bili-pitch', '创业计划书与路演答辩', '挑战杯 创业计划 商业计划书 路演'), papers('创业 商业模式')],
        [('市场与需求', '界定客户与市场问题', '提交访谈记录、目标客户画像与竞品对照。', 'bili-business'),
         ('模式与方案', '验证产品方案和商业模式', '提交原型或服务流程、商业模式画布及验证记录。', 'projects'),
         ('运营与财务', '梳理成本、收入与风险', '制作标明假设的收支表，区分真实运营数据与预测。', 'bili-business'),
         ('计划书与路演', '完成计划书并模拟答辩', '提交计划书、路演稿、实践证据目录及修改记录。', 'bili-pitch')],
        [event('第十五届举办通知发布', 2026, '2026-05-23', '2026-05-23', '5月23日', '官方动态中的通知发布日期，不是报名开始或截止日期。', CHALLENGE_NEWS, 'notice')],
        '主体赛全国报名、作品提交和决赛具体时间尚未核实；校赛、省赛请联系校团委。',
        {'skills': '了解商业计划书，缺少市场验证', 'interest': '创业实践、商业模式设计'}),

    contest('lanqiao', '蓝桥杯全国软件和信息技术专业人才大赛', '蓝桥杯', ['程序设计', '算法训练', '软件与电子'],
        '把知识练成解题能力，在限时挑战中稳定发挥。',
        '本页模板以软件类程序设计备赛为起点；电子、人工智能等赛项需选择对应大纲。第十七届通知使用“蓝桥杯全国大学生软件和信息技术大赛”名称。', LANQIAO,
        [resource('official', '蓝桥杯大赛官网', '官方通知', LANQIAO, '选择大学生组、具体赛项和科目，核对大纲与要求。'),
         resource('schedule', '第十七届省赛时间通知', '组委会文件 · 高校转载', LANQIAO_NOTICE, '软件科目日期不同，注意区分 C/C++、Java、Python 和网络安全。'),
         video('bili-algorithm', '算法与数据结构基础', '蓝桥杯 算法 数据结构 入门'),
         video('bili-practice', '历年题目讲解与复盘', '蓝桥杯 历年真题 讲解'),
         resource('practice', '蓝桥云课学习与练习', '练习入口', 'https://www.lanqiao.cn/', '选择适合科目的练习；部分内容可能需登录或付费。')],
        [('基础诊断', '选择科目并完成基础题诊断', '整理语言基础、复杂度和数据结构薄弱点，保存解题记录。', 'bili-algorithm'),
         ('专项训练', '练习搜索、贪心或动态规划', '提交可运行解答，解释复杂度并补充边界测试。', 'practice'),
         ('真题模拟', '完成限时真题练习', '按本周时间预算选题，记录独立完成率、用时和错误类型。', 'bili-practice'),
         ('复盘巩固', '重做错题并整理解题策略', '提交错题改进对照表与考场时间分配方案。', 'practice')],
        [event('C/C++、Web、软件测试省赛', 2026, '2026-04-11', '2026-04-11', '4月11日 9:00—13:00（通知拟定）', '第十七届对应软件科目；通知拟定安排，请再核对准考证。', LANQIAO_NOTICE, source_label='组委会文件（高校转载）'),
         event('Java、Python 省赛', 2026, '2026-04-12', '2026-04-12', '4月12日 9:00—13:00（通知拟定）', '对应 Java 和 Python 科目，不代表所有赛项。', LANQIAO_NOTICE, source_label='组委会文件（高校转载）'),
         event('网络安全省赛', 2026, '2026-04-25', '2026-04-25', '4月25日（通知拟定）', '具体场次与要求以科目通知及准考证为准。', LANQIAO_NOTICE, source_label='组委会文件（高校转载）')],
        '报名、总决赛及下一届时间尚未收录；电子与人工智能赛项不套用软件科目日期。',
        {'skills': '会一门编程语言，算法基础较弱', 'interest': 'Python / C++ 程序设计、算法'}),

    contest('electronics', '全国大学生电子设计竞赛', '电子设计 · NUEDC', ['电路设计', '嵌入式', '工程测试'],
        '从电路到系统，让设计经得起实际测量。',
        '2026 年包含赛区赛及专题竞赛，各专题日程不同；本页选录模拟电子系统专题赛节点，不作为所有赛项统一赛程。', ELECTRONICS,
        [resource('official', '全国大学生电子设计竞赛培训网', '赛事与培训入口', ELECTRONICS, '官网通知转载、赛题解析与培训资源。'),
         resource('schedule', '2026 年模拟电子系统专题赛通知', '组委会通知转载', ELECTRONICS_NOTICE, '查看赛区赛、选拔与专题赛安排。'),
         video('bili-circuit', '模拟电路与仪器使用', '电子设计竞赛 模拟电路 示波器'),
         video('bili-embedded', '单片机与嵌入式系统实践', '电子设计竞赛 STM32 单片机'), papers('电子设计 控制系统')],
        [('基础与仪器', '检查电路基础和实验条件', '提交可用设备清单、基本电路测量记录及误差分析。', 'bili-circuit'),
         ('模块实现', '完成一个基础硬件模块', '提交原理图、元件清单、代码与模块测试数据。', 'bili-embedded'),
         ('系统联调', '组合模块并测试关键指标', '提交联调记录，测量稳定性、误差与边界条件。', 'schedule'),
         ('测评与报告', '模拟测评并整理设计报告', '提交系统演示、指标表、设计报告与故障复盘。', 'papers')],
        [event('赛区赛（山东官方实施安排）', 2026, '2026-07-29', '2026-08-01', '7月29日 8:00—8月1日 20:00', '赛区示例：山东省赛实施时间；其他地区请核对本赛区通知。', 'https://www.dxsjs.sdu.edu.cn/info/1003/2085.htm', 'competition', source_label='山东赛区组委会'),
         event('模拟电子专题赛报到', 2026, '2026-08-23', '2026-08-23', '8月23日 20:00 前', '入围队伍在武汉大学报到；不是所有电子设计竞赛的统一决赛日。', ELECTRONICS_NOTICE, 'final', source_label='组委会通知转载')],
        '先确认你参加的年份、赛区与专题赛；校内选拔、报名及下一届全国赛时间未收录。',
        {'skills': '学过电路基础，接触过单片机', 'interest': '嵌入式控制、模拟电路'}),

    contest('computer-design', '中国大学生计算机设计大赛', '计算机设计 · 4C', ['软件开发', '数字媒体', '作品设计'],
        '选一个具体场景，用技术与设计交付完整作品。',
        '包含软件、人工智能、物联网、数字媒体等类别。模板以作品开发为起点，主题与提交材料按所选类别核对。', COMPUTER,
        [resource('official', '计算机设计大赛官网', '官方通知', COMPUTER, '赛事类别、参赛要求、作品提交规范和历届公告。'),
         resource('guide', '2026 年国赛参赛指南', '官方指南', COMPUTER_GUIDE, '各决赛区要求与参赛流程。'),
         resource('projects', '大赛类别与往届作品线索', '官方介绍', COMPUTER + 'info/1077/1717.htm', '了解作品类别，再从官网参赛指南及作品选登查找案例。'),
         video('bili-product', '作品需求与交互原型', '计算机设计大赛 软件应用 原型 需求分析'),
         video('bili-demo', '作品演示与答辩', '中国大学生计算机设计大赛 作品 演示 答辩')],
        [('类别与选题', '确定类别和作品需求', '提交主题核对表、用户场景、需求清单与验收标准。', 'projects'),
         ('原型与开发', '实现核心作品流程', '提交可演示原型和最小功能，记录技术及素材来源。', 'bili-product'),
         ('测试与完善', '完成用户测试及作品迭代', '提交测试记录、问题修复清单与作品改进对比。', 'official'),
         ('材料与展示', '整理作品包和答辩演示', '对照类别规范提交作品、说明文档、演示视频和答辩稿。', 'bili-demo')],
        [event('省级上推作品信息公示', 2026, '2026-06', '2026-06', '6月（公告阶段）', '官方通知说明6月底公布最终入围名单；这不是省赛报名截止日期。', COMPUTER + 'info/1041/2754.htm', 'selection', 'month'),
         event('国赛决赛窗口', 2026, '2026-07', '2026-08', '7—8月（按类别分场）', '参赛指南给出决赛窗口，各类别具体日期须查分赛区通知及后续调整。', COMPUTER_GUIDE, 'final', 'month')],
        '校赛、省赛和具体类别的作品提交截止日期不同，请向学校负责人确认。',
        {'skills': '有编程或设计基础，尚未完成参赛作品', 'interest': '软件应用、交互设计或数字媒体'}),
]

# Planning references, deliberately separate from confirmed edition dates.
# School-level examples are not nationwide opening dates.
REGISTRATION_REFERENCES = {
    'cumcm': {'month': 5, 'label': '5月', 'source': 'https://www.mcm.edu.cn/upload_cn/node/745/ogFWOgXVc36c27bb3ee3adf21e06f53146b03585.pdf', 'note': '2025年参赛队报名注册自5月开始；下一届以通知为准。'},
    'innovation': {'month': 5, 'label': '5—8月', 'source': 'https://www.moe.gov.cn/srcsite/A08/s5672/202505/t20250509_1189810.html', 'note': '往届全国系统5月开启，2026年调整为8月；这是参考区间，不是当届报名窗口。'},
    'challenge-academic': {'month': 3, 'label': '3月', 'parity': 1, 'source': 'https://ccs.cuc.edu.cn/2025/0331/c5543a253767/page.htm', 'note': '校内申报月份参考中国传媒大学2025年通知；学校可更早启动。主体赛通常在奇数年举行，与创业计划赛交替。'},
    'challenge-business': {'month': 1, 'label': '1月', 'parity': 0, 'source': 'https://www.cqjzc.edu.cn/tw/info/1003/2611.htm', 'note': '参考2026年1月校内选拔预通知，具体报名由学校组织；主体赛通常在偶数年举行。'},
    'lanqiao': {'month': 10, 'label': '10月', 'source': 'https://www.hbfs.edu.cn/_upload/article/files/87/bc/7935b1c6411080d7866e42601df7/82443214-5415-4446-a526-ba90716c6b7a.pdf', 'note': '参考第十七届通知的10月报名开启安排；不同赛项截止时间不同。'},
    'electronics': {'month': 5, 'label': '5月', 'source': 'https://nuedc-sh.sjtu.edu.cn/storage/seiee/project/nuedc/article/2025/04/e2b524253af81810d7a245359aefae0b.pdf', 'note': '参考2025年全国赛进度：5月由赛区组织报名；其他年份赛区赛、专题赛可能另行安排。'},
    'computer-design': {'month': 3, 'label': '3月', 'source': 'https://jwc.hfnu.edu.cn/info/2261/62110.htm', 'note': '参考2026年高校3—4月校赛通知，按3月开始关注校内报名；不是全国统一报名日期。'},
}
for c in CONTESTS:
    c['registration_reference'] = REGISTRATION_REFERENCES[c['id']]

BY_ID = {c['id']: c for c in CONTESTS}


def public_contest(c):
    return {k: v for k, v in c.items() if k not in ('topics', 'resources')}


# Selected primary-source tutorials; checked 2026-10-11.
CURATED = {
 'cumcm': [resource('python-guide','Python 官方中文教程','精选教程','https://docs.python.org/zh-cn/3/tutorial/','先读控制流、函数和数据结构；完成数据读取小脚本。'), resource('pandas-guide','pandas 表格数据入门教程','精选教程','https://pandas.pydata.org/docs/getting_started/intro_tutorials/index.html','按读写数据、选择子集、统计和绘图顺序练习，提交可运行 Notebook。'), resource('scipy-guide','SciPy 优化方法教程','精选教程','https://docs.scipy.org/doc/scipy/tutorial/optimize.html','先理解目标函数与约束，再复现一个优化示例并检查结果。')],
 'lanqiao':[resource('python-guide','Python 官方中文教程','精选教程','https://docs.python.org/zh-cn/3/tutorial/','适用于 Python 科目；重点练函数、列表、字典，记录边界用例。')],
 'electronics':[resource('stm32-guide','STM32 官方开发资源','精选教程','https://www.st.com/content/st_com/en/stm32-mcu-developer-zone/developer-resources.html','按实际开发板选择文档和学习资源；完成一个外设实验并记录测量结果。')],
 'computer-design':[resource('python-guide','Python 官方中文教程','精选教程','https://docs.python.org/zh-cn/3/tutorial/','适用于 Python 开发方向；完成一条可运行的核心作品流程。')]
}
for c in CONTESTS:
    c['resources'].extend(CURATED.get(c['id'], []))
    c['learning_path']=[{'stage':topic[0], 'action':topic[1], 'deliverable':topic[2], 'resource_id':topic[3]} for topic in c['topics']]


# Extra topic-specific search entries and verified course platforms.
for c in CONTESTS:
    for i, tag in enumerate(c['tags']):
        c['resources'].append(video(f'extended-course-{i}', tag+' · 系统课程', tag+' 系统课程 入门 实践'))
    c['resources'].extend([
        resource('mooc-platform','中国大学 MOOC','课程平台','https://www.icourse163.org/','按本赛事方向查找高校课程；开课时间与收费以平台为准。'),
        resource('xuetang-platform','学堂在线','课程平台','https://www.xuetangx.com/','按主题查找课程，核对目录和先修要求。'),
        resource('mit-ocw','MIT 开放课程','课程平台','https://ocw.mit.edu/','开放课程资料，按专业主题选择；多数为英文。')])
    if c['id'] in ('cumcm','lanqiao','computer-design','challenge-academic'):
        c['resources'].append(resource('kaggle-learn','Kaggle 实践课程','课程平台','https://www.kaggle.com/learn','Python、数据分析等短课程与练习。'))


from .catalog_expansion import ADDITIONAL
for ident,name,short,disciplines,tags,reason,official,ref_source,month,note,subjects in ADDITIONAL:
    resources=[resource('official',short+' · 官方入口','官方通知',official,'先核对当届赛项、资格与提交规范。'), resource('reference','时间参考依据','高校或赛事通知',ref_source,note)]
    for i,subject in enumerate(subjects):
        resources.append(video(f'course-{i}',subject+' · 课程检索',tags[0]+' '+subject+' 教程'))
    resources.extend([papers(tags[0]),resource('mooc','高校课程 · 中国大学MOOC','课程平台','https://www.icourse163.org/','按本赛事基础学科检索，核对课程目录。'),resource('xuetang','高校课程 · 学堂在线','课程平台','https://www.xuetangx.com/','按主题选择课程，开课信息以平台为准。')])
    topics=[]
    for i,subject in enumerate(subjects):
        acceptance=['形成问题、规则与先修知识清单，明确一个训练目标。','提交可检查的方案、代码或作品草稿，并写出步骤与依据。','记录至少一次对照或模拟结果、误差和改进证据。','提交规范成果包与演示稿，按当届要求自查。'][i]
        topics.append((subject,'完成'+subject+'专项训练',acceptance,f'course-{i}'))
    c=contest(ident,name,short,tags,reason,'按所选赛项与当届规则备赛；资格和队伍条件需向学校确认。',official,resources,topics,[], '当届完整赛程未收录，请核对官方通知和学校选拔安排。',{'skills':'已有相关课程基础，尚未完成系统训练','interest':tags[0]})
    c.update(disciplines=disciplines,fit_reason=reason,verified_at='2026-10-11',registration_reference={'month':month,'label':str(month)+'月','source':ref_source,'note':note})
    if ident=='mechanical-design': c['registration_reference']['parity']=0
    c['learning_path']=[{'stage':t[0],'action':t[1],'deliverable':t[2],'resource_id':t[3]} for t in topics]
    CONTESTS.append(c);BY_ID[ident]=c

DISCIPLINE_INFO={
 'cumcm':(['理','工','医'],'适合运用数学与数据分析解决实际问题的学生。'),
 'innovation':(['文','理','医','工'],'适合围绕真实需求进行产品或项目验证的团队。'),
 'challenge-academic':(['文','理','医','工'],'可从社会调查、学术研究或科技发明切入。'),
 'challenge-business':(['文','理','医','工'],'适合结合专业成果开展商业分析与实践验证。'),
 'lanqiao':(['理','工'],'适合愿意训练编程、算法或电子技术的学生。'),
 'electronics':(['工','理'],'适合具备电路基础和硬件实验条件的学生。'),
 'computer-design':(['文','理','工'],'适合将软件技术、设计与内容创作结合的团队。')}
for c in CONTESTS:
    if c['id'] in DISCIPLINE_INFO:
        c['disciplines'],c['fit_reason']=DISCIPLINE_INFO[c['id']]
