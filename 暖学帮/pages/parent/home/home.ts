const api = require('../../utils/api.js');
const { parentLogin, getParentQRToken, bindChild, getChildrenProfiles, getChildPsychReports, getChildPsychStatus, getChildStatus, getChildCheckins, getDailyAdvice, getChildId, getParentAlerts } = api;

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
    const angleRad = angleDeg * Math.PI / 180;
    const r = RADAR_MAX_RADIUS * ratio;
    const x = RADAR_CENTER + r * Math.cos(angleRad);
    const y = RADAR_CENTER + r * Math.sin(angleRad);
    dots.push(`left:${x}rpx;top:${y}rpx;`);
  }
  return dots;
}

Page({
  data: {
    today: '',

    // 登录状态
    isLoggedIn: false,
    loginPhone: '',
    parentId: '',
    parentPhone: '',

    // 绑定弹窗
    showQR: false,
    qrData: null as { qrImageUrl: string; token: string } | null,
    boundChildren: [] as any[],

    childInfo: {
      name: '李明',
      grade: '七年级',
      class: '（3）班',
      studentId: '2024001',
    },

    checkin: { emotion: 4, sleep: 3, study: 3, social: 4 },
    checkinDone: true,

    radarScores: [3, 2, 1, 4, 2, 3] as number[],
    dot0Style: '', dot1Style: '', dot2Style: '',
    dot3Style: '', dot4Style: '', dot5Style: '',
    riskLevel: 1,

    weekCheckins: [
      { day: '一', done: true, emotion: 4 },
      { day: '二', done: true, emotion: 3 },
      { day: '三', done: true, emotion: 4 },
      { day: '四', done: true, emotion: 2 },
      { day: '五', done: false, emotion: 0 },
      { day: '六', done: false, emotion: 0 },
      { day: '日', done: false, emotion: 0 },
    ],

    aiAdvice: '孩子本周学习状态有所波动，建议多关注情绪疏导而非施加压力。',

    recentGrades: [
      { subject: '数学', examDate: '2026-04-02', score: 78 },
      { subject: '英语', examDate: '2026-04-02', score: 85 },
      { subject: '语文', examDate: '2026-04-02', score: 92 },
    ],

    // 测评报告
    psychReports: [] as any[],
    psychReportsLoading: false,
    reportLevelLabel: {
      normal: '正常',
      mild: '轻度',
      moderate: '中度',
      concerning: '偏高',
      severe: '严重',
    } as Record<string, string>,
    reportTypeLabel: {
      weekly: '综合评估',
      pressure: '压力评估',
      communication: '亲子沟通',
    } as Record<string, string>,

    // 预警相关
    unreadAlertCount: 0,
    latestUnreadAlert: null as ParentAlert | null,
    alertTypeMap: {
      emotion_drop: { icon: '😊', color: '#ff9800', label: '情绪' },
      no_checkin: { icon: '📋', color: '#9e9e9e', label: '打卡' },
      test_concerning: { icon: '📊', color: '#f44336', label: '测评' },
      chat_silence: { icon: '💬', color: '#2196f3', label: '互动' },
    } as Record<string, { icon: string; color: string; label: string }>,
  },

  onLoad() {
    const now = new Date();
    this.setData({
      today: `${now.getMonth() + 1}月${now.getDate()}日 周${['日','一','二','三','四','五','六'][now.getDay()]}`,
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
      dot0Style: dots[0] || '', dot1Style: dots[1] || '',
      dot2Style: dots[2] || '', dot3Style: dots[3] || '',
      dot4Style: dots[4] || '', dot5Style: dots[5] || '',
    });
  },

  // ===== 登录 =====
  onPhoneInput(e: any) {
    this.setData({ loginPhone: e.detail.value });
  },

  checkLogin() {
    const saved = wx.getStorageSync('parent_account') || null;
    if (saved && saved.phone) {
      this.setData({
        isLoggedIn: true,
        parentId: String(saved.id),
        parentPhone: saved.phone,
        boundChildren: saved.children || [],
      });
      // 每次进来都从后端拉最新绑定数据
      this.refreshChildren();
      this.loadAllData();
    }
  },

  onRefreshChildren() {
    const phone = this.data.parentPhone;
    if (!phone) return;
    parentLogin(phone)
      .then((res: any) => {
        if (res.success) {
          const account = res.account;
          const data = {
            id: account.id, phone: account.phone,
            name: account.name || '', children: res.bound_children || [],
          };
          wx.setStorageSync('parent_account', data);
          // 查孩子档案获取姓名
          const childIds = res.bound_children || [];
          if (childIds.length > 0) {
            getChildrenProfiles(childIds)
              .then((profRes: any) => {
                if (profRes.success) {
                  const profiles = profRes.profiles || [];
                  const childrenWithInfo = childIds.map((id: string) => {
                    const p = profiles.find((x: any) => x.user_id === id) || {};
                    return { id, name: p.name || '孩子', grade: p.grade || '' };
                  });
                  this.setData({ boundChildren: childrenWithInfo });
                  // 自动选中第一个孩子
                  const first = childrenWithInfo[0];
                  if (first) {
                    wx.setStorageSync('bound_child_id', first.id);
                    this.loadAllData();
                  }
                } else {
                  const childrenWithInfo = childIds.map((id: string) => ({ id, name: '孩子', grade: '' }));
                  this.setData({ boundChildren: childrenWithInfo });
                  if (childrenWithInfo[0]) {
                    wx.setStorageSync('bound_child_id', childrenWithInfo[0].id);
                    this.loadAllData();
                  }
                }
              })
              .catch(() => {
                const childrenWithInfo = childIds.map((id: string) => ({ id, name: '孩子', grade: '' }));
                this.setData({ boundChildren: childrenWithInfo });
                if (childrenWithInfo[0]) {
                  wx.setStorageSync('bound_child_id', childrenWithInfo[0].id);
                  this.loadAllData();
                }
              });
          } else {
            this.setData({ boundChildren: [] });
          }
          wx.showToast({ title: '已刷新', icon: 'success' });
        }
      })
      .catch(() => {});
  },

  onLogin() {
    const phone = this.data.loginPhone.trim();
    if (!/^1\d{10}$/.test(phone)) {
      wx.showToast({ title: '手机号格式不正确', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '登录中...', mask: true });
    parentLogin(phone)
      .then((res: any) => {
        wx.hideLoading();
        if (res.success) {
          const account = res.account;
          const data = {
            id: account.id,
            phone: account.phone,
            name: account.name || '',
            children: res.bound_children || [],
          };
          wx.setStorageSync('parent_account', data);
          this.setData({
            isLoggedIn: true,
            parentId: String(account.id),
            parentPhone: account.phone,
            boundChildren: res.bound_children || [],
          });
          // 登录后自动刷新孩子数据
          if (res.bound_children && res.bound_children.length > 0) {
            this.loadAllData();
          }
        }
      })
      .catch(() => {
        wx.hideLoading();
        wx.showToast({ title: '登录失败，请重试', icon: 'none' });
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

  loadQRCode() {
    const parentId = this.data.parentId;
    if (!parentId) return;
    getParentQRToken(Number(parentId))
      .then((res: any) => {
        if (res.success) {
          // 生成二维码图片URL（使用第三方API）
          const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=${encodeURIComponent(res.qr_url)}`;
          this.setData({ qrData: { qrImageUrl, token: res.token } });
        }
      })
      .catch(() => {
        wx.showToast({ title: '生成二维码失败', icon: 'none' });
      });
  },

  // ===== 加载数据 =====
  loadAllData() {
    const childId = getChildId();
    const parentId = this.data.parentId;
    if (!childId) return;
    Promise.all([
      getChildStatus(childId).catch(() => null),
      getChildCheckins(childId, 7).catch(() => null),
      getDailyAdvice(childId).catch(() => null),
      this.loadPsychReports(childId),
      parentId ? this.loadAlerts(parentId) : Promise.resolve(),
    ]).then(([statusData, checkinsData, adviceData]) => {
      if (statusData && statusData.status === 'ok') {
        const m = statusData.psych && statusData.psych.metrics || {};
        const checkin = {
          emotion: m.emotion || 3, sleep: m.sleep || 3,
          study: m.study || 3, social: m.social || 3,
        };
        const done = !!(checkin.emotion && checkin.sleep && checkin.study && checkin.social);
        this.setData({ checkin, checkinDone: done });
        if (statusData.radarScores) this.updateRadar(statusData.radarScores);
        if (statusData.riskLevel !== undefined) this.setData({ riskLevel: statusData.riskLevel });
        if (statusData.summary && statusData.summary.profile) {
          this.setData({
            childInfo: {
              name: statusData.summary.profile.name || '孩子',
              grade: statusData.summary.profile.grade || '',
              class: '',
              studentId: statusData.summary.profile.user_id || '',
            },
          });
        }
      }
      if (checkinsData && checkinsData.records) {
        const weekDays = [...this.data.weekCheckins];
        checkinsData.records.forEach((r: any, i: number) => {
          if (i < 7) { weekDays[i].done = true; weekDays[i].emotion = r.emotion || 3; }
        });
        this.setData({ weekCheckins: weekDays });
      }
      if (adviceData && adviceData.advice) this.setData({ aiAdvice: adviceData.advice });
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
          const unread = (res.alerts || []).filter((a: ParentAlert) => !a.is_read);
          this.setData({
            unreadAlertCount: res.unread_count || 0,
            latestUnreadAlert: unread.length > 0 ? unread[0] : null,
          });
        }
      })
      .catch(() => {});
  },

  goToAlerts() {
    wx.navigateTo({ url: '/pages/alerts/alerts' });
  },

  goToAI() {
    wx.switchTab({ url: '/pages/ai-chat/ai-chat' });
  },

  onViewReportDetail(e: any) {
    const childId = getChildId();
    wx.navigateTo({
      url: `/pages/report-detail/report-detail?id=${e.currentTarget.dataset.id}&child_id=${childId}`,
    });
  },

  onViewAllReports() {
    wx.showToast({ title: '全部报告功能开发中', icon: 'none' });
  },
});
