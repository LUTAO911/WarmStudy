/**
 * WarmStudy - Unified API Request Tool
 * Backend: http://192.168.0.68:8000
 */

const API_BASE = 'http://localhost:8000';

// 请求封装
function request<T = any>(url: string, data?: any, method: string = 'POST'): Promise<T> {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}${url}`,
      data,
      method,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T);
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail: (err) => reject(err),
    });
  });
}

// ===== 通用响应类型 =====
interface ApiResponse {
  success: boolean;
  [key: string]: any;
}

// ===== 登录相关 =====

/**
 * 手机号登录（支持同一手机号不同角色）
 * POST /api/auth/login/phone
 */
export function loginByPhone(phone: string, code: string, role: 'student' | 'parent'): Promise<{
  success: boolean;
  message?: string;
  data?: {
    user_id: string;
    name: string;
    phone: string;
    role: string;
    token: string;
  };
}> {
  return request('/api/auth/login/phone', { phone, code, role });
}

/**
 * 微信登录（支持同一手机号不同角色）
 * POST /api/auth/login/wechat
 */
export function loginByWechat(wxCode: string, role: 'student' | 'parent'): Promise<{
  success: boolean;
  message?: string;
  data?: {
    user_id: string;
    name: string;
    phone: string;
    role: string;
    token: string;
  };
}> {
  return request('/api/auth/login/wechat', { wx_code: wxCode, role });
}

/**
 * 发送验证码
 * POST /api/auth/send-code
 */
export function sendVerifyCode(phone: string): Promise<{
  success: boolean;
  message?: string;
}> {
  return request('/api/auth/send-code', { phone });
}

// ===== 学生端 API =====

/**
 * AI 心理师对话
 * POST /api/student/chat
 */
export function studentChat(userId: string, message: string): Promise<{ response: string; ai_name: string }> {
  return request<{ success: boolean; response: string; ai_name: string }>(
    '/api/student/chat',
    { user_id: userId, message }
  );
}

/**
 * 提交每日打卡
 * POST /api/student/checkin
 */
export function submitCheckin(userId: string, data: {
  emotion?: number;
  sleep?: number;
  study?: number;
  social?: number;
  note?: string;
}): Promise<{ success: boolean; message: string }> {
  return request('/api/student/checkin', { user_id: userId, ...data });
}

/**
 * 提交心理测评
 * POST /api/student/psych/test
 */
export function submitPsychTest(
  userId: string,
  answers: number[],
  testType: string = 'weekly'
): Promise<ApiResponse> {
  return request('/api/student/psych/test', {
    user_id: userId,
    answers,
    test_type: testType,
  });
}

/**
 * 获取心理状态
 * GET /api/student/psych/status/{user_id}
 */
export function getPsychStatus(userId: string): Promise<any> {
  return request(`/api/student/psych/status/${userId}`, undefined, 'GET');
}

/**
 * 获取历史打卡
 * GET /api/student/checkin/{user_id}
 */
export function getCheckinHistory(userId: string, days: number = 7): Promise<any> {
  return request(`/api/student/checkin/${userId}?days=${days}`, undefined, 'GET');
}

// ===== 家长端 API =====

/**
 * AI 家庭教育助手对话
 * POST /api/parent/chat
 */
export function parentChat(userId: string, message: string): Promise<{ response: string }> {
  return request<{ success: boolean; response: string }>(
    '/api/parent/chat',
    { user_id: userId, message }
  );
}

/**
 * 获取孩子综合状态
 * GET /api/parent/child/{child_id}/status
 */
export function getChildStatus(childId: string): Promise<any> {
  return request(`/api/parent/child/${childId}/status`, undefined, 'GET');
}

/**
 * 获取孩子打卡记录
 * GET /api/parent/child/{child_id}/checkins
 */
export function getChildCheckins(childId: string, days: number = 7): Promise<any> {
  return request(`/api/parent/child/${childId}/checkins?days=${days}`, undefined, 'GET');
}

/**
 * 获取 AI 每日建议
 * GET /api/parent/child/{child_id}/ai_advice
 */
export function getDailyAdvice(childId: string): Promise<{ advice: string; focus: string }> {
  return request(`/api/parent/child/${childId}/ai_advice`, undefined, 'GET');
}

/**
 * 录入孩子成绩
 * POST /api/parent/child/grade
 */
export function submitGrade(userId: string, subject: string, score: number, examDate: string): Promise<any> {
  return request('/api/parent/child/grade', {
    user_id: userId,
    subject,
    score,
    exam_date: examDate,
  });
}

/**
 * 家长手机号登录
 * POST /api/parent/login
 */
export function parentLogin(phone: string): Promise<{
  success: boolean;
  account: { id: number; phone: string; name: string; qr_token: string };
  bound_children: string[];
}> {
  return request('/api/parent/login', { phone });
}

/**
 * 批量获取孩子档案（家长端展示用）
 */
export function getChildrenProfiles(childIds: string[]): Promise<{
  success: boolean;
  profiles: { user_id: string; name: string; grade: string }[];
}> {
  return request('/api/parent/children/profiles', { child_ids: childIds.join(',') });
}

/**
 * 获取家长二维码内容
 */
export function getParentQRToken(parentId: number): Promise<{
  success: boolean;
  token: string;
  qr_url: string;
}> {
  return request('/api/parent/qr_token', { parent_id: parentId });
}

/**
 * 绑定孩子（家长主动添加）
 */
export function bindChild(parentId: string, childId: string): Promise<any> {
  return request('/api/parent/child/bind', { parent_id: parentId, child_id: childId });
}

// ===== 工具函数 =====

/** 获取当前时间字符串 HH:MM */
export function getCurrentTime(): string {
  const now = new Date();
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
}

/** 获取当前日期 YYYY-MM-DD */
export function getCurrentDate(): string {
  const now = new Date();
  return `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')}`;
}

