const pptxgen = require("C:/Users/34206/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "OpenAI";
pptx.subject = "2026年广东省大学生计算机设计大赛赛题说明提炼";
pptx.title = "2026广东省大学生计算机设计大赛赛题关键信息提炼";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};

const COLORS = {
  navy: "17324D",
  blue: "2F6BFF",
  cyan: "6BCBFF",
  gold: "F5B700",
  cream: "F7F4ED",
  ink: "1E2430",
  gray: "5F6B7A",
  light: "E9EEF5",
  red: "D64545",
  green: "2A9D6F",
  white: "FFFFFF",
};

function addBg(slide, accent = COLORS.blue) {
  slide.background = { color: COLORS.cream };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 0.3,
    line: { color: COLORS.navy, transparency: 100 },
    fill: { color: COLORS.navy },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 7.2,
    w: 13.333,
    h: 0.3,
    line: { color: accent, transparency: 100 },
    fill: { color: accent },
  });
}

function addHeader(slide, title, kicker) {
  slide.addText(kicker || "", {
    x: 0.65,
    y: 0.48,
    w: 5.6,
    h: 0.28,
    fontFace: "Microsoft YaHei",
    fontSize: 11,
    bold: true,
    color: COLORS.blue,
    charSpace: 0.5,
  });
  slide.addText(title, {
    x: 0.65,
    y: 0.8,
    w: 8.8,
    h: 0.7,
    fontFace: "Microsoft YaHei",
    fontSize: 24,
    bold: true,
    color: COLORS.ink,
  });
}

function addBullets(slide, items, x, y, w, h, options = {}) {
  const runs = [];
  items.forEach((item) => {
    if (typeof item === "string") {
      runs.push({
        text: item,
        options: { bullet: { indent: 12 } },
      });
    } else {
      runs.push({
        text: item.text,
        options: { bullet: { indent: 12 }, bold: !!item.bold, color: item.color || COLORS.ink },
      });
    }
  });
  slide.addText(runs, {
    x,
    y,
    w,
    h,
    fontFace: "Microsoft YaHei",
    fontSize: options.fontSize || 16,
    color: COLORS.ink,
    breakLine: true,
    paraSpaceAfterPt: options.paraSpaceAfterPt || 10,
    valign: "top",
    margin: 0.05,
    fit: "shrink",
    ...options.extra,
  });
}

function addStatCard(slide, x, y, w, h, value, label, color) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color, transparency: 100 },
    fill: { color: COLORS.white },
    shadow: { type: "outer", color: "C9D2DE", angle: 45, blur: 1, distance: 1, opacity: 0.15 },
  });
  slide.addText(value, {
    x: x + 0.18,
    y: y + 0.18,
    w: w - 0.36,
    h: 0.45,
    fontFace: "Microsoft YaHei",
    fontSize: 23,
    bold: true,
    color,
    align: "center",
  });
  slide.addText(label, {
    x: x + 0.14,
    y: y + 0.72,
    w: w - 0.28,
    h: 0.44,
    fontFace: "Microsoft YaHei",
    fontSize: 11,
    color: COLORS.gray,
    align: "center",
    valign: "mid",
    margin: 0.03,
  });
}

function addFooter(slide, text) {
  slide.addText(text, {
    x: 0.68,
    y: 6.86,
    w: 11.9,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 9,
    color: COLORS.gray,
    align: "left",
  });
}

