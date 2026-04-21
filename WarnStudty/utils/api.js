/**
 * WarmStudy - Unified API Request Tool
 * Backend: http://localhost:8000
 */

function getApiBase() {
  const app = typeof getApp === 'function' ? getApp() : null;
  return (app && app.globalData && app.globalData.apiBase) || 'http://localhost:8000';
}

// 请求封装
function request(url, data, method = 'POST') {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getApiBase()}${url}`,
      data,
      method,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail: (err) => reject(err),
    });
  });
}

// ===== 登录相关 =====

/**
 * 手机号登录（支持同一手机号不同角色）
 */
function loginByPhone(phone, code, role) {
  return request('/api/auth/login/phone', { phone, code, role });
}

/**
 * 微信登录（支持同一手机号不同角色）
 */
function loginByWechat(wxCode, role) {
  return request('/api/auth/login/wechat', { wx_code: wxCode, role });
}

/**
 * 发送验证码
 */
function sendVerifyCode(phone) {
  return request('/api/auth/send-code', { phone });
}

// ===== 学生端 API =====

/**
 * AI 心理师对话
 */
function studentChat(userId, message) {
  return request('/api/student/chat', { user_id: userId, message });
}

/**
 * 提交每日打卡
 */
function submitCheckin(userId, data) {
  return request('/api/student/checkin', { user_id: userId, ...data });
}

/**
 * 提交心理测评
 */
function submitPsychTest(userId, answers, testType = 'weekly') {
  return request('/api/student/psych/test', {
    user_id: userId,
    answers,
    test_type: testType,
  });
}

/**
 * 获取心理状态
 */
function getPsychStatus(userId) {
  return request(`/api/student/psych/status/${userId}`, undefined, 'GET');
}

/**
 * 获取历史打卡
 */
function getCheckinHistory(userId, days = 7) {
  return request(`/api/student/checkin/${userId}?days=${days}`, undefined, 'GET');
}

// ===== 家长端 API =====

/**
 * AI 家庭教育助手对话
 */
function parentChat(userId, message) {
  return request('/api/parent/chat', { user_id: userId, message });
}

/**
 * 获取孩子综合状态
 */
function getChildStatus(childId) {
  return request(`/api/parent/child/${childId}/status`, undefined, 'GET');
}

/**
 * 获取孩子打卡记录
 */
function getChildCheckins(childId, days = 7) {
  return request(`/api/parent/child/${childId}/checkins?days=${days}`, undefined, 'GET');
}

/**
 * 获取 AI 每日建议
 */
function getDailyAdvice(childId) {
  return request(`/api/parent/child/${childId}/ai_advice`, undefined, 'GET');
}

/**
 * 录入孩子成绩
 */
function submitGrade(userId, subject, score, examDate) {
  return request('/api/parent/child/grade', {
    user_id: userId,
    subject,
    score,
    exam_date: examDate,
  });
}

/**
 * 家长手机号登录
 */
function parentLogin(phone) {
  return request('/api/parent/login', { phone });
}

/**
 * 批量获取孩子档案（家长端展示用）
 */
function getChildrenProfiles(childIds) {
  return request('/api/parent/children/profiles', { child_ids: childIds.join(',') });
}

/**
 * 获取家长二维码内容
 */
function getParentQRToken(parentId) {
  return request('/api/parent/qr_token', { parent_id: parentId });
}

/**
 * 绑定孩子（家长主动添加）
 */
function bindChild(parentId, childId) {
  return request('/api/parent/child/bind', { parent_id: parentId, child_id: childId });
}

// ===== 工具函数 =====

/** 获取当前时间字符串 HH:MM */
function getCurrentTime() {
  const now = new Date();
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
}

/** 获取当前日期 YYYY-MM-DD */
function getCurrentDate() {
  const now = new Date();
  return `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')}`;
}

/** 获取本地存储的 userId */
function getUserId(role = 'student') {
  const key = role === 'student' ? 'student_user_id' : 'parent_user_id';
  return wx.getStorageSync(key) || (role === 'student' ? 'student_001' : 'parent_001');
}

/** 获取当前登录用户的ID */
function getCurrentUserId() {
  return wx.getStorageSync('user_id') || '';
}

/** 获取当前用户角色 */
function getCurrentRole() {
  return wx.getStorageSync('user_role') || '';
}

/** 获取本地存储的家长 ID */
function getParentId() {
  return wx.getStorageSync('parent_user_id') || 'parent_001';
}

/** 获取绑定的孩子 ID */
function getChildId() {
  return wx.getStorageSync('bound_child_id') || 'student_001';
}

// ===== 扫码绑定 =====

/**
 * 用扫码得到的 token 绑定家长
 */
function bindParentByToken(token, childId) {
  return request('/api/child/bind', { token, child_id: childId });
}

// ===== 测评报告 =====

/** 获取孩子测评报告列表 */
function getChildPsychReports(childId, limit = 5) {
  return request(`/api/parent/child/${childId}/psych_reports?limit=${limit}`);
}

/** 获取孩子最新心理状态 */
function getChildPsychStatus(childId) {
  return request(`/api/parent/child/${childId}/psych/latest`);
}

// ===== 家长预警 =====

/** 获取预警列表 */
function getParentAlerts(parentId, limit = 20, offset = 0) {
  return request(`/api/parent/alerts?parent_id=${parentId}&limit=${limit}&offset=${offset}`, undefined, 'GET');
}

/** 标记单条已读 */
function markAlertRead(alertId, parentId) {
  return request(`/api/parent/alerts/${alertId}/read`, { parent_id: parentId });
}

/** 全部标为已读 */
function markAllAlertsRead(parentId) {
  return request('/api/parent/alerts/read_all', { parent_id: parentId });
}

/** 获取测评报告详情（家长端） */
function getChildPsychReportDetail(reportId) {
  return request(`/api/parent/report/${reportId}`);
}

// 导出所有函数
module.exports = {
  loginByPhone,
  loginByWechat,
  sendVerifyCode,
  studentChat,
  submitCheckin,
  submitPsychTest,
  getPsychStatus,
  getCheckinHistory,
  parentChat,
  getChildStatus,
  getChildCheckins,
  getDailyAdvice,
  submitGrade,
  parentLogin,
  getChildrenProfiles,
  getParentQRToken,
  bindChild,
  getCurrentTime,
  getCurrentDate,
  getUserId,
  getCurrentUserId,
  getCurrentRole,
  getParentId,
  getChildId,
  bindParentByToken,
  getChildPsychReports,
  getChildPsychStatus,
  getParentAlerts,
  markAlertRead,
  markAllAlertsRead,
  getChildPsychReportDetail,
};