/** 获取本地存储的 userId */
export function getUserId(role: 'student' | 'parent' = 'student'): string {
  const key = role === 'student' ? 'student_user_id' : 'parent_user_id';
  return wx.getStorageSync(key) || (role === 'student' ? 'student_001' : 'parent_001');
}

/** 获取当前登录用户的ID */
export function getCurrentUserId(): string {
  return wx.getStorageSync('user_id') || '';
}

/** 获取当前用户角色 */
export function getCurrentRole(): 'student' | 'parent' | '' {
  return wx.getStorageSync('user_role') || '';
}

/** 获取本地存储的家长 ID */
export function getParentId(): string {
  return wx.getStorageSync('parent_user_id') || 'parent_001';
}

/** 获取绑定的孩子 ID */
export function getChildId(): string {
  return wx.getStorageSync('bound_child_id') || 'student_001';
}

// ===== 扫码绑定 =====

/**
 * 用扫码得到的 token 绑定家长
 */
export function bindParentByToken(token: string, childId: string): Promise<{ success: boolean; error?: string; parent_name?: string }> {
  return request('/api/child/bind', { token, child_id: childId });
}

// ===== 测评报告 =====

/** 获取孩子测评报告列表 */
export function getChildPsychReports(childId: string, limit = 5): Promise<{
  success: boolean;
  reports: {
    id: number;
    scale_id: string;
    level: string;
    normalized: number;
    summary: string;
    advice: string;
    date: string;
  }[];
}> {
  return request(`/api/parent/child/${childId}/psych_reports?limit=${limit}`);
}

/** 获取孩子最新心理状态 */
export function getChildPsychStatus(childId: string): Promise<any> {
  return request(`/api/parent/child/${childId}/psych/latest`);
}

// ===== 家长预警 =====

export type AlertType = 'emotion_drop' | 'no_checkin' | 'test_concerning' | 'chat_silence';

export interface ParentAlert {
  id: number;
  child_id: string;
  child_name: string;
  alert_type: AlertType;
  title: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

/** 获取预警列表 */
export function getParentAlerts(parentId: string, limit = 20, offset = 0): Promise<{
  success: boolean;
  alerts: ParentAlert[];
  unread_count: number;
}> {
  return request(`/api/parent/alerts?parent_id=${parentId}&limit=${limit}&offset=${offset}`, undefined, 'GET');
}

/** 标记单条已读 */
export function markAlertRead(alertId: number, parentId: string): Promise<{ success: boolean }> {
  return request(`/api/parent/alerts/${alertId}/read`, { parent_id: parentId });
}

/** 全部标为已读 */
export function markAllAlertsRead(parentId: string): Promise<{ success: boolean; marked_count: number }> {
  return request('/api/parent/alerts/read_all', { parent_id: parentId });
}

/** 获取测评报告详情（家长端） */
export function getChildPsychReportDetail(reportId: string): Promise<{
  success: boolean;
  report?: {
    id: number;
    scale_id: string;
    level: string;
    normalized: number;
    summary: string;
    advice: string;
    key_findings: string[];
    dimensions: { name: string; score: number; max: number; level: string; level_label: string; pct: number }[];
    parent_advice: string;
    date: string;
    child_name: string;
    child_grade: string;
  };
}> {
  return request(`/api/parent/report/${reportId}`);
}
