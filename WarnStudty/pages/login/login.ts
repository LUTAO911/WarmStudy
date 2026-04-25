const {
  loginByPhone,
  sendVerifyCode,
} = require("../../utils/api.js");

const isLocalMockEnvironment = (): boolean => {
  const app = getApp<IAppOption>();
  const apiBase =
    app && app.globalData && typeof app.globalData.apiBase === "string"
      ? app.globalData.apiBase
      : "";
  return /localhost|127\.0\.0\.1|192\.168\./i.test(apiBase);
};

const getReadableError = (err: any): string => {
  if (err && typeof err.message === "string" && err.message) {
    return err.message;
  }
  if (err && typeof err.errMsg === "string" && err.errMsg) {
    return err.errMsg;
  }
  return "当前无法连接服务器，请稍后再试";
};

Page({
  data: {
    selectedRole: "" as "student" | "parent" | "",
    phone: "",
    code: "",
    countdown: 0,
    agreed: false,
    redirecting: false,
  },

  countdownTimer: null as ReturnType<typeof setInterval> | null,

  onLoad() {
    // 检查是否已登录
    const userRole = wx.getStorageSync("user_role");
    const userId = wx.getStorageSync("user_id");

    if (userRole && userId) {
      // 已登录，直接跳转
      this.navigateToHome(userRole);
    }
  },

  onUnload() {
    this.clearCountdownTimer();
  },

  clearCountdownTimer() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
  },

  // 选择身份
  onSelectRole(e: any) {
    const role = e.currentTarget.dataset.role;
    this.setData({ selectedRole: role });
  },

  // 切换身份
  onSwitchRole() {
    this.setData({ selectedRole: "" });
  },

  // 手机号输入
  onPhoneInput(e: any) {
    this.setData({ phone: e.detail.value });
  },

  // 验证码输入
  onCodeInput(e: any) {
    this.setData({ code: e.detail.value });
  },

  // 发送验证码
  onSendCode() {
    const { phone, countdown } = this.data;

    if (countdown > 0) return;

    if (!phone || phone.length !== 11) {
      wx.showToast({ title: "请输入正确的手机号", icon: "none" });
      return;
    }

    sendVerifyCode(phone)
      .then(() => {
        wx.showToast({ title: "验证码已发送", icon: "success" });

        this.clearCountdownTimer();
        this.setData({ countdown: 60 });
        this.countdownTimer = setInterval(() => {
          const newCountdown = this.data.countdown - 1;
          if (newCountdown <= 0) {
            this.clearCountdownTimer();
            this.setData({ countdown: 0 });
            return;
          }
          this.setData({ countdown: newCountdown });
        }, 1000);
      })
      .catch((err: any) => {
        wx.showToast({ title: getReadableError(err), icon: "none", duration: 2500 });
      });
  },

  // 微信登录
  onWechatLogin() {
    const { selectedRole, agreed } = this.data;

    if (!selectedRole) {
      wx.showToast({ title: "请先选择身份", icon: "none" });
      return;
    }

    if (!agreed) {
      wx.showToast({ title: "请先同意用户协议", icon: "none" });
      return;
    }
    wx.showToast({
      title: "演示版暂不开放微信登录，请使用手机号登录",
      icon: "none",
      duration: 2500,
    });
  },

  // 手机号登录
  onPhoneLogin() {
    const { phone, code, selectedRole, agreed, redirecting } = this.data;

    if (redirecting) {
      return;
    }

    if (!selectedRole) {
      wx.showToast({ title: "请先选择身份", icon: "none" });
      return;
    }

    if (!agreed) {
      wx.showToast({ title: "请先同意用户协议", icon: "none" });
      return;
    }

    if (!phone || phone.length !== 11) {
      wx.showToast({ title: "请输入正确的手机号", icon: "none" });
      return;
    }

    if (!code || code.length !== 6) {
      wx.showToast({ title: "请输入6位验证码", icon: "none" });
      return;
    }

    loginByPhone(phone, code, selectedRole)
      .then((result: any) => {
        if (result.success) {
          this.handleLoginSuccess(result, selectedRole);
        } else {
          wx.showToast({ title: result.message || "登录失败", icon: "none" });
        }
      })
      .catch((err: any) => {
        if (isLocalMockEnvironment()) {
          console.warn("本地开发环境登录失败，回退到演示账号", err);
          this.mockLogin(selectedRole);
          return;
        }

        wx.showModal({
          title: "连接服务器失败",
          content: getReadableError(err),
          showCancel: false,
          confirmText: "知道了",
        });
      });
  },

  // 处理登录成功
  handleLoginSuccess(result: any, role: string) {
    // 保存登录信息
    wx.setStorageSync("user_id", result.data.user_id);
    wx.setStorageSync("user_role", role);
    wx.setStorageSync("user_name", result.data.name);
    wx.setStorageSync("user_phone", result.data.phone);
    if (result.data.token) {
      wx.setStorageSync("auth_token", result.data.token);
    }

    wx.showToast({ title: "登录成功", icon: "success" });
    this.navigateToHome(role);
  },

  // 模拟登录（开发阶段使用）
  mockLogin(role: string) {
    const mockUserId = role === "student" ? "student_001" : "parent_001";
    const mockName = role === "student" ? "学生用户" : "家长用户";

    wx.setStorageSync("user_id", mockUserId);
    wx.setStorageSync("user_role", role);
    wx.setStorageSync("user_name", mockName);
    wx.setStorageSync("user_phone", this.data.phone || "13800138000");

    wx.showToast({
      title: "登录成功",
      icon: "success",
    });
    this.navigateToHome(role);
  },

  // 跳转到首页
  navigateToHome(role: string) {
    if (this.data.redirecting) {
      return;
    }

    this.setData({ redirecting: true });

    const complete = () => {
      this.setData({ redirecting: false });
    };

    // 学生端使用 switchTab 跳转到 tabBar 页面
    if (role === "student") {
      wx.switchTab({
        url: "/pages/student/chat/chat",
        fail: (err) => {
          console.error("学生端跳转失败", err);
          wx.showToast({ title: "跳转失败", icon: "none" });
        },
        complete,
      });
    } else {
      // 家长端使用 navigateTo
      wx.navigateTo({
        url: "/pages/parent/home/home",
        fail: (err) => {
          console.error("家长端跳转失败", err);
          wx.showToast({ title: "跳转失败", icon: "none" });
        },
        complete,
      });
    }
  },

  // 切换协议同意状态
  onToggleAgree() {
    this.setData({ agreed: !this.data.agreed });
  },

  // 查看用户协议
  onViewAgreement() {
    wx.showModal({
      title: "用户协议",
      content: "这里是用户协议内容...",
      showCancel: false,
    });
  },

  // 查看隐私政策
  onViewPrivacy() {
    wx.showModal({
      title: "隐私政策",
      content: "这里是隐私政策内容...",
      showCancel: false,
    });
  },
});

