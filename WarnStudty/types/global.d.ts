declare function Page(pageConfig: IPageConfig): void;
declare function getApp<T = IAppOption>(): T;

interface IAppOption {
  globalData: {
    userId: string;
    userRole: string;
    childId: string;
    apiBase: string;
  };
  onLaunch?: () => void;
  checkLoginStatus?: () => void;
  setCurrentUser?: (userId: string, role: string) => void;
  clearLoginStatus?: () => void;
}

interface IPageConfig {
  data?: Record<string, any>;
  onLoad?: (options?: Record<string, string>) => void;
  onShow?: () => void;
  onHide?: () => void;
  onUnload?: () => void;
  onReady?: () => void;
  onPullDownRefresh?: () => void;
  onReachBottom?: () => void;
  onPageScroll?: (e: { scrollTop: number }) => void;
  onShareAppMessage?: () => void;
  [key: string]: any;
}

declare const wx: {
  request(options: wx.RequestOption): void;
  getStorageSync(key: string): any;
  setStorageSync(key: string, value: any): void;
  showToast(options: { title: string; icon?: string; duration?: number }): void;
  showLoading(options: { title: string }): void;
  hideLoading(): void;
  showModal(options: {
    title?: string;
    content?: string;
    confirmText?: string;
    cancelText?: string;
    success?: (res: { confirm: boolean; cancel?: boolean }) => void;
  }): void;
  login(options: { success?: (res: { code: string }) => void; fail?: () => void }): void;
  getUserProfile(options: {
    desc: string;
    success?: (res: { userInfo: any }) => void;
  }): void;
  scanCode(options: {
    onlyFromCamera?: boolean;
    success?: (res: { result: string }) => void;
  }): void;
  navigateTo(options: { url: string }): void;
  redirectTo(options: { url: string }): void;
  switchTab(options: { url: string }): void;
  reLaunch(options: { url: string }): void;
  navigateBack(options?: { delta?: number }): void;
  makePhoneCall(options: { phoneNumber: string }): void;
  getLocation(options: {
    type?: string;
    success?: (res: { latitude: number; longitude: number }) => void;
  }): void;
  chooseImage(options?: {
    count?: number;
    sourceType?: string[];
    success?: (res: { tempFilePaths: string[] }) => void;
  }): void;
  uploadFile(options: {
    url: string;
    filePath: string;
    name: string;
    formData?: any;
    success?: (res: { data: string }) => void;
  }): void;
  downloadFile(options: {
    url: string;
    success?: (res: { tempFilePath: string }) => void;
  }): void;
  playVoice(options: { filePath: string }): void;
  pauseVoice(): void;
  stopVoice(): void;
  createInnerAudioContext(): any;
  createAnimation(options: any): any;
  createSelectorQuery(): any;
  createVideoContext(id: string): any;
  createCameraContext(): any;
  getSystemInfo(options: {
    success?: (res: { model: string; pixelRatio: number; screenWidth: number; screenHeight: number; windowWidth: number; windowHeight: number; language: string; version: string; system: string; platform: string }) => void;
  }): void;
  getExtConfig(options: {
    success?: (res: { extConfig: any }) => void;
  }): void;
  getDeviceInfo(): { brand: string; model: string; system: string };
  getAppBaseInfo(): { SDKVersion: string };
  env: { VERSION: string };
  cloud: any;
  accountInfo: { appId: string };
  worklet: any;
  [key: string]: any;
};

declare const setTimeout: (callback: () => void, ms?: number) => number;
declare const clearTimeout: (id: number) => void;
declare const setInterval: (callback: () => void, ms?: number) => number;
declare const clearInterval: (id: number) => void;
declare const console: {
  log(...args: any[]): void;
  error(...args: any[]): void;
  warn(...args: any[]): void;
  info(...args: any[]): void;
  debug(...args: any[]): void;
};
