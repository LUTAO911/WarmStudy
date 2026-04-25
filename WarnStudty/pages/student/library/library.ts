export {};

/* library.ts - 心理成长中心 */

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
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail: (err) => reject(err),
    });
  });
}

function isValidStudentId(value: any): boolean {
  return /^\d{9}$/.test(String(value || "").trim());
}

function ensureStudentId(): string {
  const existing =
    wx.getStorageSync("student_user_id") ||
    (wx.getStorageSync("user_role") === "student" ? wx.getStorageSync("user_id") : "");
  if (isValidStudentId(existing)) {
    wx.setStorageSync("student_user_id", existing);
    wx.setStorageSync("student_id", existing);
    return existing;
  }
  const generated = String(Math.floor(100000000 + Math.random() * 900000000));
  wx.setStorageSync("student_user_id", generated);
  wx.setStorageSync("student_id", generated);
  if (!wx.getStorageSync("user_id")) {
    wx.setStorageSync("user_id", generated);
    wx.setStorageSync("user_role", "student");
  }
  return generated;
}

interface PsychCard {
  id: string;
  title: string;
  desc: string;
  icon: string;
  bgColor: string;
  path: string;
  tag?: string;
}

interface KnowledgeItem {
  id: string;
  title: string;
  category: string;
  summary: string;
  readTime: string;
  isNew?: boolean;
}

interface ReportData {
  weekEmotion: number[];
  averageScore: number;
  trend: "up" | "down" | "stable";
  suggestions: string[];
}

const PSYCH_CARDS: PsychCard[] = [
  {
    id: "checkin",
    title: "心理打卡",
    desc: "记录今日心情",
    icon: "/images/ui-growth-checkin.png",
    bgColor: "#fff3e0",
    path: "/pages/student/chat/chat",
    tag: "每日",
  },
  {
    id: "report",
    title: "心理周报",
    desc: "查看情绪变化",
    icon: "/images/ui-growth-report.png",
    bgColor: "#e3f2fd",
    path: "/pages/student/assessment/assessment",
  },
  {
    id: "knowledge",
    title: "心理知识",
    desc: "学习心理知识",
    icon: "/images/ui-growth-knowledge.png",
    bgColor: "#f3e5f5",
    path: "/pages/student/library/knowledge/knowledge",
    tag: "推荐",
  },
  {
    id: "relax",
    title: "放松训练",
    desc: "正念冥想放松",
    icon: "/images/ui-growth-relax.png",
    bgColor: "#e8f5e9",
    path: "/pages/student/chat/chat",
  },
  {
    id: "consult",
    title: "心理咨询",
    desc: "AI陪伴倾诉",
    icon: "/images/ui-growth-consult.png",
    bgColor: "#fce4ec",
    path: "/pages/student/chat/chat",
  },
  {
    id: "test",
    title: "心理测评",
    desc: "专业量表测试",
    icon: "/images/ui-growth-test.png",
    bgColor: "#fff8e1",
    path: "/pages/student/assessment/assessment",
  },
];

const KNOWLEDGE_LIST: KnowledgeItem[] = [
  {
    id: "1",
    title: "如何应对考试焦虑？",
    category: "考试心理",
    summary: "考试前感到紧张是很常见的反应...",
    readTime: "5分钟",
    isNew: true,
  },
  {
    id: "2",
    title: "和同学闹矛盾了怎么办？",
    category: "人际关系",
    summary: "朋友之间的摩擦很正常...",
    readTime: "4分钟",
  },
  {
    id: "3",
    title: "家长总是不理解我怎么办？",
    category: "亲子沟通",
    summary: "代沟是很多家庭都会遇到的问题...",
    readTime: "6分钟",
    isNew: true,
  },
  {
    id: "4",
    title: "学习压力大怎么放松？",
    category: "压力管理",
    summary: "当学习压力让你喘不过气时...",
    readTime: "3分钟",
  },
  {
    id: "5",
    title: "如何克服拖延症？",
    category: "自我管理",
    summary: "拖延是很多学生都面临的难题...",
    readTime: "5分钟",
  },
];