// Slide 1
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.navy };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5,
    line: { color: COLORS.navy, transparency: 100 },
    fill: { color: COLORS.navy },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 8.9,
    y: 0,
    w: 4.433,
    h: 7.5,
    line: { color: COLORS.blue, transparency: 100 },
    fill: { color: COLORS.blue },
    transparency: 16,
  });
  slide.addShape(pptx.ShapeType.arc, {
    x: 8.4,
    y: 4.6,
    w: 4.3,
    h: 2.2,
    line: { color: COLORS.cyan, pt: 1.2 },
    fill: { color: COLORS.cyan, transparency: 100 },
  });
  slide.addText("2026年广东省大学生计算机设计大赛", {
    x: 0.8,
    y: 1.1,
    w: 7.6,
    h: 0.45,
    fontFace: "Microsoft YaHei",
    fontSize: 16,
    bold: true,
    color: COLORS.cyan,
  });
  slide.addText("本科赛道赛题说明\n关键信息提炼", {
    x: 0.8,
    y: 1.7,
    w: 6.8,
    h: 1.5,
    fontFace: "Microsoft YaHei",
    fontSize: 26,
    bold: true,
    color: COLORS.white,
    breakLine: true,
    margin: 0,
  });
  slide.addText("一份面向答辩与项目推进的简洁版摘要", {
    x: 0.82,
    y: 3.45,
    w: 5.6,
    h: 0.34,
    fontFace: "Microsoft YaHei",
    fontSize: 14,
    color: "D9E6F2",
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.82,
    y: 4.1,
    w: 2.6,
    h: 0.56,
    rectRadius: 0.06,
    line: { color: COLORS.gold, transparency: 100 },
    fill: { color: COLORS.gold },
  });
  slide.addText("核心主线", {
    x: 0.82,
    y: 4.24,
    w: 2.6,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 14,
    bold: true,
    color: COLORS.ink,
    align: "center",
  });
  slide.addText("叙事 / 证据 / 决策 / 后续步骤", {
    x: 0.85,
    y: 4.86,
    w: 5.0,
    h: 0.24,
    fontFace: "Microsoft YaHei",
    fontSize: 15,
    color: COLORS.white,
  });
  slide.addText("信息来源：原始 PDF《2026年广东省大学生计算机设计大赛-本科赛道赛题说明》", {
    x: 0.82,
    y: 6.75,
    w: 8.6,
    h: 0.2,
    fontFace: "Microsoft YaHei",
    fontSize: 9,
    color: "C7D0DC",
  });
}

// Slide 2
{
  const slide = pptx.addSlide();
  addBg(slide, COLORS.blue);
  addHeader(slide, "核心叙事：评委要看到的不是“会聊天”，而是“能落地”", "STORY");
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.7,
    y: 1.6,
    w: 7.4,
    h: 4.8,
    rectRadius: 0.06,
    line: { color: COLORS.light, pt: 1 },
    fill: { color: COLORS.white },
  });
  addBullets(
    slide,
    [
      "赛题要求以成熟大模型为“智能大脑”，结合 RAG、工具调用、智能体工作流，做出一个可运行的产业或教育智能体原型。",
      "方向只需四选一：服装、珠宝、时尚潮玩、教育；关键不是覆盖面大，而是切入点真实、痛点清晰、价值明确。",
      "交付目标不是论文式概念验证，而是完整系统：后端服务、前端交互、知识库、工具接入、可现场演示。",
      "这意味着答辩叙事应从“场景痛点 -> 方案架构 -> 核心能力 -> 演示结果 -> 价值闭环”展开。",
    ],
    0.95,
    1.95,
    6.8,
    3.95,
    { fontSize: 17, paraSpaceAfterPt: 12 }
  );
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 8.35,
    y: 1.6,
    w: 4.25,
    h: 4.8,
    rectRadius: 0.06,
    line: { color: COLORS.blue, pt: 1.2 },
    fill: { color: "F4F8FF" },
  });
  slide.addText("一句话理解赛题", {
    x: 8.62,
    y: 1.95,
    w: 3.7,
    h: 0.35,
    fontSize: 18,
    bold: true,
    color: COLORS.navy,
    fontFace: "Microsoft YaHei",
    align: "center",
  });
  slide.addText("选一个真实场景\n做一个可运行智能体\n并用清晰证据证明它值得做", {
    x: 8.7,
    y: 2.7,
    w: 3.5,
    h: 1.6,
    fontFace: "Microsoft YaHei",
    fontSize: 20,
    bold: true,
    color: COLORS.ink,
    align: "center",
    breakLine: true,
    margin: 0.05,
    valign: "mid",
  });
  slide.addText("关键词", {
    x: 8.72,
    y: 4.85,
    w: 1.2,
    h: 0.2,
    fontSize: 11,
    bold: true,
    color: COLORS.gray,
    fontFace: "Microsoft YaHei",
  });
  slide.addText("真实痛点 / 完整架构 / RAG / 工具调用 / 稳定演示 / 价值证明", {
    x: 8.72,
    y: 5.12,
    w: 3.45,
    h: 0.9,
    fontSize: 13,
    color: COLORS.gray,
    fontFace: "Microsoft YaHei",
    align: "center",
    valign: "mid",
  });
  addFooter(slide, "依据：赛题内容、任务要求、发布要求");
}

