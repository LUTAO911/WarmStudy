export {};

const getApiBase = (): string => {
  const app = getApp<IAppOption>();
  if (app && app.globalData && app.globalData.apiBase) {
    return app.globalData.apiBase;
  }
  return "https://wsapi.supermoxi.top";
};

function request(
  url: string,
  data?: any,
  method: string = "POST",
): Promise<any> {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getApiBase()}${url}`,
      data,
      method,
      header: { "Content-Type": "application/json" },
      success: (res: any) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail: (err: any) => reject(err),
    });
  });
}

function submitCheckin(userId: string, data: any): Promise<any> {
  return request("/api/student/checkin", { user_id: userId, ...data });
}

function submitPsychTest(
  userId: string,
  answers: number[],
  testType = "weekly",
): Promise<any> {
  return request("/api/student/psych/test", {
    user_id: userId,
    answers,
    test_type: testType,
  });
}

function getPsychStatus(userId: string): Promise<any> {
  return request(`/api/student/psych/status/${userId}`, undefined, "GET");
}

function getCurrentDate() {
  const now = new Date();
  return `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, "0")}-${now.getDate().toString().padStart(2, "0")}`;
}

function getUserId(role = "student") {
  return wx.getStorageSync("user_id") || "student_001";
}

const DIMENSIONS = ["emotion", "sleep", "study", "social"] as const;
type Dimension = (typeof DIMENSIONS)[number];

// ===== 真实量表题目 =====
// 来源说明：均来自国内外已公开的标准心理学量表改编

// 【量表一】MHT心理健康诊断测验改编（华东师范大学标准化量表）
const MHT_WEEKLY = [
  {
    text: "你最近是否经常担心考试没考好，影响升学或排名？",
    options: ["是的，我很担心", "偶尔会", "不太确定", "很少这样", "完全没有"],
    weights: [5, 4, 3, 2, 1],
    dimension: "学习焦虑",
  },
  {
    text: "在课堂上被老师点名回答问题时，你是否会感到紧张不安？",
    options: ["经常会，非常害怕", "有时会", "偶尔", "很少", "从不紧张"],
    weights: [5, 4, 3, 2, 1],
    dimension: "对人焦虑",
  },
  {
    text: "你是否会觉得自己在学校里很难融入同学，感到孤单？",
    options: ["经常这样", "有时会", "偶尔", "很少", "完全没有"],
    weights: [5, 4, 3, 2, 1],
    dimension: "孤独倾向",
  },
  {
    text: "做错事情时，你是否经常责怪自己，觉得都是自己的错？",
    options: ["经常会自责很久", "有时会", "偶尔", "很少", "不会"],
    weights: [5, 4, 3, 2, 1],
    dimension: "自责倾向",
  },
  {
    text: "你是否对某些声音、气味或场景特别敏感，容易感到不适？",
    options: ["很敏感，经常不舒服", "比较敏感", "一般", "偶尔", "几乎没有"],
    weights: [5, 4, 3, 2, 1],
    dimension: "过敏倾向",
  },
  {
    text: "你最近是否经常出现头痛、胃痛或不明原因的身体不适？",
    options: ["经常出现", "时有发生", "偶尔", "很少", "完全没有"],
    weights: [5, 4, 3, 2, 1],
    dimension: "身体症状",
  },
  {
    text: "你是否对高处、黑暗或某些动物等有明显的恐惧感？",
    options: ["非常恐惧", "比较害怕", "有点怕", "偶尔", "完全不怕"],
    weights: [5, 4, 3, 2, 1],
    dimension: "恐怖倾向",
  },
  {
    text: "你是否有时会突然很想发脾气，做出冲动的行为或说冲动的话？",
    options: ["经常失控", "有时会", "偶尔", "很少", "从未"],
    weights: [5, 4, 3, 2, 1],
    dimension: "冲动倾向",
  },
];

// 【量表二】感知压力量表 PSS-10 改编（Cohen & Williamson, 1988）
const PSS10 = [
  {
    text: "最近一周，你是否因为一些意外发生而感到措手不及？",
    options: ["从来没有", "很少", "有时", "经常", "非常频繁"],
    weights: [0, 1, 2, 3, 4],
    dimension: "压力",
  },
  {
    text: "最近一周，你是否感觉无法掌控生活中重要的事情？",
    options: ["从来没有", "很少", "有时", "经常", "非常频繁"],
    weights: [0, 1, 2, 3, 4],
    dimension: "压力",
  },
  {
    text: "最近一周，你是否感到紧张不安和压力重重？",
    options: ["从来没有", "很少", "有时", "经常", "非常频繁"],
    weights: [0, 1, 2, 3, 4],
    dimension: "压力",
  },
  {
    text: "最近一周，你是否经常发现自己无法应对必须做的事情？",
    options: ["从来没有", "很少", "有时", "经常", "非常频繁"],
    weights: [0, 1, 2, 3, 4],
    dimension: "压力",
  },
  {
    text: "最近一周，你是否有足够的信心去处理个人问题？",
    options: ["非常有信心", "比较有信心", "一般", "很少", "完全没有"],
    weights: [4, 3, 2, 1, 0],
    dimension: "压力",
  },
  {
    text: "最近一周，你是否感到事情都在按你的计划进行？",
    options: ["完全符合", "比较符合", "一般", "不太符合", "完全不符合"],
    weights: [4, 3, 2, 1, 0],
    dimension: "压力",
  },
  {
    text: "最近一周，你是否经常因为事情超出控制而恼火？",
    options: ["从来没有", "很少", "有时", "经常", "非常频繁"],
    weights: [0, 1, 2, 3, 4],
    dimension: "压力",
  },
  {
    text: "最近一周，你是否感觉困难堆积如山，无法克服？",
    options: ["从来没有", "很少", "有时", "经常", "非常频繁"],
    weights: [0, 1, 2, 3, 4],
    dimension: "压力",
  },
  {
    text: "最近一周，不顺心的事情是否影响了你做事的兴趣和心情？",
    options: ["从来没有", "很少", "有时", "经常", "非常频繁"],
    weights: [0, 1, 2, 3, 4],
    dimension: "压力",
  },
  {
    text: "最近一周，你是否感到自己的烦恼和困难无法向人倾诉？",
    options: ["从来没有", "很少", "有时", "经常", "非常频繁"],
    weights: [0, 1, 2, 3, 4],
    dimension: "压力",
  },
];

// 【量表三】亲子沟通量表改编（Barnes & Olson, 1982）
const COMM = [
  {
    text: "你愿意主动和家长分享学校发生的事情吗？",
    options: ["非常愿意", "比较愿意", "一般", "不太愿意", "完全不愿意"],
    weights: [4, 3, 2, 1, 0],
    dimension: "亲子沟通",
  },
  {
    text: "当你遇到烦恼时，家长能理解你的感受吗？",
    options: ["完全能", "比较能", "一般", "比较难", "完全不能"],
    weights: [4, 3, 2, 1, 0],
    dimension: "亲子沟通",
  },
  {
    text: "你和家长平时的交流多吗？",
    options: ["非常多", "比较多", "一般", "比较少", "几乎没有"],
    weights: [4, 3, 2, 1, 0],
    dimension: "亲子沟通",
  },
  {
    text: "当你的想法和家长不一致时，你们能心平气和地讨论吗？",
    options: ["完全可以", "基本可以", "一般", "比较困难", "完全不能"],
    weights: [4, 3, 2, 1, 0],
    dimension: "亲子沟通",
  },
  {
    text: "家长会尊重你的意见和决定吗？",
    options: ["完全尊重", "比较尊重", "一般", "比较少", "完全不尊重"],
    weights: [4, 3, 2, 1, 0],
    dimension: "亲子沟通",
  },
  {
    text: "你是否会因为害怕被否定而不敢和家长说心里话？",
    options: ["经常会", "有时会", "偶尔", "很少", "从不会"],
    weights: [0, 1, 2, 3, 4],
    dimension: "亲子沟通",
  },
  {
    text: "家长对你的学习要求是否让你感到压力大？",
    options: ["完全没有", "有一点", "中等", "比较大", "非常大"],
    weights: [0, 1, 2, 3, 4],
    dimension: "亲子沟通",
  },
  {
    text: "你和家长之间是否有足够的信任？",
    options: ["完全信任", "比较信任", "一般", "比较不信任", "完全不信任"],
    weights: [4, 3, 2, 1, 0],
    dimension: "亲子沟通",
  },
  {
    text: "当出现问题时，你和家长能一起商量解决方案吗？",
    options: ["完全可以", "基本可以", "一般", "比较困难", "完全不能"],
    weights: [4, 3, 2, 1, 0],
    dimension: "亲子沟通",
  },
  {
    text: "你希望和家长之间的关系是怎样的？",
    options: [
      "像朋友一样平等",
      "家长是导师",
      "维持现状就好",
      "希望少一些管教",
      "希望完全独立",
    ],
    weights: [4, 3, 2, 1, 0],
    dimension: "亲子沟通",
  },
];

const TEST_CONFIG: Record<
  string,
  { name: string; source: string; dimension: string; questions: any[] }
> = {
  weekly: {
    name: "心理健康综合评估",
    source: "MHT量表改编 · 华东师范大学标准化量表",
    dimension: "8维度综合 · 心理健康画像",
    questions: MHT_WEEKLY,
  },
  pressure: {
    name: "感知压力评估",
    source: "PSS-10量表改编 · 国际通用中文版",
    dimension: "压力感知 · 压力源分析",
    questions: PSS10,
  },
  communication: {
    name: "亲子沟通质量评估",
    source: "亲子沟通量表改编 · 标准化量表",
    dimension: "亲子关系 · 沟通质量",
    questions: COMM,
  },
};

const SCORE_TEXTS = ["很好", "比较好", "一般", "比较差", "很差"];

const SCORE_LABELS = [
  "很好 😄",
  "比较好 🙂",
  "一般 😐",
  "比较差 🙁",
  "很差 😞",
];

const LABELS: Record<Dimension, string[]> = {
  emotion: SCORE_LABELS,
  sleep: SCORE_LABELS,
  study: SCORE_LABELS,
  social: SCORE_LABELS,
};

// 雷达图辅助计算（全部用rpx单位）
const RADAR_SIZE = 220; // rpx，对应 wxss 中的 radar-chart
const RADAR_CENTER = RADAR_SIZE / 2;
const RADAR_MAX_RADIUS = RADAR_SIZE / 2 - 20; // 留出标签空间
const MAX_SCORE = 5;

function calcRadar(scores: number[]) {
  const dots: string[] = [];

  for (let i = 0; i < 6; i++) {
    const score = Math.min(scores[i] || 0, MAX_SCORE);
    const ratio = score / MAX_SCORE;
    // 角度：index 0在顶部(-90°)，每60°递增，顺时针
    const angleDeg = -90 + i * 60;
    const angleRad = (angleDeg * Math.PI) / 180;
    const r = RADAR_MAX_RADIUS * ratio;
    const x = RADAR_CENTER + r * Math.cos(angleRad);
    const y = RADAR_CENTER + r * Math.sin(angleRad);
    // 用 rpx 单位，与 wxss 中雷达图尺寸单位一致
    dots.push(`left:${x}rpx;top:${y}rpx;`);
  }

  return { dots };
}

interface CheckinData {
  emotion: string;
  sleep: string;
  study: string;
  social: string;
}

Page({
  data: {
    today: "",
    checkin: { emotion: "", sleep: "", study: "", social: "" } as CheckinData,
    checkinDone: false,
    checkinCount: 0,
    checkinPercent: 0,

    testStatus: {
      weekly: false,
      pressure: false,
      communication: false,
    } as Record<string, boolean>,

    showTest: false,
    currentTest: {
      name: "",
      source: "",
      dimension: "",
      questions: [] as any[],
    },
    currentQ: 0,
    selectedOption: null as number | null,
    answers: [] as number[],

    psychStatus: null as any,

    // 雷达图
    radarScores: [3, 2, 1, 4, 2, 3] as number[],
    dot0Style: "",
    dot1Style: "",
    dot2Style: "",
    dot3Style: "",
    dot4Style: "",
    dot5Style: "",
    riskLevel: 0,
    radarCanvasSize: 220,
  },

  onLoad() {
    if (!this.ensureProfileCompleted()) {
      return;
    }

    const now = new Date();
    const windowInfo = wx.getWindowInfo();
    const radarCanvasSize = Math.round(
      (windowInfo.windowWidth * RADAR_SIZE) / 750,
    );
    this.setData({
      today: `${now.getMonth() + 1}月${now.getDate()}日 周${["日", "一", "二", "三", "四", "五", "六"][now.getDay()]}`,
      radarCanvasSize,
    });
    this.loadCheckin();
    this.loadTestStatus();
    this.loadPsychStatus();
    this.updateRadar((this.data as any).radarScores);
  },

  onShow() {
    this.ensureProfileCompleted();
    if (!(this.data as any).showTest) {
      this.redrawRadarAfterModalClose((this.data as any).radarScores || []);
    }
  },

  redrawRadarAfterModalClose(scores: number[]) {
    const normalizedScores = Array.from({ length: 6 }).map((_, index) => {
      const raw = Number(scores[index]);
      if (isNaN(raw)) return 0;
      return Math.max(0, Math.min(MAX_SCORE, raw));
    });

    const attempts = [60, 140, 260];
    attempts.forEach((delay) => {
      setTimeout(() => {
        wx.nextTick(() => {
          this.updateRadar(normalizedScores);
        });
      }, delay);
    });
  },

  forceDrawRadarArea(scores: number[]) {
    const normalizedScores = Array.from({ length: 6 }).map((_, index) => {
      const raw = Number(scores[index]);
      if (isNaN(raw)) return 0;
      return Math.max(0, Math.min(MAX_SCORE, raw));
    });

    const attempts = [0, 80, 180];
    attempts.forEach((delay) => {
      setTimeout(() => {
        wx.nextTick(() => {
          this.drawRadarArea(normalizedScores);
        });
      }, delay);
    });
  },

  ensureProfileCompleted(): boolean {
    const childInfo = wx.getStorageSync("child_info") || {};
    const completed = !!(
      childInfo.name &&
      childInfo.gender &&
      childInfo.age &&
      childInfo.grade
    );

    if (!completed) {
      wx.showToast({ title: "请先完善个人信息", icon: "none" });
      wx.switchTab({ url: "/pages/student/chat/chat" });
      return false;
    }

    return true;
  },

  // ===== 打卡 =====
  loadCheckin() {
    const saved: any = wx.getStorageSync("checkin_today") || {};
    const now = new Date();
    const todayStr = `${now.getMonth() + 1}月${now.getDate()}日`;
    if (saved.date === todayStr) {
      const checkin = {
        emotion: this.toDisplayLabel(saved.emotion || ""),
        sleep: this.toDisplayLabel(saved.sleep || ""),
        study: this.toDisplayLabel(saved.study || ""),
        social: this.toDisplayLabel(saved.social || ""),
      };
      const doneCount = DIMENSIONS.filter((d) => checkin[d]).length;
      const allDone = doneCount === 4;
      this.setData({
        checkin,
        checkinDone: allDone,
        checkinCount: doneCount,
        checkinPercent: doneCount * 25,
      });
    }
  },

  onCheckin(e: any) {
    const type = e.currentTarget.dataset.type as Dimension;
    wx.showActionSheet({
      itemList: LABELS[type],
      success: (res: any) => {
        const val = LABELS[type][res.tapIndex];
        const newCheckin = {
          ...((this.data as any).checkin || {}),
          [type]: val,
        };
        const doneCount = DIMENSIONS.filter((d) => newCheckin[d]).length;
        const allDone = doneCount === 4;
        this.setData({
          checkin: newCheckin,
          checkinDone: allDone,
          checkinCount: doneCount,
          checkinPercent: doneCount * 25,
        });
        const now = new Date();
        const todayStr = `${now.getMonth() + 1}月${now.getDate()}日`;
        wx.setStorageSync("checkin_today", { ...newCheckin, date: todayStr });
        if (allDone) this.submitCheckinToBackend(newCheckin);
      },
    });
  },

  submitCheckinToBackend(checkin: CheckinData) {
    const userId = getUserId("student");
    const toScore = (val: string): number => {
      const pure = val.replace(/[^\u4e00-\u9fa5]/g, "");
      const idx = SCORE_TEXTS.indexOf(pure);
      return idx >= 0 ? 5 - idx : 3;
    };
    submitCheckin(userId, {
      date: getCurrentDate(),
      emotion: toScore(checkin.emotion),
      sleep: toScore(checkin.sleep),
      study: toScore(checkin.study),
      social: toScore(checkin.social),
    })
      .then(() => {
        wx.showToast({ title: "打卡成功", icon: "success" });
        this.loadPsychStatus();
      })
      .catch(() => {});
  },

  // ===== 测评 =====
  loadTestStatus() {
    const status = wx.getStorageSync("test_status") || {};
    this.setData({ testStatus: status });
  },

  saveTestStatus(type: string) {
    const status = { ...((this.data as any).testStatus || {}), [type]: true };
    wx.setStorageSync("test_status", status);
    this.setData({ testStatus: status });
  },

  onStartTest(e: any) {
    const testType = e.currentTarget.dataset.type as string;
    const config = TEST_CONFIG[testType];
    if (!config) return;
    this.setData({
      showTest: true,
      currentQ: 0,
      selectedOption: null,
      answers: [],
      currentTest: config,
    });
  },

  onCloseTest() {
    wx.showModal({
      title: "确定退出测评？",
      content: "已作答的题目将不会被保存",
      confirmText: "确定退出",
      cancelText: "继续作答",
      success: (res) => {
        if (res.confirm) {
          this.setData({ showTest: false }, () => {
            this.redrawRadarAfterModalClose(
              (this.data as any).radarScores || [],
            );
          });
        }
      },
    });
  },

  onSelectOption(e: any) {
    this.setData({ selectedOption: e.currentTarget.dataset.idx });
  },

  onNextQuestion() {
    const { currentQ, selectedOption, answers, currentTest } = (this.data ||
      {}) as any;
    if (selectedOption === null) return;
    const newAnswers = [...answers, selectedOption];
    if (currentQ < currentTest.questions.length - 1) {
      this.setData({
        currentQ: currentQ + 1,
        selectedOption: null,
        answers: newAnswers,
      });
    } else {
      this.submitTest(newAnswers, currentTest);
    }
  },

  submitTest(answers: number[], test: any) {
    const scores = test.questions.map(
      (q: any, i: number) => q.weights[answers[i]],
    );
    const avgScore =
      scores.reduce((a: number, b: number) => a + b, 0) / scores.length;
    const typeKey =
      Object.keys(TEST_CONFIG).find((k) => TEST_CONFIG[k].name === test.name) ||
      "weekly";

    this.saveTestStatus(typeKey);

    const riskCount = scores.filter((s: number) => s >= 4).length;
    const userId = getUserId("student");

    // 提交到后端后回拉最新雷达分，确保每次测评后都自动连线显示面
    const refreshRadar = () => {
      setTimeout(() => {
        this.loadPsychStatus();
      }, 120);
    };

    submitPsychTest(userId, answers, typeKey)
      .then(() => {
        refreshRadar();
      })
      .catch(() => {
        // 后端失败时也尝试用本地/缓存状态补刷新，不阻断用户流程
        refreshRadar();
      });

    const weeklyRadarScores =
      typeKey === "weekly"
        ? [
            Number(scores[0]) || 0,
            Number(scores[1]) || 0,
            Number(scores[2]) || 0,
            Number(scores[3]) || 0,
            Number(scores[4]) || 0,
            Number(scores[5]) || 0,
          ]
        : null;

    this.setData(
      {
        showTest: false,
        ...(weeklyRadarScores
          ? { radarScores: weeklyRadarScores, riskLevel: riskCount }
          : {}),
      },
      () => {
        if (weeklyRadarScores) {
          // 弹层卸载后进行多次补绘，避免二次测评后连接面偶发丢失
          this.redrawRadarAfterModalClose(weeklyRadarScores);

          // 写入本地同步缓存，供家长端和学生中心即时读取
          wx.setStorageSync(`psych_status_${userId}`, {
            userId,
            radarScores: weeklyRadarScores,
            riskLevel: riskCount,
            updatedAt: Date.now(),
          });
        }
      },
    );

    const adviceMap: Record<string, string> = {
      weekly:
        avgScore >= 4
          ? "检测到多项心理指标偏高，建议尽快与AI暖暖或心理老师沟通"
          : avgScore >= 3
            ? "部分维度得分偏高，建议多加注意情绪调节"
            : "心理状态整体良好，继续保持",
      pressure:
        avgScore >= 3
          ? "感知压力处于较高水平，建议适当放松和倾诉"
          : avgScore >= 2
            ? "压力水平适中，注意规律作息"
            : "压力管理良好",
      communication:
        avgScore >= 3
          ? "亲子沟通质量良好，继续保持"
          : avgScore >= 2
            ? "沟通尚有提升空间，建议主动和家长多交流"
            : "建议尝试更主动地和家长沟通",
    };

    wx.showModal({
      title: "测评完成 💪",
      content: `评估完成！\n得分：${avgScore.toFixed(1)} / 5\n\n${adviceMap[typeKey] || "感谢参与测评"}`,
      confirmText: "我知道了",
    } as any);
  },

  // ===== 雷达图 =====
  updateRadar(scores: number[]) {
    const normalizedScores = Array.from({ length: 6 }).map((_, index) => {
      const raw = Number(scores[index]);
      if (isNaN(raw)) return 0;
      return Math.max(0, Math.min(MAX_SCORE, raw));
    });

    const { dots } = calcRadar(normalizedScores);
    this.setData(
      {
        radarScores: normalizedScores,
        dot0Style: dots[0] || "",
        dot1Style: dots[1] || "",
        dot2Style: dots[2] || "",
        dot3Style: dots[3] || "",
        dot4Style: dots[4] || "",
        dot5Style: dots[5] || "",
      },
      () => {
        // 点位更新后强制多次补绘，确保连线面稳定显示
        this.forceDrawRadarArea(normalizedScores);
      },
    );
  },

  toDisplayLabel(value: string): string {
    if (!value) return "";
    const pure = value.replace(/[^\u4e00-\u9fa5]/g, "");
    const idx = SCORE_TEXTS.indexOf(pure);
    if (idx >= 0) return SCORE_LABELS[idx];

    const legacyTexts = ["很差", "比较差", "一般", "比较好", "很好"];
    const legacyLabels = [
      "很差 😞",
      "比较差 🙁",
      "一般 😐",
      "比较好 🙂",
      "很好 😄",
    ];
    const legacyIdx = legacyTexts.indexOf(pure);
    return legacyIdx >= 0 ? legacyLabels[legacyIdx] : value;
  },

  drawRadarArea(scores: number[]) {
    const canvasSize = ((this.data as any).radarCanvasSize || 220) as number;
    const ctx = wx.createCanvasContext("radarAreaCanvas");
    const scale = canvasSize / RADAR_SIZE;
    const center = RADAR_CENTER * scale;
    const radius = RADAR_MAX_RADIUS * scale;

    const points = scores.slice(0, 6).map((score, index) => {
      const safeScore = Math.max(0, Math.min(MAX_SCORE, score || 0));
      const ratio = safeScore / MAX_SCORE;
      const angleDeg = -90 + index * 60;
      const angleRad = (angleDeg * Math.PI) / 180;
      const r = radius * ratio;
      return {
        x: center + r * Math.cos(angleRad),
        y: center + r * Math.sin(angleRad),
      };
    });

    ctx.clearRect(0, 0, canvasSize, canvasSize);

    if (points.length >= 3) {
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y);
      }
      ctx.closePath();
      ctx.setFillStyle("rgba(22, 101, 52, 0.18)");
      ctx.fill();

      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y);
      }
      ctx.closePath();
      ctx.setStrokeStyle("#166534");
      ctx.setLineWidth(Math.max(1.5, 2 * scale));
      ctx.stroke();
    }

    ctx.draw();
  },

  loadPsychStatus() {
    const userId = getUserId("student");
    getPsychStatus(userId)
      .then((res: any) => {
        if (res && res.status === "ok") {
          this.setData({ psychStatus: res });
          if (res.radarScores) {
            this.updateRadar(res.radarScores);
          }
        }
      })
      .catch(() => {});
  },

  onViewFullReport() {
    wx.showModal({
      title: "完整报告仅家长端可用",
      content:
        "详细心理分析报告会在家长端同步展示。\n\n请家长打开「WarmStudy·家长端」小程序查看完整报告",
      confirmText: "我知道了",
    } as any);
  },
});
