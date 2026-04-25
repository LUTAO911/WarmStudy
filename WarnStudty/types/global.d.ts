declare function Page(pageConfig: IPageConfig): void;
declare function App<T = IAppOption>(appConfig: T): void;
declare function getApp<T = IAppOption>(): T;
declare function require(path: string): any;

declare namespace wx {
  type RequestOption = any;
}

interface IAppOption {
  globalData: {
    userId: string;
    userRole: string;
    childId: string;
    apiBase: string;
  };
  onLaunch?: () => void;
  hydrateApiBase?: () => void;
  checkLoginStatus?: () => void;
  setCurrentUser?: (userId: string, role: string) => void;
  setApiBase?: (apiBase: string) => void;
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

declare namespace wx {
  interface RequestResponse {
    statusCode: number;
    data: any;
    header?: Record<string, string>;
  }

  interface RequestOption {
    url: string;
    data?: any;
    method?: string;
    header?: Record<string, string>;
    timeout?: number;
    success?: (res: RequestResponse) => void;
    fail?: (err: any) => void;
  }

  interface NavigateOption {
    url: string;
    success?: () => void;
    fail?: (err: any) => void;
    complete?: () => void;
  }
}

declare const wx: {
  request(options: wx.RequestOption): void;
  getStorageSync(key: string): any;
  setStorageSync(key: string, value: any): void;
  removeStorageSync(key: string): void;
  showToast(options: { title: string; icon?: string; duration?: number }): void;
  showLoading(options: { title: string; mask?: boolean }): void;
  hideLoading(): void;
  showModal(options: {
    title?: string;
    content?: string;
    confirmText?: string;
    cancelText?: string;
    showCancel?: boolean;
    editable?: boolean;
    placeholderText?: string;
    success?: (res: { confirm: boolean; cancel?: boolean; content?: string }) => void;
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
  navigateTo(options: { url: string; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void;
  redirectTo(options: { url: string; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void;
  switchTab(options: { url: string; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void;
  reLaunch(options: { url: string; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void;
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

declare class AbortController {
  signal: any;
  abort(): void;
}

declare const setTimeout: (callback: (...args: any[]) => void, ms?: number, ...args: any[]) => number;
declare const clearTimeout: (id: number) => void;
declare const setInterval: (callback: (...args: any[]) => void, ms?: number, ...args: any[]) => number;
declare const clearInterval: (id: number) => void;
declare const console: {
  log(...args: any[]): void;
  error(...args: any[]): void;
  warn(...args: any[]): void;
  info(...args: any[]): void;
  debug(...args: any[]): void;
};