// Slide 3
{
  const slide = pptx.addSlide();
  addBg(slide, COLORS.gold);
  addHeader(slide, "硬性要求：方案边界清晰，交付项必须一次配齐", "EVIDENCE");
  addStatCard(slide, 0.78, 1.65, 2.25, 1.35, "4选1", "方向范围\n服装 / 珠宝 / 潮玩 / 教育", COLORS.blue);
  addStatCard(slide, 3.18, 1.65, 2.25, 1.35, "必须有", "RAG 能力\n领域知识库 + 检索增强", COLORS.green);
  addStatCard(slide, 5.58, 1.65, 2.25, 1.35, "至少1种", "工具或 API 调用\n进入推理与决策流程", COLORS.red);
  addStatCard(slide, 7.98, 1.65, 2.25, 1.35, "完整 Demo", "后端服务 + 前端交互\n支持现场演示", COLORS.gold);
  addStatCard(slide, 10.38, 1.65, 2.25, 1.35, "5项提交", "概要表 / 报告 / 视频 / PPT / 代码", COLORS.navy);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.78,
    y: 3.45,
    w: 5.85,
    h: 2.55,
    rectRadius: 0.06,
    line: { color: COLORS.light, pt: 1 },
    fill: { color: COLORS.white },
  });
  slide.addText("推荐答辩里的“最低合规说明”", {
    x: 1.0,
    y: 3.78,
    w: 4.6,
    h: 0.3,
    fontFace: "Microsoft YaHei",
    fontSize: 18,
    bold: true,
    color: COLORS.ink,
  });
  addBullets(
    slide,
    [
      "为什么选择这个具体场景，而不是更泛的方向。",
      "知识库从哪里来，如何组织，RAG 如何参与回答。",
      "接了什么工具，解决了哪一步决策或执行问题。",
      "系统如何部署、如何稳定运行、如何演示闭环。",
    ],
    1.0,
    4.18,
    5.2,
    1.45,
    { fontSize: 15, paraSpaceAfterPt: 9 }
  );
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 6.92,
    y: 3.45,
    w: 5.63,
    h: 2.55,
    rectRadius: 0.06,
    line: { color: COLORS.gold, pt: 1.2 },
    fill: { color: "FFF9E8" },
  });
  slide.addText("提交清单", {
    x: 7.18,
    y: 3.78,
    w: 1.8,
    h: 0.28,
    fontFace: "Microsoft YaHei",
    fontSize: 18,
    bold: true,
    color: COLORS.navy,
  });
  addBullets(
    slide,
    [
      "作品信息概要表",
      "智能体原型项目报告",
      "3 分钟以内演示视频",
      "答辩 PPT",
      "可运行代码与清晰 README.md",
    ],
    7.15,
    4.2,
    4.8,
    1.45,
    { fontSize: 16, paraSpaceAfterPt: 8 }
  );
  addFooter(slide, "依据：2.2 作品提交要求、3.2 任务要求、3.4 发布要求");
}

