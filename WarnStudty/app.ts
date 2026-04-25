// app.ts
const DEFAULT_API_BASE = 'https://wsapi.supermoxi.top';

App<IAppOption>({
  globalData: {
    userId: '',
    userRole: '',
    childId: '',
    apiBase: DEFAULT_API_BASE,
  },
  onLaunch() {
    // 先解析宿主配置里的 API 地址，再进入页面逻辑。
    this.hydrateApiBase();
    this.checkLoginStatus();
  },

  hydrateApiBase() {
    const storedApiBase = wx.getStorageSync('api_base_override');
    if (typeof storedApiBase === 'string' && storedApiBase.trim()) {
      this.globalData.apiBase = storedApiBase.trim();
    }

    wx.getExtConfig({
      success: (res) => {
        const extConfig = res && res.extConfig ? res.extConfig : {};
        const extApiBase =
          typeof extConfig.apiBase === 'string'
            ? extConfig.apiBase
            : typeof extConfig.api_base === 'string'
              ? extConfig.api_base
              : '';

        if (extApiBase && extApiBase.trim()) {
          this.setApiBase(extApiBase.trim());
        }
      },
    });
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

  setApiBase(apiBase: string) {
    this.globalData.apiBase = apiBase;
    wx.setStorageSync('api_base_override', apiBase);
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
    wx.removeStorageSync('student_user_id');
    wx.removeStorageSync('student_id');
    wx.removeStorageSync('parent_user_id');
    wx.removeStorageSync('parent_account');
    wx.removeStorageSync('bound_child_id');
  },
});
