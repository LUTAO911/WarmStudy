// app.ts
App<IAppOption>({
  globalData: {
    userId: '',
    userRole: '',
    childId: '',
    apiBase: 'http://localhost:8000',
  },
  onLaunch() {
    // 初始化：检查登录状态
    this.checkLoginStatus();
  },

  // 检查登录状态
  checkLoginStatus() {
    const userId = wx.getStorageSync('user_id');
    const userRole = wx.getStorageSync('user_role');

    if (userId && userRole) {
      this.globalData.userId = userId;
      this.globalData.userRole = userRole;

      // 如果是家长，获取绑定的孩子ID
      if (userRole === 'parent') {
        this.globalData.childId = wx.getStorageSync('bound_child_id') || '';
      }
    }
  },

  // 设置当前用户
  setCurrentUser(userId: string, role: string) {
    this.globalData.userId = userId;
    this.globalData.userRole = role;
    wx.setStorageSync('user_id', userId);
    wx.setStorageSync('user_role', role);
  },

  // 清除登录状态
  clearLoginStatus() {
    this.globalData.userId = '';
    this.globalData.userRole = '';
    this.globalData.childId = '';
    wx.removeStorageSync('user_id');
    wx.removeStorageSync('user_role');
    wx.removeStorageSync('user_name');
    wx.removeStorageSync('user_phone');
    wx.removeStorageSync('bound_child_id');
  },
});