// Slide 4
{
  const slide = pptx.addSlide();
  addBg(slide, COLORS.green);
  addHeader(slide, "评分证据：现场胜负主要由场景与方案决定", "EVIDENCE");
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.82,
    y: 1.75,
    w: 4.0,
    h: 4.7,
    rectRadius: 0.06,
    line: { color: COLORS.light, pt: 1 },
    fill: { color: COLORS.white },
  });
  const bars = [
    { label: "场景与方案", score: 50, color: COLORS.blue },
    { label: "技术与创新", score: 30, color: COLORS.green },
    { label: "文档与呈现", score: 20, color: COLORS.gold },
  ];
  slide.addText("评分结构", {
    x: 1.1,
    y: 2.0,
    w: 1.8,
    h: 0.26,
    fontFace: "Microsoft YaHei",
    fontSize: 18,
    bold: true,
    color: COLORS.ink,
  });
  bars.forEach((b, i) => {
    slide.addText(String(b.score), {
      x: 1.18,
      y: 2.65 + i * 1.05,
      w: 0.8,
      h: 0.42,
      fontFace: "Microsoft YaHei",
      fontSize: 26,
      bold: true,
      color: b.color,
      align: "right",
    });
    slide.addText("%", {
      x: 2.0,
      y: 2.72 + i * 1.05,
      w: 0.35,
      h: 0.26,
      fontFace: "Microsoft YaHei",
      fontSize: 12,
      color: COLORS.gray,
    });
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 2.45,
      y: 2.72 + i * 1.05,
      w: 1.8,
      h: 0.34,
      rectRadius: 0.03,
      line: { color: b.color, transparency: 100 },
      fill: { color: b.color },
    });
    slide.addText(b.label, {
      x: 1.18,
      y: 3.1 + i * 1.05,
      w: 3.0,
      h: 0.2,
      fontFace: "Microsoft YaHei",
      fontSize: 12,
      color: COLORS.gray,
      align: "left",
    });
  });
  slide.addText("结论：先把场景定义、价值主张、架构合理性讲透，再放大技术亮点。", {
    x: 1.1,
    y: 5.75,
    w: 3.2,
    h: 0.42,
    fontFace: "Microsoft YaHei",
    fontSize: 14,
    bold: true,
    color: COLORS.navy,
    margin: 0.03,
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 5.15,
    y: 1.75,
    w: 7.4,
    h: 4.7,
    rectRadius: 0.06,
    line: { color: COLORS.green, pt: 1.2 },
    fill: { color: "F2FBF7" },
  });
  slide.addText("评委真正会问的 6 个问题", {
    x: 5.45,
    y: 2.05,
    w: 4.2,
    h: 0.3,
    fontFace: "Microsoft YaHei",
    fontSize: 19,
    bold: true,
    color: COLORS.ink,
  });
  addBullets(
    slide,
    [
      "这个痛点是否真实、具体、有代表性？",
      "你们的方案为什么比普通问答机器人更有价值？",
      "架构模块是否完整，技术选型是否有理由？",
      "交互流程是否顺畅，Demo 是否稳定可信？",
      "有没有超出基础要求的创新或工程巧思？",
      "PPT、报告、视频、现场陈述是否形成同一套逻辑？",
    ],
    5.48,
    2.55,
    6.45,
    2.9,
    { fontSize: 16, paraSpaceAfterPt: 10 }
  );
  addFooter(slide, "依据：第四部分评分规则");
}

