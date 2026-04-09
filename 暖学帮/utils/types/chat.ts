/**
 * 聊天相关类型定义
 * 供家长端和学生端共享使用
 */

/** 消息类型 */
export interface Message {
  id: number;
  role: 'ai' | 'user';
  content: string;
  time: string;
  showTime?: boolean;
  emotion?: number;
  isStreaming?: boolean;
  canWithdraw?: boolean;
}

/** 会话类型 */
export interface Session {
  id: string;
  title: string;
  lastMessage: string;
  time: string;
  messages: Message[];
}

/** AI助手配置 */
export interface AgentConfig {
  name: string;
  avatar: string;
  personality: string;
  emotionLevel: number;
}

/** 情绪配置 */
export interface EmotionConfig {
  level: number;
  label: string;
  color: string;
  icon: string;
}

/** AI角色头像 */
export interface AgentAvatar {
  id: string;
  name: string;
  avatar: string;
  desc: string;
}

/** 存储键名常量 */
export const STORAGE_KEYS = {
  sessions: 'sessions',
  agentConfig: 'agent_config',
  childInfo: 'child_info',
} as const;

/** 默认情绪配置 */
export const DEFAULT_EMOTION_CONFIG: EmotionConfig = {
  level: 2,
  label: '温暖',
  color: '#ffc53d',
  icon: '😊',
};

/** 情绪配置列表 */
export const EMOTION_CONFIGS: readonly EmotionConfig[] = [
  { level: 1, label: '平静', color: '#95de64', icon: '😌' },
  { level: 2, label: '温暖', color: '#ffc53d', icon: '😊' },
  { level: 3, label: '关切', color: '#ff7a45', icon: '🤗' },
  { level: 4, label: '专注', color: '#69c0ff', icon: '🧐' },
  { level: 5, label: '热情', color: '#ff85c0', icon: '💖' },
] as const;

/** AI头像列表 */
export const AGENT_AVATARS: readonly AgentAvatar[] = [
  { id: 'default', name: '暖暖', avatar: '/assets/avatar/pet/avatar.png', desc: '温暖贴心' },
  { id: 'wise', name: '智慧导师', avatar: '/assets/avatar/pet/avatar.png', desc: '睿智沉稳' },
  { id: 'friendly', name: '知心姐姐', avatar: '/assets/avatar/pet/avatar.png', desc: '亲切友善' },
] as const;

/**
 * 格式化时间戳
 */
export function formatTime(date: Date = new Date()): string {
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

/**
 * 判断是否需要显示时间戳
 */
export function shouldShowTime(lastTime: string, currentTime: string, interval: number = 5): boolean {
  const lastParts = lastTime.split(':');
  const currentParts = currentTime.split(':');
  if (lastParts.length !== 2 || currentParts.length !== 2) return false;

  const lastMinutes = parseInt(lastParts[0]) * 60 + parseInt(lastParts[1]);
  const currentMinutes = parseInt(currentParts[0]) * 60 + parseInt(currentParts[1]);

  return currentMinutes - lastMinutes >= interval;
}

/**
 * 检测文本中的情绪等级
 */
export function detectEmotion(text: string): number {
  if (text.includes('😊') || text.includes('很高兴') || text.includes('太棒了')) return 5;
  if (text.includes('🤗') || text.includes('理解') || text.includes('支持')) return 3;
  if (text.includes('🧐') || text.includes('建议') || text.includes('可以尝试')) return 4;
  if (text.includes('😌') || text.includes('放心') || text.includes('正常')) return 1;
  return 2;
}

/**
 * 获取情绪配置
 */
export function getEmotionConfig(level: number): EmotionConfig {
  return EMOTION_CONFIGS.find(e => e.level === level) || DEFAULT_EMOTION_CONFIG;
}

/**
 * 根据角色获取存储键前缀
 */
export function getStorageKeys(role: 'student' | 'parent'): typeof STORAGE_KEYS {
  const prefix = role === 'student' ? 'student' : 'parent';
  return {
    sessions: `${prefix}_sessions`,
    agentConfig: `${prefix}_agent_config`,
    childInfo: role === 'student' ? 'child_info' : `${prefix}_child_info`,
  } as const;
}