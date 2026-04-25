export {};

Page({
  data: {
    notif: { checkin: true, weekly: true, alert: true },
    accountName: "家长",
    avatarText: "家",
    accountPhone: "未登录",
    childBindingText: "未绑定",
    childBindingClass: "warn",
  },
  onLoad() {
    const s: any = wx.getStorageSync("parent_notif");
    if (Object.keys(s || {}).length > 0) this.setData({ notif: s });
    this.loadAccountState();
  },
  onShow() {
    this.loadAccountState();
  },
  loadAccountState() {
    const account = wx.getStorageSync("parent_account") || {};
    const children = account.children || [];
    const accountName = account.name || wx.getStorageSync("user_name") || "家长";
    this.setData({
      accountName,
      avatarText: String(accountName).slice(0, 1) || "家",
      accountPhone: account.phone || wx.getStorageSync("user_phone") || "未登录",
      childBindingText: children.length ? `${children.length} 个孩子` : "未绑定",
      childBindingClass: children.length ? "success" : "warn",
    });
  },
  onBindChild() {
    wx.reLaunch({ url: "/pages/parent/home/home" });
  },
  onBindSchool() {
    wx.showToast({ title: "智学网绑定即将上线", icon: "none" });
  },
  onBindParent() {
    wx.showToast({ title: "邀请功能即将上线", icon: "none" });
  },
  onToggle(e: any) {
    const t = e.currentTarget.dataset.type as keyof typeof this.data.notif;
    const val = e.detail.value;
    const n = { ...this.data.notif, [t]: val };
    this.setData({ notif: n });
    wx.setStorageSync("parent_notif", n);
  },
  onLogout() {
    wx.showModal({
      title: "提示",
      content: "确定要退出登录吗？",
      success: (r) => {
        if (r.confirm) {
          wx.clearStorageSync();
          wx.reLaunch({ url: "/pages/login/login" });
        }
      },
    });
  },

  onParentHome() {
    wx.reLaunch({ url: "/pages/parent/home/home" });
  },

  onParentAI() {
    wx.reLaunch({ url: "/pages/parent/ai-chat/ai-chat" });
  },

  onParentSettings() {
    // 当前页
  },
});
