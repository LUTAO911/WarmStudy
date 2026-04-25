export {};

const {
  loginByPhone,
  sendVerifyCode,
} = require("../../utils/api.js");

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
      .catch(() => {
        wx.showToast({ title: "验证码发送失败", icon: "none" });
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

    console.log("onPhoneLogin called", { phone, code, selectedRole, agreed, redirecting });

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
      .catch((err) => {
        console.warn("手机号登录接口不可用，回退到本地演示登录", err);
        this.mockLogin(selectedRole);
      });
  },

  // 处理登录成功
  handleLoginSuccess(result: any, role: string) {
    const payload = result.data || {};
    const userId = String(payload.user_id || "");
    // 保存登录信息
    wx.setStorageSync("user_id", userId);
    wx.setStorageSync("user_role", role);
    wx.setStorageSync("user_name", payload.name);
    wx.setStorageSync("user_phone", payload.phone);

    if (role === "student") {
      const studentId = String(payload.student_id || userId);
      wx.setStorageSync("student_user_id", studentId);
      wx.setStorageSync("student_id", studentId);
    } else {
      const children = payload.bound_children || [];
      wx.setStorageSync("parent_user_id", userId);
      wx.setStorageSync("parent_account", {
        id: userId,
        parent_id: userId,
        phone: payload.phone,
        name: payload.name || "",
        children,
      });
      if (children.length > 0) {
        wx.setStorageSync("bound_child_id", children[0]);
      } else {
        wx.removeStorageSync("bound_child_id");
      }
    }

    wx.showToast({ title: "登录成功", icon: "success" });
    this.navigateToHome(role);
  },

  // 模拟登录（开发阶段使用）
  mockLogin(role: string) {
    console.log("mockLogin called", role);
    const localStudentId =
      wx.getStorageSync("student_user_id") ||
      String(Math.floor(100000000 + Math.random() * 900000000));
    const phone = this.data.phone || "13800138000";
    const mockUserId =
      role === "student" ? localStudentId : `parent_${phone.slice(-4) || "0001"}`;
    const mockName = role === "student" ? "学生用户" : "家长用户";

    wx.setStorageSync("user_id", mockUserId);
    wx.setStorageSync("user_role", role);
    wx.setStorageSync("user_name", mockName);
    wx.setStorageSync("user_phone", phone);
    if (role === "student") {
      wx.setStorageSync("student_user_id", mockUserId);
      wx.setStorageSync("student_id", mockUserId);
    } else {
      wx.setStorageSync("parent_user_id", mockUserId);
      wx.setStorageSync("parent_account", {
        id: mockUserId,
        parent_id: mockUserId,
        phone,
        name: mockName,
        children: [],
      });
      wx.removeStorageSync("bound_child_id");
    }

    console.log("登录信息已保存", { mockUserId, role, mockName });

    wx.showToast({
      title: "登录成功",
      icon: "success",
    });
    this.navigateToHome(role);
  },

  // 跳转到首页
  navigateToHome(role: string) {
    console.log("navigateToHome called", role);

    if (this.data.redirecting) {
      console.log("已有跳转进行中，忽略重复跳转", role);
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
        success: () => {
          console.log("学生端跳转成功");
        },
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
        success: () => {
          console.log("家长端跳转成功");
        },
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

