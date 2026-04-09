declare namespace wx {
  function request(options: RequestOptions): RequestTask;
  function getStorageSync(key: string): any;
  function setStorageSync(key: string, value: any): void;
  function removeStorageSync(key: string): void;
  function showToast(options: ShowToastOption): void;
  function showModal(options: ShowModalOption): void;
  function hideKeyboard(): void;
  function vibrateShort(options?: VibrateShortOption): void;
  function startRecord(options?: StartRecordOption): void;
  function stopRecord(options?: StopRecordOption): void;
  function setClipboardData(options: SetClipboardDataOption): void;
  function onKeyboardHeightChange(callback: (res: { height: number }) => void): void;
  function offKeyboardHeightChange(callback: () => void): void;

  interface RequestOptions {
    url: string;
    data?: any;
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'OPTIONS';
    header?: Record<string, string>;
    success?: (res: RequestResult) => void;
    fail?: (err: any) => void;
    complete?: () => void;
  }

  interface RequestResult {
    statusCode: number;
    data: any;
    header: Record<string, string>;
  }

  interface RequestTask {
    abort(): void;
  }

  interface ShowToastOption {
    title: string;
    icon?: 'success' | 'none' | 'error';
    duration?: number;
    mask?: boolean;
    image?: string;
  }

  interface ShowModalOption {
    title?: string;
    content?: string;
    showCancel?: boolean;
    cancelText?: string;
    cancelColor?: string;
    confirmText?: string;
    confirmColor?: string;
    success?: (res: { confirm: boolean; cancel: boolean }) => void;
    fail?: (err: any) => void;
  }

  interface VibrateShortOption {
    type?: 'light' | 'medium' | 'heavy';
    fail?: () => void;
  }

  interface StartRecordOption {
    success?: () => void;
    fail?: (err: any) => void;
    complete?: () => void;
  }

  interface StopRecordOption {
    success?: (res: { tempFilePath: string }) => void;
    fail?: (err: any) => void;
  }

  interface SetClipboardDataOption {
    data: string;
    success?: () => void;
    fail?: (err: any) => void;
  }
}

declare function getCurrentPages(): any[];
declare const getApp: () => any;