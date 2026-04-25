export {};

const api = require("../../../utils/api.js");
const {
  parentLogin,
  getParentQRToken,
  bindChild,
  getChildrenProfiles,
  getChildComprehensiveReport,
  getChildPsychReports,
  getChildPsychStatus,
  getChildStatus,
  getChildCheckins,
  getDailyAdvice,
  getChildId,
  getParentAlerts,
  isValidStudentId,
} = api;

// 定义 ParentAlert 类型
interface ParentAlert {
  id: number;
  child_id: string;
  child_name: string;
  alert_type: string;
  title: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

const RADAR_SIZE = 220;
const RADAR_CENTER = RADAR_SIZE / 2;
const RADAR_MAX_RADIUS = RADAR_SIZE / 2 - 20;
const MAX_SCORE = 5;

function calcRadarDots(scores: number[]) {
  const dots: string[] = [];
  for (let i = 0; i < 6; i++) {
    const score = Math.min(scores[i] || 0, MAX_SCORE);
    const ratio = score / MAX_SCORE;
    const angleDeg = -90 + i * 60;
    const angleRad = (angleDeg * Math.PI) / 180;
    const r = RADAR_MAX_RADIUS * ratio;
    const x = RADAR_CENTER + r * Math.cos(angleRad);
    const y = RADAR_CENTER + r * Math.sin(angleRad);
    dots.push(`left:${x}rpx;top:${y}rpx;`);
  }
  return dots;
}

Page({
  data: {
    today: "",

    // 登录状态
    isLoggedIn: false,
    loginPhone: "",
    parentId: "",
    parentPhone: "",

    // 绑定弹窗
    showQR: false,
    qrData: null as { qrImageUrl: string; token: string } | null,
    boundChildren: [] as any[],
    bindChildId: "",
    bindingChild: false,
    hasBoundChild: false,

    childInfo: {
      name: "未绑定孩子",
      grade: "",
      class: "",
      studentId: "--",
    },

    checkin: { emotion: 0, sleep: 0, study: 0, social: 0 },
    checkinDone: false,

    radarScores: [3, 2, 1, 4, 2, 3] as number[],
    dot0Style: "",
    dot1Style: "",
    dot2Style: "",
    dot3Style: "",
    dot4Style: "",
    dot5Style: "",
    radarCanvasSize: 220,
    riskLevel: 0,

    weekCheckins: [
      { day: "一", done: true, emotion: 4 },
      { day: "二", done: true, emotion: 3 },
      { day: "三", done: true, emotion: 4 },
      { day: "四", done: true, emotion: 2 },
      { day: "五", done: false, emotion: 0 },
      { day: "六", done: false, emotion: 0 },
      { day: "日", done: false, emotion: 0 },
    ],

    aiAdvice: "绑定孩子后，系统会根据测评、打卡和对话状态生成家长建议。",

    comprehensiveReport: null as any,

    recentGrades: [
      { subject: "数学", examDate: "2026-04-02", score: 78 },
      { subject: "英语", examDate: "2026-04-02", score: 85 },
      { subject: "语文", examDate: "2026-04-02", score: 92 },
    ],

    // 测评报告
    psychReports: [] as any[],
    psychReportsLoading: false,
    reportLevelLabel: {
      normal: "正常",
      mild: "轻度",
      moderate: "中度",
      concerning: "偏高",
      severe: "严重",
    } as Record<string, string>,
    reportTypeLabel: {
      weekly: "综合评估",
      pressure: "压力评估",
      communication: "亲子沟通",
    } as Record<string, string>,

    // 预警相关
    unreadAlertCount: 0,
    latestUnreadAlert: null as ParentAlert | null,
    alertTypeMap: {
      emotion_drop: { icon: "情", color: "#ff9800", label: "情绪" },
      no_checkin: { icon: "卡", color: "#9e9e9e", label: "打卡" },
      test_concerning: { icon: "测", color: "#f44336", label: "测评" },
      chat_silence: { icon: "聊", color: "#2196f3", label: "互动" },
    } as Record<string, { icon: string; color: string; label: string }>,
  },

  onLoad() {
    const now = new Date();
    const windowInfo = wx.getWindowInfo();
    const radarCanvasSize = Math.round(
      (windowInfo.windowWidth * RADAR_SIZE) / 750,
    );
    this.setData({
      today: `${now.getMonth() + 1}月${now.getDate()}日 周${["日", "一", "二", "三", "四", "五", "六"][now.getDay()]}`,
      radarCanvasSize,
    });
    this.updateRadar(this.data.radarScores);
    this.checkLogin();
  },

  onShow() {
    if (this.data.isLoggedIn) {
      this.refreshChildren();
      this.loadAllData();
    }
  },

  updateRadar(scores: number[]) {
    const dots = calcRadarDots(scores);
    this.setData({
      radarScores: scores,
      dot0Style: dots[0] || "",
      dot1Style: dots[1] || "",
      dot2Style: dots[2] || "",
      dot3Style: dots[3] || "",
      dot4Style: dots[4] || "",
      dot5Style: dots[5] || "",
    });

    this.drawRadarArea(scores);
  },

  drawRadarArea(scores: number[]) {
    const canvasSize = this.data.radarCanvasSize || 220;
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

  // ===== 登录 =====
  onPhoneInput(e: any) {
    this.setData({ loginPhone: e.detail.value });
  },

  resetChildData(showBind = false) {
    wx.removeStorageSync("bound_child_id");
    this.setData({
      hasBoundChild: false,
      childInfo: {
        name: "未绑定孩子",
        grade: "",
        class: "",
        studentId: "--",
      },
      checkin: { emotion: 0, sleep: 0, study: 0, social: 0 },
      checkinDone: false,
      riskLevel: 0,
      aiAdvice: "绑定孩子后，系统会根据测评、打卡和对话状态生成家长建议。",
      psychReports: [],
      comprehensiveReport: null,
      latestUnreadAlert: null,
      unreadAlertCount: 0,
      showQR: showBind,
    });
    this.updateRadar([0, 0, 0, 0, 0, 0]);
  },

  applyBoundChildren(childIds: string[]) {
    if (!childIds.length) {
      this.setData({ boundChildren: [] });
      this.resetChildData(true);
      return Promise.resolve();
    }

    return getChildrenProfiles(childIds)
      .then((profRes: any) => {
        const profiles = profRes.success ? profRes.profiles || [] : [];
        const childrenWithInfo = childIds.map((id: string) => {
          const p = profiles.find((x: any) => x.user_id === id) || {};
          return {
            id,
            name: p.name || `孩子${id.slice(-3)}`,
            grade: p.grade || "",
            active: id === wx.getStorageSync("bound_child_id"),
          };
        });
        const selectedId =
          wx.getStorageSync("bound_child_id") &&
          childIds.includes(wx.getStorageSync("bound_child_id"))
            ? wx.getStorageSync("bound_child_id")
            : childrenWithInfo[0].id;
        wx.setStorageSync("bound_child_id", selectedId);
        this.setData({
          boundChildren: childrenWithInfo.map((item: any) => ({
            ...item,
            active: item.id === selectedId,
          })),
          hasBoundChild: true,
          showQR: false,
        });
        this.loadAllData();
      })
      .catch(() => {
        const selectedId = childIds[0];
        wx.setStorageSync("bound_child_id", selectedId);
        this.setData({
          boundChildren: childIds.map((id: string) => ({
            id,
            name: `孩子${id.slice(-3)}`,
            grade: "",
            active: id === selectedId,
          })),
          hasBoundChild: true,
          showQR: false,
        });
        this.loadAllData();
      });
  },

  checkLogin() {
    const saved = wx.getStorageSync("parent_account") || null;
    if (saved && saved.phone) {
      const parentId = String(saved.parent_id || saved.id || "");
      this.setData({
        isLoggedIn: true,
        parentId,
        parentPhone: saved.phone,
        boundChildren: saved.children || [],
      });
      // 每次进来都从后端拉最新绑定数据
      this.refreshChildren();
    }
  },

  onRefreshChildren() {
    const phone = this.data.parentPhone;
    if (!phone) return;
    parentLogin(phone)
      .then((res: any) => {
        if (res.success) {
          const account = res.account;
          const parentId = String(account.parent_id || account.id);
          const data = {
            id: parentId,
            parent_id: parentId,
            phone: account.phone,
            name: account.name || "",
            children: res.bound_children || [],
          };
          wx.setStorageSync("parent_account", data);
          wx.setStorageSync("parent_user_id", parentId);
          this.setData({ parentId, parentPhone: account.phone });
          const childIds = res.bound_children || [];
          this.applyBoundChildren(childIds);
          wx.showToast({ title: "已刷新", icon: "success" });
        }
      })
      .catch(() => {});
  },

  onLogin() {
    const phone = this.data.loginPhone.trim();
    if (!/^1\d{10}$/.test(phone)) {
      wx.showToast({ title: "手机号格式不正确", icon: "none" });
      return;
    }
    wx.showLoading({ title: "登录中...", mask: true });
    parentLogin(phone)
      .then((res: any) => {
        wx.hideLoading();
        if (res.success) {
          const account = res.account;
          const parentId = String(account.parent_id || account.id);
          const data = {
            id: parentId,
            parent_id: parentId,
            phone: account.phone,
            name: account.name || "",
            children: res.bound_children || [],
          };
          wx.setStorageSync("parent_account", data);
          wx.setStorageSync("parent_user_id", parentId);
          this.setData({
            isLoggedIn: true,
            parentId,
            parentPhone: account.phone,
            boundChildren: res.bound_children || [],
          });
          this.applyBoundChildren(res.bound_children || []);
        }
      })
      .catch(() => {
        wx.hideLoading();
        wx.showToast({ title: "登录失败，请重试", icon: "none" });
      });
  },

  // ===== 绑定弹窗 =====
  onShowBindQR() {
    if (!this.data.isLoggedIn) {
      this.setData({ showQR: true });
      return;
    }
    this.setData({ showQR: true, qrData: null });
    this.loadQRCode();
  },
  onCloseQR() {
    this.setData({ showQR: false });
  },
  onBindChildIdInput(e: any) {
    this.setData({ bindChildId: String(e.detail.value || "").replace(/\D/g, "").slice(0, 9) });
  },

  onBindChildById() {
    const parentId = this.data.parentId;
    const childId = this.data.bindChildId.trim();
    if (!parentId) {
      wx.showToast({ title: "请先登录家长端", icon: "none" });
      return;
    }
    if (!isValidStudentId(childId)) {
      wx.showToast({ title: "请输入9位孩子ID", icon: "none" });
      return;
    }

    this.setData({ bindingChild: true });
    bindChild(parentId, childId)
      .then((res: any) => {
        if (!res.success) {
          throw new Error(res.error || "绑定失败");
        }
        wx.setStorageSync("bound_child_id", childId);
        const account = wx.getStorageSync("parent_account") || {};
        const children = Array.from(new Set([...(account.children || []), childId]));
        wx.setStorageSync("parent_account", { ...account, children });
        this.setData({ bindChildId: "", showQR: false, bindingChild: false });
        wx.showToast({ title: "绑定成功", icon: "success" });
        this.applyBoundChildren(children as string[]);
      })
      .catch((err: Error) => {
        this.setData({ bindingChild: false });
        wx.showToast({ title: err.message || "绑定失败", icon: "none" });
      });
  },

  loadQRCode() {
    const parentId = this.data.parentId;
    if (!parentId) return;
    getParentQRToken(parentId)
      .then((res: any) => {
        if (res.success) {
          // 生成二维码图片URL（使用第三方API）
          const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=${encodeURIComponent(res.qr_url)}`;
          this.setData({ qrData: { qrImageUrl, token: res.token } });
        }
      })
      .catch(() => {
        wx.showToast({ title: "生成二维码失败", icon: "none" });
      });
  },

  // ===== 加载数据 =====
  loadAllData() {
    const childId = getChildId();
    const parentId = this.data.parentId;
    if (!childId) {
      this.resetChildData(this.data.isLoggedIn);
      return;
    }
    const localPsych = wx.getStorageSync(`psych_status_${childId}`) || null;
    Promise.all([
      getChildStatus(childId).catch(() => null),
      getChildCheckins(childId, 7).catch(() => null),
      getDailyAdvice(childId).catch(() => null),
      this.loadComprehensiveReport(childId),
      this.loadPsychReports(childId),
      parentId ? this.loadAlerts(parentId) : Promise.resolve(),
    ]).then(([statusData, checkinsData, adviceData]) => {
      if (statusData && statusData.status === "ok") {
        const m = (statusData.psych && statusData.psych.metrics) || {};
        const checkin = {
          emotion: m.emotion || 3,
          sleep: m.sleep || 3,
          study: m.study || 3,
          social: m.social || 3,
        };
        const done = !!(
          checkin.emotion &&
          checkin.sleep &&
          checkin.study &&
          checkin.social
        );
        this.setData({ checkin, checkinDone: done });
        if (statusData.radarScores) this.updateRadar(statusData.radarScores);
        if (statusData.riskLevel !== undefined)
          this.setData({ riskLevel: statusData.riskLevel });
        if (statusData.summary && statusData.summary.profile) {
          this.setData({
            childInfo: {
              name: statusData.summary.profile.name || "孩子",
              grade: statusData.summary.profile.grade || "",
              class: "",
              studentId: statusData.summary.profile.user_id || "",
            },
          });
        }
      }

      // 优先读取学生端最新本地画像缓存，确保测评提交后家长端即时跟随
      if (localPsych && Array.isArray(localPsych.radarScores)) {
        this.updateRadar(localPsych.radarScores);
        if (localPsych.riskLevel !== undefined) {
          this.setData({ riskLevel: localPsych.riskLevel });
        }
      }

      if (checkinsData && checkinsData.records) {
        const weekDays = [...this.data.weekCheckins];
        checkinsData.records.forEach((r: any, i: number) => {
          if (i < 7) {
            weekDays[i].done = true;
            weekDays[i].emotion = r.emotion || 3;
          }
        });
        this.setData({ weekCheckins: weekDays });
      }
      if (adviceData && adviceData.advice)
        this.setData({ aiAdvice: adviceData.advice });
    });
  },

  loadComprehensiveReport(childId: string) {
    return getChildComprehensiveReport(childId)
      .then((res: any) => {
        if (res.success && res.report) {
          this.setData({ comprehensiveReport: res.report });
          if (Array.isArray(res.report.radarScores)) {
            this.updateRadar(res.report.radarScores);
          }
        }
      })
      .catch(() => {
        this.setData({ comprehensiveReport: null });
      });
  },

  loadPsychReports(childId: string) {
    this.setData({ psychReportsLoading: true });
    return getChildPsychReports(childId, 5)
      .then((res: any) => {
        if (res.success && res.reports) {
          this.setData({ psychReports: res.reports });
        }
      })
      .catch(() => {})
      .finally(() => {
        this.setData({ psychReportsLoading: false });
      });
  },

  loadAlerts(parentId: string) {
    return getParentAlerts(parentId, 10, 0)
      .then((res: any) => {
        if (res.success) {
          const unread = (res.alerts || []).filter(
            (a: ParentAlert) => !a.is_read,
          );
          this.setData({
            unreadAlertCount: res.unread_count || 0,
            latestUnreadAlert: unread.length > 0 ? unread[0] : null,
          });
        }
      })
      .catch(() => {});
  },

  goToAlerts() {
    wx.navigateTo({ url: "/pages/parent/alerts/alerts" });
  },

  goToAI() {
    wx.navigateTo({ url: "/pages/parent/ai-chat/ai-chat" });
  },

  onSelectChild(e: any) {
    const childId = e.currentTarget.dataset.id;
    if (!childId) return;
    wx.setStorageSync("bound_child_id", childId);
    this.setData({
      boundChildren: this.data.boundChildren.map((item: any) => ({
        ...item,
        active: item.id === childId,
      })),
      showQR: false,
      hasBoundChild: true,
    });
    this.loadAllData();
  },

  onViewReportDetail(e: any) {
    const childId = getChildId();
    wx.navigateTo({
      url: `/pages/parent/report-detail/report-detail?id=${e.currentTarget.dataset.id}&child_id=${childId}`,
    });
  },

  onViewAllReports() {
    wx.showToast({ title: "全部报告功能开发中", icon: "none" });
  },

  onGradeTrendTap() {
    wx.showToast({ title: "成绩趋势功能开发中", icon: "none" });
  },

  onParentHome() {
    // 当前页
  },

  onParentAI() {
    wx.reLaunch({ url: "/pages/parent/ai-chat/ai-chat" });
  },

  onParentSettings() {
    wx.reLaunch({ url: "/pages/parent/settings/settings" });
  },
});