// Slide 5
{
  const slide = pptx.addSlide();
  addBg(slide, COLORS.red);
  addHeader(slide, "关键决策：团队应尽快拍板的 4 件事", "DECISIONS");
  const cards = [
    {
      x: 0.82,
      y: 1.75,
      title: "决策 1",
      head: "选哪个方向与场景",
      body: "优先选“痛点强、数据可得、Demo 易闭环”的细分场景，而不是追求大而全。",
    },
    {
      x: 3.98,
      y: 1.75,
      title: "决策 2",
      head: "RAG 的知识来源",
      body: "尽早确定行业资料、自建文档、FAQ、政策/课程资料等，避免后期知识库空心化。",
    },
    {
      x: 7.14,
      y: 1.75,
      title: "决策 3",
      head: "工具调用放在哪一步",
      body: "工具要服务于“决策或执行”，例如检索、分析、生成、查询、推荐，而非只做噱头。",
    },
    {
      x: 10.3,
      y: 1.75,
      title: "决策 4",
      head: "答辩主证据是什么",
      body: "至少准备一个可量化或可观测的结果：准确性、效率、转化、流程缩短、体验提升。",
    },
  ];
  cards.forEach((c, idx) => {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: c.x,
      y: c.y,
      w: 2.35,
      h: 4.4,
      rectRadius: 0.06,
      line: { color: idx % 2 === 0 ? COLORS.red : COLORS.blue, pt: 1 },
      fill: { color: COLORS.white },
    });
    slide.addText(c.title, {
      x: c.x + 0.18,
      y: c.y + 0.18,
      w: 0.8,
      h: 0.2,
      fontFace: "Microsoft YaHei",
      fontSize: 11,
      bold: true,
      color: COLORS.gray,
    });
    slide.addText(c.head, {
      x: c.x + 0.18,
      y: c.y + 0.52,
      w: 1.95,
      h: 0.65,
      fontFace: "Microsoft YaHei",
      fontSize: 19,
      bold: true,
      color: COLORS.ink,
      margin: 0.02,
    });
    slide.addText(c.body, {
      x: c.x + 0.18,
      y: c.y + 1.45,
      w: 1.98,
      h: 2.45,
      fontFace: "Microsoft YaHei",
      fontSize: 14,
      color: COLORS.gray,
      margin: 0.02,
      valign: "top",
      fit: "shrink",
    });
  });
  addFooter(slide, "这些决策将直接影响场景定义、架构完整性、创新亮点与最终答辩表现。");
}

// Slide 6
{
  const slide = pptx.addSlide();
  addBg(slide, COLORS.cyan);
  addHeader(slide, "后续步骤：按评分逻辑倒推项目推进节奏", "NEXT STEPS");
  slide.addShape(pptx.ShapeType.line, {
    x: 1.0,
    y: 3.85,
    w: 11.1,
    h: 0,
    line: { color: COLORS.navy, pt: 2 },
  });
  const steps = [
    {
      x: 1.0,
      date: "现在",
      title: "定题",
      body: "锁定方向、痛点、价值主张与核心用户。",
    },
    {
      x: 3.15,
      date: "第 1 周",
      title: "搭框架",
      body: "完成大模型、RAG、工具调用与前后端骨架。",
    },
    {
      x: 5.3,
      date: "第 2 周",
      title: "做闭环",
      body: "打通最小可演示流程，形成一个稳定用例。",
    },
    {
      x: 7.45,
      date: "第 3 周",
      title: "补证据",
      body: "准备测试、效果对比、截图、视频素材与报告图表。",
    },
    {
      x: 9.6,
      date: "提交前",
      title: "磨答辩",
      body: "统一 PPT、视频、报告、README 与现场 Demo 口径。",
    },
  ];
  steps.forEach((s, i) => {
    slide.addShape(pptx.ShapeType.ellipse, {
      x: s.x,
      y: 3.55,
      w: 0.36,
      h: 0.36,
      line: { color: COLORS.blue, pt: 1.5 },
      fill: { color: i === 2 ? COLORS.gold : COLORS.white },
    });
    slide.addText(s.date, {
      x: s.x - 0.18,
      y: 2.92,
      w: 0.72,
      h: 0.18,
      fontFace: "Microsoft YaHei",
      fontSize: 11,
      bold: true,
      color: COLORS.blue,
      align: "center",
    });
    slide.addText(s.title, {
      x: s.x - 0.33,
      y: 4.06,
      w: 1.0,
      h: 0.22,
      fontFace: "Microsoft YaHei",
      fontSize: 16,
      bold: true,
      color: COLORS.ink,
      align: "center",
    });
    slide.addText(s.body, {
      x: s.x - 0.48,
      y: 4.4,
      w: 1.32,
      h: 1.18,
      fontFace: "Microsoft YaHei",
      fontSize: 12,
      color: COLORS.gray,
      align: "center",
      valign: "mid",
      margin: 0.02,
      fit: "shrink",
    });
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.95,
    y: 1.35,
    w: 11.3,
    h: 1.0,
    rectRadius: 0.06,
    line: { color: COLORS.light, pt: 1 },
    fill: { color: COLORS.white },
  });
  slide.addText("时间提醒：官方说明写明初赛在 2026 年 4 月、决赛暂定 2026 年 5 月；上传截止日期以官网通知为准。另有 2026 年 3 月 31 日（暂定）产业园参观安排，填报截至 3 月 29 日。", {
    x: 1.2,
    y: 1.63,
    w: 10.7,
    h: 0.42,
    fontFace: "Microsoft YaHei",
    fontSize: 14,
    bold: true,
    color: COLORS.navy,
    align: "center",
    margin: 0.04,
  });
  addFooter(slide, "依据：第六、七部分竞赛安排与支持信息");
}

