Page({
  data: { notif: { checkin: true, weekly: true, alert: true } },
  onLoad() {
    const s: any = wx.getStorageSync('parent_notif');
    if (Object.keys(s || {}).length > 0) this.setData({ notif: s });
  },
  onBindChild() { wx.showToast({ title: '孩子账号已绑定', icon: 'none' }); },
  onBindSchool() { wx.showToast({ title: '智学网绑定即将上线', icon: 'none' }); },
  onBindParent() { wx.showToast({ title: '邀请功能即将上线', icon: 'none' }); },
  onToggle(e: any) {
    const t = e.currentTarget.dataset.type as keyof typeof this.data.notif;
    const val = e.detail.value;
    const n = { ...this.data.notif, [t]: val };
    this.setData({ notif: n });
    wx.setStorageSync('parent_notif', n);
  },
  onLogout() {
    wx.showModal({ title: '提示', content: '确定要退出登录吗？', success: (r) => {
      if (r.confirm) { wx.clearStorageSync(); wx.reLaunch({ url: '/pages/settings/settings' }); }
    }});
  },
});