Page({
  data: {
    userInfo: {
      name: "李明",
      grade: "七年级",
      class: "",
      studentId: "",
      todayMood: 0.8,
      moodLabel: "心情不错",
      moodIcon: "😊",
    } as {
      name: string;
      grade: string;
      class: string;
      studentId: string;
      todayMood: number;
      moodLabel: string;
      moodIcon: string;
    },
    psychCards: PSYCH_CARDS as PsychCard[],
    knowledgeList: KNOWLEDGE_LIST as KnowledgeItem[],
    showKnowledgeModal: false,
    selectedKnowledge: null as KnowledgeItem | null,
    showMoodPicker: false,
    todayChecked: false,
    todayMoodValue: 3,
    weekData: [75, 80, 65, 85, 70, 90, 78] as number[],
    reportData: {
      averageScore: 77,
      trend: "up" as const,
      suggestions: ["继续保持良好作息", "适当增加运动时间", "多与朋友交流"],
    } as ReportData,
  },

  onLoad() {
    if (!this.ensureProfileCompleted()) {
      return;
    }

    this.loadUserInfo();
    this.checkTodayStatus();
    this.syncTrendWithAssessment();
  },

  onShow() {
    if (!this.ensureProfileCompleted()) {
      return;
    }

    this.loadUserInfo();
    this.checkTodayStatus();
    this.syncTrendWithAssessment();
  },

  ensureProfileCompleted() {
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

  loadUserInfo() {
    const info = wx.getStorageSync("user_info") || {};
    const childInfo = wx.getStorageSync("child_info") || {};
    const studentId = ensureStudentId();
    const merged = {
      ...info,
      name: childInfo.name || info.name || this.data.userInfo.name,
      grade: childInfo.grade || info.grade || this.data.userInfo.grade,
      studentId,
      class:
        info.class !== undefined && info.class !== null
          ? info.class
          : this.data.userInfo.class || "",
      todayMood:
        info.todayMood !== undefined && info.todayMood !== null
          ? info.todayMood
          : this.data.userInfo.todayMood,
    };

    if (merged) {
      const moodLabels = ["很差", "不太好", "一般", "还不错", "很棒"];
      const moodIcons = ["😢", "😔", "😐", "😊", "🥰"];
      const moodIndex = Math.max(
        0,
        Math.min(4, Math.round((merged.todayMood || 0.6) * 4)),
      );
      this.setData({
        userInfo: {
          ...merged,
          todayMood: merged.todayMood || 0.8,
          moodLabel: moodLabels[moodIndex],
          moodIcon: moodIcons[moodIndex],
          studentId,
        },
      });
    }
  },

  onCopyStudentId() {
    const studentId = ensureStudentId();
    wx.setClipboardData({
      data: studentId,
      success: () => wx.showToast({ title: "孩子ID已复制", icon: "success" }),
    });
  },

  checkTodayStatus() {
    const lastCheck = wx.getStorageSync("last_mood_checkin");
    const today = new Date().toDateString();
    this.setData({ todayChecked: lastCheck === today });
  },

  onPsychCardTap(e: any) {
    const card = e.currentTarget.dataset.card as PsychCard;

    switch (card.id) {
      case "checkin":
        this.onMoodCheckin();
        break;
      case "report":
        this.showWeeklyReport();
        break;
      case "knowledge":
        this.showKnowledgeList();
        break;
      case "relax":
        this.startRelax();
        break;
      case "consult":
        wx.switchTab({ url: "/pages/student/chat/chat" });
        break;
      case "test":
        this.startAssessment();
        break;
      default:
        wx.navigateTo({ url: card.path });
    }
  },

  onMoodCheckin() {
    this.setData({ showMoodPicker: true });
  },

  onMoodSelect(e: any) {
    const moodValue = e.currentTarget.dataset.value;
    const moodLabels = ["很差", "不太好", "一般", "还不错", "很棒"];
    const moodIcons = ["😢", "😔", "😐", "😊", "🥰"];

    const userInfo = this.data.userInfo;
    userInfo.todayMood = moodValue / 4;
    userInfo.moodLabel = moodLabels[moodValue - 1];
    userInfo.moodIcon = moodIcons[moodValue - 1];

    wx.setStorageSync("user_info", userInfo);
    wx.setStorageSync("last_mood_checkin", new Date().toDateString());

    this.setData({
      userInfo,
      showMoodPicker: false,
      todayChecked: true,
    });

    wx.showToast({ title: "打卡成功 🌸", icon: "success" });

    // 调用后端API记录
    request("/api/student/checkin", {
      user_id: ensureStudentId(),
      emotion: moodValue,
      sleep: 3,
      study: 3,
      social: 3,
      timestamp: Date.now(),
    }).catch(() => {});
  },

  closeMoodPicker() {
    this.setData({ showMoodPicker: false });
  },

  showWeeklyReport() {
    wx.switchTab({ url: "/pages/student/assessment/assessment" });
  },

  showKnowledgeList() {
    wx.navigateTo({ url: "/pages/student/library/knowledge/knowledge" });
  },

  onKnowledgeTap(e: any) {
    const item = e.currentTarget.dataset.item as KnowledgeItem;
    this.setData({ selectedKnowledge: item, showKnowledgeModal: true });
  },

  closeKnowledgeModal() {
    this.setData({ showKnowledgeModal: false, selectedKnowledge: null });
  },

  readKnowledge() {
    const item = this.data.selectedKnowledge;
    if (item) {
      wx.navigateTo({
        url: `/pages/student/library/knowledge/knowledge?id=${item.id}`,
      });
    }
    this.closeKnowledgeModal();
  },

  startRelax() {
    wx.showModal({
      title: "放松训练",
      content: "先和暖暖聊聊你的状态吧，我会先带你做简单放松训练。",
      success: (res) => {
        if (res.confirm) {
          wx.setStorageSync("student_pending_chat_prompt", "我想要放松训练");
          wx.switchTab({ url: "/pages/student/chat/chat" });
        }
      },
    });
  },

  syncTrendWithAssessment() {
    const userId = ensureStudentId();
    const psychStatus = wx.getStorageSync(`psych_status_${userId}`) || {};
    const rawScores = Array.isArray(psychStatus.radarScores)
      ? psychStatus.radarScores
      : [];

    if (!rawScores.length) {
      this.getWeekChart();
      return;
    }

    const radarScores = rawScores.slice(0, 6).map((value: any) => {
      const num = Number(value);
      if (isNaN(num)) return 0;
      return Math.max(0, Math.min(5, num));
    });

    const avgRisk =
      radarScores.reduce((sum: number, value: number) => sum + value, 0) /
      radarScores.length;
    const currentScore = Math.max(
      40,
      Math.min(100, Math.round(100 - avgRisk * 14)),
    );

    const historyKey = "student_psych_week_scores";
    const historyRaw = wx.getStorageSync(historyKey);
    const history = Array.isArray(historyRaw)
      ? historyRaw
          .map((v: any) => Number(v))
          .filter((v: number) => !isNaN(v) && v >= 0 && v <= 100)
      : [];

    const last = history.length ? history[history.length - 1] : null;
    const nextHistory =
      last === null || Math.abs(last - currentScore) >= 1
        ? [...history, currentScore].slice(-7)
        : history.slice(-7);

    if (!nextHistory.length) nextHistory.push(currentScore);
    wx.setStorageSync(historyKey, nextHistory);

    const trendData =
      nextHistory.length >= 7
        ? nextHistory
        : [
            ...Array(Math.max(0, 7 - nextHistory.length)).fill(
              nextHistory[0] || currentScore,
            ),
            ...nextHistory,
          ];

    const prevScore =
      nextHistory.length > 1
        ? nextHistory[nextHistory.length - 2]
        : nextHistory[nextHistory.length - 1];
    const trend: "up" | "down" | "stable" =
      currentScore > prevScore
        ? "up"
        : currentScore < prevScore
          ? "down"
          : "stable";

    const suggestions =
      avgRisk >= 4
        ? [
            "压力指标偏高，建议先做一次放松训练",
            "试着把困扰告诉暖暖，获取个性化建议",
            "必要时与家长或老师主动沟通",
          ]
        : avgRisk >= 3
          ? [
              "保持规律作息，避免熬夜",
              "每天安排10分钟放松训练",
              "遇到情绪波动时及时记录和倾诉",
            ]
          : [
              "当前状态较稳，继续保持",
              "每周做一次心理测评追踪变化",
              "适当运动和社交有助于维持好状态",
            ];

    this.setData(
      {
        weekData: trendData,
        reportData: {
          averageScore: currentScore,
          trend,
          suggestions,
        },
      },
      () => {
        this.getWeekChart();
      },
    );
  },

  startAssessment() {
    wx.switchTab({ url: "/pages/student/assessment/assessment" });
  },

  onCrisisHelp() {
    wx.showModal({
      title: "紧急求助",
      content:
        "如果你现在很难受，请立即联系老师、家长，或拨打心理援助热线。是否现在打开暖暖求助对话？",
      confirmText: "立即求助",
      cancelText: "我再想想",
      success: (res) => {
        if (res.confirm) {
          wx.switchTab({ url: "/pages/student/chat/chat" });
        }
      },
    });
  },

  onLogout() {
    wx.showModal({
      title: "提示",
      content: "确定要退出登录吗？",
      success: (res) => {
        if (res.confirm) {
          wx.clearStorageSync();
          wx.reLaunch({ url: "/pages/login/login" });
        }
      },
    });
  },

  getWeekChart() {
    const ctx = wx.createCanvasContext("weekChart");
    const data = this.data.weekData;
    const max = 100;
    const min = 0;
    const height = 120;
    const width = 280;
    const stepX = width / (data.length - 1);

    // 绘制折线
    ctx.setStrokeStyle("#69c0ff");
    ctx.setLineWidth(2);
    ctx.beginPath();

    data.forEach((value, index) => {
      const x = index * stepX;
      const y = height - ((value - min) / (max - min)) * height;
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    // 绘制点
    ctx.setFillStyle("#69c0ff");
    data.forEach((value, index) => {
      const x = index * stepX;
      const y = height - ((value - min) / (max - min)) * height;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fill();
    });

    ctx.draw();
  },

  onShareAppMessage() {
    return {
      title: "暖学帮 - 心理成长中心",
      path: "/pages/student/library/library",
    };
  },
});