// Slide 7
{
  const slide = pptx.addSlide();
  addBg(slide, COLORS.navy);
  addHeader(slide, "一页带走：答辩 PPT 应该讲什么", "TAKEAWAY");
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.85,
    y: 1.7,
    w: 12.0,
    h: 4.85,
    rectRadius: 0.06,
    line: { color: COLORS.light, pt: 1 },
    fill: { color: COLORS.white },
  });
  const lines = [
    ["1", "痛点", "用一个真实、具体、有代表性的场景开场。"],
    ["2", "方案", "说明角色设定、知识库、工具、工作流与前后端架构。"],
    ["3", "演示", "展示一条稳定闭环，而不是泛泛展示多个零散功能。"],
    ["4", "证据", "给出效果、效率、准确性或用户价值的证据。"],
    ["5", "创新", "突出超出基础要求的亮点，例如工作流、多模态、自研工具。"],
    ["6", "落地", "说明部署方式、README、代码结构与现场可复现性。"],
  ];
  lines.forEach((line, idx) => {
    const y = 2.05 + idx * 0.72;
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 1.15,
      y,
      w: 0.52,
      h: 0.42,
      rectRadius: 0.05,
      line: { color: COLORS.blue, transparency: 100 },
      fill: { color: idx % 2 === 0 ? COLORS.blue : COLORS.gold },
    });
    slide.addText(line[0], {
      x: 1.15,
      y: y + 0.1,
      w: 0.52,
      h: 0.16,
      fontFace: "Microsoft YaHei",
      fontSize: 14,
      bold: true,
      color: idx % 2 === 0 ? COLORS.white : COLORS.ink,
      align: "center",
    });
    slide.addText(line[1], {
      x: 1.88,
      y: y + 0.04,
      w: 1.2,
      h: 0.24,
      fontFace: "Microsoft YaHei",
      fontSize: 18,
      bold: true,
      color: COLORS.ink,
    });
    slide.addText(line[2], {
      x: 3.0,
      y: y + 0.04,
      w: 8.95,
      h: 0.24,
      fontFace: "Microsoft YaHei",
      fontSize: 15,
      color: COLORS.gray,
    });
  });
  addFooter(slide, "这份演示稿适合作为赛题理解版摘要，也可直接作为团队启动会材料。");
}

const output = "2026广东省大学生计算机设计大赛赛题关键信息提炼.pptx";

(async () => {
  await pptx.writeFile({ fileName: output });
  console.log(`WROTE ${output}`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
