// Verified naming references are documented in research/competition-english-names.md.
// “working” entries are descriptive English display labels, not official translations.
(function(root){
  const byId = {
  "cumcm": {
    "name": "Contemporary Undergraduate Mathematical Contest in Modeling (CUMCM)",
    "short": "Mathematical Modeling · CUMCM",
    "reason": "For students who want to solve real-world problems using mathematics and data analysis.",
    "sourceKind": "organizer",
    "source": "https://en.mcm.edu.cn/",
    "zhName": "全国大学生数学建模竞赛",
    "zhShort": "数学建模 · CUMCM",
    "zhReason": "适合运用数学与数据分析解决实际问题的学生。"
  },
  "innovation": {
    "name": "China International College Students’ Innovation Competition (CICSIC)",
    "short": "Innovation Competition · CICSIC",
    "reason": "For teams validating a product or project against real needs.",
    "sourceKind": "organizer",
    "source": "https://en.moe.gov.cn/news/press_releases/202510/t20251031_1418688.html",
    "zhName": "中国国际大学生创新大赛",
    "zhShort": "创新大赛",
    "zhReason": "适合围绕真实需求进行产品或项目验证的团队。"
  },
  "challenge-academic": {
    "name": "Challenge Cup National College Student Extracurricular Academic and Technological Works Competition",
    "short": "Challenge Cup · Academic & Technology",
    "reason": "Explore social research, academic inquiry or technological invention.",
    "sourceKind": "organizer-republished",
    "source": "https://tiaozhanbei.net/article/15750/",
    "zhName": "“挑战杯”全国大学生课外学术科技作品竞赛",
    "zhShort": "挑战杯 · 学术科技",
    "zhReason": "可从社会调查、学术研究或科技发明切入。"
  },
  "challenge-business": {
    "name": "Challenge Cup China College Students’ Entrepreneurship Plan Competition",
    "short": "Challenge Cup · Entrepreneurship",
    "reason": "For turning academic outcomes into business analysis and practical validation.",
    "sourceKind": "working",
    "source": "https://2026.tiaozhanbei.net/d51/tzb_inno_main",
    "zhName": "“挑战杯”中国大学生创业计划竞赛",
    "zhShort": "挑战杯 · 创业计划",
    "zhReason": "适合结合专业成果开展商业分析与实践验证。"
  },
  "lanqiao": {
    "name": "Lan Qiao Cup National Software and Information Technology Professional Talent Contest",
    "short": "Lan Qiao Cup",
    "reason": "For students developing programming, algorithms or electronics skills.",
    "sourceKind": "organizer",
    "source": "https://guojisai.lanqiao.cn/",
    "zhName": "蓝桥杯全国软件和信息技术专业人才大赛",
    "zhShort": "蓝桥杯",
    "zhReason": "适合愿意训练编程、算法或电子技术的学生。"
  },
  "electronics": {
    "name": "National Undergraduate Electronics Design Contest (NUEDC)",
    "short": "Electronics Design · NUEDC",
    "reason": "For students with circuit fundamentals and access to hardware labs.",
    "sourceKind": "institution",
    "source": "https://dsj.imut.edu.cn/info/1123/3419.htm",
    "zhName": "全国大学生电子设计竞赛",
    "zhShort": "电子设计 · NUEDC",
    "zhReason": "适合具备电路基础和硬件实验条件的学生。"
  },
  "computer-design": {
    "name": "Chinese Collegiate Computing Competition (4C)",
    "short": "Computing Competition · 4C",
    "reason": "For teams combining software, design and content creation.",
    "sourceKind": "institution",
    "source": "https://cist.buct.edu.cn/2026/0317/c981a217625/page.htm",
    "zhName": "中国大学生计算机设计大赛",
    "zhShort": "计算机设计 · 4C",
    "zhReason": "适合将软件技术、设计与内容创作结合的团队。"
  },
  "fltrp": {
    "name": "FLTRP·ETIC Cup “Understanding Contemporary China” National Foreign Language Contest for College Students",
    "short": "FLTRP·ETIC Cup · Foreign Languages",
    "reason": "For students improving foreign-language expression and cross-cultural communication.",
    "sourceKind": "institution",
    "source": "https://www.wku.edu.cn/en/event/5398",
    "zhName": "“外研社·国才杯”“理解当代中国”全国大学生外语能力大赛",
    "zhShort": "外语能力 · 国才杯",
    "zhReason": "适合希望提升外语表达与跨文化沟通的学生。"
  },
  "advertising": {
    "name": "National Advertising Art Design Competition for College Students (NAADCCS)",
    "short": "Advertising Art · NAADCCS",
    "reason": "For students strong in copywriting, visual design or interactive work.",
    "sourceKind": "institution",
    "source": "https://www.gzu.edu.cn/en/2024/1225/c11084a244472/page.htm",
    "zhName": "全国大学生广告艺术大赛",
    "zhShort": "广告艺术 · 大广赛",
    "zhReason": "适合擅长文案、视觉设计或交互作品的学生。"
  },
  "mathematics": {
    "name": "National College Mathematics Competition (CMC)",
    "short": "Mathematics · CMC",
    "reason": "For students strengthening mathematical reasoning and problem-solving.",
    "sourceKind": "institution",
    "source": "https://math.szu.edu.cn/en/info/1049/3533.htm",
    "zhName": "全国大学生数学竞赛",
    "zhShort": "数学竞赛 · CMC",
    "zhReason": "适合希望强化数学推导和解题能力的学生。"
  },
  "physics-experiment": {
    "name": "National Undergraduate Physics Experiment Competition (Innovation)",
    "short": "Physics Experiments · Innovation",
    "reason": "For students with physics lab experience who want to build instruments or test methods.",
    "sourceKind": "institution-plus-track",
    "source": "https://cpoe.szu.edu.cn/en/info/1103/1595.htm",
    "zhName": "全国大学生物理实验竞赛（创新）",
    "zhShort": "物理实验 · 创新",
    "zhReason": "适合有物理实验基础、愿意制作仪器或验证方法的学生。"
  },
  "mechanical-design": {
    "name": "National College Student Mechanical Innovation Design Competition (Regular Track)",
    "short": "Mechanical Innovation Design",
    "reason": "For students with mechanical design basics and access to prototyping.",
    "sourceKind": "institution-plus-track",
    "source": "https://sgim.sztu.edu.cn/en/info/1319/1402.htm",
    "zhName": "全国大学生机械创新设计大赛（常规赛）",
    "zhShort": "机械创新设计",
    "zhReason": "适合具备机械设计基础和样机制作条件的学生。"
  },
  "biomedical-design": {
    "name": "National College Student Biomedical Engineering Innovation Design Competition",
    "short": "Biomedical Engineering Innovation",
    "reason": "For students creating engineering prototypes and validating data for healthcare needs.",
    "sourceKind": "working",
    "source": "https://www.bmedesign.cn/",
    "zhName": "全国大学生生物医学工程创新设计竞赛",
    "zhShort": "生物医学工程创新",
    "zhReason": "适合围绕健康需求开展工程原型与数据验证的学生。"
  },
  "life-science": {
    "name": "National Undergraduate Life Science Competition (Scientific Exploration)",
    "short": "Life Science · Scientific Exploration",
    "reason": "For research teams with biology knowledge, a supervisor and lab access.",
    "sourceKind": "working",
    "source": "https://www.culsc.cn/",
    "zhName": "全国大学生生命科学竞赛（科学探究类）",
    "zhShort": "生命科学 · 科学探究",
    "zhReason": "适合有生物学基础、导师和实验条件的研究团队。"
  },
  "medical-innovation": {
    "name": "National Undergraduate Medical Innovation Competition and the Belt and Road International Competition",
    "short": "Medical Innovation",
    "reason": "For students doing medical research or experimental design under a supervisor.",
    "sourceKind": "working",
    "source": "https://ism.zju.edu.cn/2026/0304/c89548a3137455/page.htm",
    "zhName": "全国大学生医学创新大赛暨“一带一路”国际竞赛",
    "zhShort": "医学创新大赛",
    "zhReason": "适合在导师指导下开展医学研究或实验设计的学生。"
  }
};
  const byChinese = Object.create(null);
  for (const entry of Object.values(byId)) {
    byChinese[entry.zhName] = entry.name;
    byChinese[entry.zhShort] = entry.short;
    byChinese[entry.zhReason] = entry.reason;
  }
  root.ContestTranslations = {
    byId,
    translate: text => byChinese[text],
    searchText: id => { const entry=byId[id]; return entry ? `${entry.name} ${entry.short} ${entry.reason}` : ''; }
  };
})(window);
