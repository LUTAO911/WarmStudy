import { parentChat, getCurrentTime, getParentId } from '../../utils/api';

interface Message {
  id: number;
  role: 'ai' | 'user';
  content: string;
  time: string;
  showTime?: boolean;
  emotion?: number;
  isStreaming?: boolean;
  canWithdraw?: boolean;
}

interface Session {
  id: string;
  title: string;
  lastMessage: string;
  time: string;
  messages: Message[];
}

interface AgentConfig {
  name: string;
  avatar: string;
  personality: string;
  emotionLevel: number;
}

interface QuickQuestion {
  id: string;
  question: string;
}

const AGENT_AVATARS: ReadonlyArray<AgentConfig & { id: string; desc: string }> = [
  { id: 'default', name: '暖暖', avatar: '/assets/avatar/pet/avatar.png', personality: '温暖贴心', emotionLevel: 2, desc: '温暖贴心' },
  { id: 'wise', name: '智慧导师', avatar: '/assets/avatar/pet/avatar.png', personality: '睿智沉稳', emotionLevel: 2, desc: '睿智沉稳' },
  { id: 'friendly', name: '知心姐姐', avatar: '/assets/avatar/pet/avatar.png', personality: '亲切友善', emotionLevel: 2, desc: '亲切友善' },
];

const EMOTION_CONFIGS: ReadonlyArray<{ level: number; label: string; color: string; icon: string }> = [
  { level: 1, label: '平静', color: '#95de64', icon: '😌' },
  { level: 2, label: '温暖', color: '#ffc53d', icon: '😊' },
  { level: 3, label: '关切', color: '#ff7a45', icon: '🤗' },
  { level: 4, label: '专注', color: '#69c0ff', icon: '🧐' },
  { level: 5, label: '热情', color: '#ff85c0', icon: '💖' },
] as const;

const QUICK_QUESTIONS: QuickQuestion[] = [
  { id: 'q1', question: '孩子学习压力大怎么办？' },
  { id: 'q2', question: '如何和孩子有效沟通？' },
  { id: 'q3', question: '孩子沉迷手机怎么办？' },
  { id: 'q4', question: '如何培养孩子的好习惯？' },
] as const;

const STORAGE_KEYS = {
  sessions: 'parent_sessions',
  agentConfig: 'parent_agent_config',
} as const;

interface ChatPageData {
  inputText: string;
  scrollTop: number;
  loading: boolean;
  messages: Message[];
  inputMode: 'text' | 'voice';
  voiceState: 'idle' | 'recording' | 'transcribing';
  keyboardHeight: number;
  inputAreaHeight: number;
  showToolbox: boolean;
  showAgentSettings: boolean;
  showSessionList: boolean;
  showAvatarPicker: boolean;
  showContextMenu: boolean;
  showContextPanel: boolean;
  contextMenuFor: number | null;
  contextMenuPos: { x: number; y: number };
  currentSessionId: string;
  sessions: Session[];
  agent: AgentConfig;
  emotionDisplay: { level: number; label: string; color: string; icon: string };
  streamingContent: string;
  abortController: AbortController | null;
  editingMessageId: number | null;
  editText: string;
}

Page({
  data: {
    inputText: '',
    scrollTop: 0,
    loading: false,
    messages: [] as Message[],
    inputMode: 'text' as const,
    voiceState: 'idle' as const,
    keyboardHeight: 0,
    inputAreaHeight: 120,
    showToolbox: false,
    showAgentSettings: false,
    showSessionList: false,
    showAvatarPicker: false,
    showContextMenu: false,
    showContextPanel: false,
    contextMenuFor: null,
    contextMenuPos: { x: 0, y: 0 },
    currentSessionId: '',
    sessions: [] as Session[],
    agent: {
      name: '暖暖',
      avatar: '/assets/avatar/pet/avatar.png',
      personality: '温暖贴心',
      emotionLevel: 2,
    } as AgentConfig,
    emotionDisplay: EMOTION_CONFIGS[1],
    streamingContent: '',
    abortController: null,
    editingMessageId: null,
    editText: '',
  } as ChatPageData,

  onLoad() {
    this.loadSessions();
    this.loadAgentConfig();
    wx.onKeyboardHeightChange((res) => {
      this.setData({ keyboardHeight: res.height });
    });
  },

  onUnload() {
    try { wx.offKeyboardHeightChange(() => {}); } catch {}
    if (this.data.abortController) {
      this.data.abortController.abort();
    }
  },

  loadSessions() {
    const sessions = wx.getStorageSync(STORAGE_KEYS.sessions) as Session[] || [];
    if (sessions.length > 0) {
      const currentSession = sessions[0];
      this.setData({
        sessions,
        currentSessionId: currentSession.id,
        messages: currentSession.messages
      });
    } else {
      this.createNewSession();
    }
  },

  loadAgentConfig() {
    const agent = wx.getStorageSync(STORAGE_KEYS.agentConfig) as AgentConfig | undefined;
    if (agent) {
      const emotionDisplay = EMOTION_CONFIGS.find(e => e.level === agent.emotionLevel) || EMOTION_CONFIGS[1];
      this.setData({ agent, emotionDisplay });
    }
  },

  createNewSession() {
    const sessionId = `session_${Date.now()}`;
    const greeting: Message = {
      id: Date.now(),
      role: 'ai',
      content: '您好！我是WarmStudy的AI家庭教育助手 🌟\n\n有什么关于孩子学习、心理或亲子沟通的问题，都可以问我哦~',
      time: getCurrentTime(),
      showTime: true,
      emotion: 2,
    };

    const newSession: Session = {
      id: sessionId,
      title: '新对话',
      lastMessage: greeting.content.substring(0, 20) + '...',
      time: getCurrentTime(),
      messages: [greeting],
    };

    const sessions = [newSession, ...this.data.sessions];
    this.setData({
      sessions,
      currentSessionId: sessionId,
      messages: [greeting]
    });
    this.saveSessions();
  },

  saveSessions() {
    const { sessions, currentSessionId, messages } = this.data;
    const sessionIndex = sessions.findIndex(s => s.id === currentSessionId);
    if (sessionIndex >= 0) {
      sessions[sessionIndex].messages = messages;
      if (messages.length > 1) {
        sessions[sessionIndex].title = messages[1].content.substring(0, 15);
        sessions[sessionIndex].lastMessage = messages[messages.length - 1].content.substring(0, 30);
      }
      sessions[sessionIndex].time = getCurrentTime();
    }
    wx.setStorageSync(STORAGE_KEYS.sessions, sessions);
  },

  onTextInput(e: any) {
    this.setData({ inputText: e.detail.value });
    this.updateInputHeight(e.detail.value);
  },

  updateInputHeight(text: string) {
    const lines = (text.match(/\n/g) || []).length + 1;
    const baseH = 100;
    const lineH = 40;
    const maxH = 200;
    const h = Math.min(baseH + (lines - 1) * lineH, maxH);
    this.setData({ inputAreaHeight: h });
  },

  onTextareaFocus() {
    this.scrollToBottom();
  },

  onToggleInputMode() {
    const next = this.data.inputMode === 'text' ? 'voice' : 'text';
    this.setData({ inputMode: next, showToolbox: false });
    if (next === 'voice') wx.hideKeyboard();
  },

  onShowToolbox() {
    this.setData({ showToolbox: true });
  },

  onCloseToolbox() {
    this.setData({ showToolbox: false });
  },

  onVoiceStart() {
    if (this.data.inputMode !== 'voice') return;
    this.setData({ voiceState: 'recording' });
    wx.vibrateShort({ type: 'medium' });
    wx.startRecord({
      success: () => {},
      fail: () => {
        this.setData({ voiceState: 'idle' });
        wx.showToast({ title: '录音失败', icon: 'none' });
      },
    });
  },

  onVoiceEnd() {
    if (this.data.voiceState !== 'recording') return;
    wx.stopRecord();
    this.setData({ voiceState: 'transcribing' });
    
    setTimeout(() => {
      this.setData({ voiceState: 'idle' });
      const mockTexts = [
        '孩子最近学习压力很大',
        '怎么和孩子有效沟通',
        '孩子沉迷手机怎么办',
      ];
      const text = mockTexts[Math.floor(Math.random() * mockTexts.length)];
      this.addUserMessage(text + ' 🎤');
      this.callAI(text);
    }, 1000);
  },

  onSend() {
    const text = this.data.inputText.trim();
    if (!text || this.data.loading) return;
    
    if (this.data.editingMessageId) {
      this.confirmEdit();
      return;
    }
    
    this.addUserMessage(text);
    this.setData({ inputText: '', inputAreaHeight: 120 });
    this.callAI(text);
  },

  addUserMessage(content: string) {
    const now = Date.now();
    const lastMsg = this.data.messages[this.data.messages.length - 1];
    const showTime = !lastMsg || this.shouldShowTime(lastMsg.time, getCurrentTime());
    
    const msg: Message = {
      id: now,
      role: 'user',
      content,
      time: getCurrentTime(),
      showTime,
      canWithdraw: true,
    };
    
    const messages = [...this.data.messages, msg];
    this.setData({ messages, loading: true });
    this.saveSessions();
    this.scrollToBottom();
  },

  addAIMessage(content: string, emotion: number = 2) {
    const now = Date.now();
    const lastMsg = this.data.messages[this.data.messages.length - 1];
    const showTime = !lastMsg || this.shouldShowTime(lastMsg.time, getCurrentTime());
    
    const msg: Message = {
      id: now,
      role: 'ai',
      content,
      time: getCurrentTime(),
      showTime,
      emotion,
    };
    
    const messages = [...this.data.messages, msg];
    const emotionDisplay = EMOTION_CONFIGS.find(e => e.level === emotion) || EMOTION_CONFIGS[1];
    
    this.setData({ 
      messages, 
      loading: false,
      streamingContent: '',
      emotionDisplay
    });
    this.saveSessions();
    this.scrollToBottom();
  },

  shouldShowTime(lastTime: string, currentTime: string): boolean {
    const lastParts = lastTime.split(':');
    const currentParts = currentTime.split(':');
    if (lastParts.length !== 2 || currentParts.length !== 2) return false;
    
    const lastMinutes = parseInt(lastParts[0]) * 60 + parseInt(lastParts[1]);
    const currentMinutes = parseInt(currentParts[0]) * 60 + parseInt(currentParts[1]);
    
    return currentMinutes - lastMinutes >= 5;
  },

  async callAI(text: string) {
    const userId = getParentId();
    this.setData({ streamingContent: '', loading: true });
    
    try {
      const res: any = await parentChat(userId, text);
      const emotion = this.detectEmotion(res.response || '');
      this.addAIMessage(res.response || '抱歉，AI助手现在比较忙，请稍后再试 🙏', emotion);
    } catch (err) {
      this.addAIMessage(this.fallbackResponse(text), 2);
    }
  },

  detectEmotion(text: string): number {
    if (text.includes('😊') || text.includes('很高兴') || text.includes('太棒了')) return 5;
    if (text.includes('🤗') || text.includes('理解') || text.includes('支持')) return 3;
    if (text.includes('🧐') || text.includes('建议') || text.includes('可以尝试')) return 4;
    if (text.includes('😌') || text.includes('放心') || text.includes('正常')) return 1;
    return 2;
  },

  onStopStreaming() {
    if (this.data.abortController) {
      this.data.abortController.abort();
      this.setData({ 
        loading: false,
        streamingContent: '',
        abortController: null
      });
      
      if (this.data.streamingContent) {
        this.addAIMessage(this.data.streamingContent + ' [已中断]', 2);
      }
    }
  },

  fallbackResponse(text: string): string {
    const q = text.toLowerCase();
    if (q.includes('压力') || q.includes('考试') || q.includes('学习')) {
      return '孩子学习压力大时，建议先关注情绪而非成绩。可以和孩子聊聊"今天有什么开心的事吗"，建立情感连接比直接谈学习更有效。';
    }
    if (q.includes('手机') || q.includes('游戏') || q.includes('网瘾')) {
      return '关于孩子沉迷手机，建议不要直接禁止，而是和孩子一起制定规则，比如完成学习任务后可以获得一定的游戏时间。关键是让孩子参与规则的制定，而不是单方面要求。';
    }
    if (q.includes('沟通') || q.includes('对话') || q.includes('青春期')) {
      return '青春期孩子渴望被理解和尊重。试试"我注意到..."开头，而不是"你怎么总是..."。先倾听孩子的想法，再表达你的担忧，会更容易沟通。';
    }
    return '谢谢您的提问！我会尽力给出有用的建议 😊';
  },

  onMessageLongPress(e: any) {
    const { id, role } = e.currentTarget.dataset;
    const message = this.data.messages.find(m => m.id === id);
    if (!message) return;
    
    const touch = e.touches[0];
    this.setData({
      showContextMenu: true,
      contextMenuFor: id,
      contextMenuPos: { x: touch.clientX, y: touch.clientY - 100 }
    });
  },

  onCopyMessage() {
    const message = this.data.messages.find(m => m.id === this.data.contextMenuFor);
    if (message) {
      wx.setClipboardData({
        data: message.content,
        success: () => wx.showToast({ title: '已复制', icon: 'success' })
      });
    }
    this.closeContextMenu();
  },

  onWithdrawMessage() {
    const { contextMenuFor, messages } = this.data;
    const index = messages.findIndex(m => m.id === contextMenuFor);
    if (index >= 0 && messages[index].role === 'user') {
      const editText = messages[index].content;
      messages.splice(index, 1);
      
      if (index < messages.length && messages[index].role === 'ai') {
        messages.splice(index, 1);
      }
      
      this.setData({ 
        messages, 
        editingMessageId: contextMenuFor,
        editText,
        inputText: editText
      });
      this.updateInputHeight(editText);
      this.saveSessions();
    }
    this.closeContextMenu();
  },

  onEditMessage() {
    const message = this.data.messages.find(m => m.id === this.data.contextMenuFor);
    if (message && message.role === 'user') {
      this.setData({
        editingMessageId: message.id,
        editText: message.content,
        inputText: message.content
      });
      this.updateInputHeight(message.content);
    }
    this.closeContextMenu();
  },

  confirmEdit() {
    const { editingMessageId, inputText, messages } = this.data;
    const index = messages.findIndex(m => m.id === editingMessageId);
    
    if (index >= 0 && inputText.trim()) {
      messages[index].content = inputText.trim();
      messages[index].time = getCurrentTime();
      
      if (index + 1 < messages.length && messages[index + 1].role === 'ai') {
        messages.splice(index + 1, 1);
      }
      
      this.setData({ 
        messages, 
        editingMessageId: null, 
        editText: '',
        inputText: '',
        inputAreaHeight: 120
      });
      this.saveSessions();
      this.callAI(inputText.trim());
    }
  },

  cancelEdit() {
    this.setData({ 
      editingMessageId: null, 
      editText: '',
      inputText: '',
      inputAreaHeight: 120
    });
  },

  closeContextMenu() {
    this.setData({ showContextMenu: false, contextMenuFor: null });
  },

  onShowSessionList() {
    this.setData({ showSessionList: true });
  },

  onCloseSessionList() {
    this.setData({ showSessionList: false });
  },

  onSelectSession(e: any) {
    const { id } = e.currentTarget.dataset;
    const session = this.data.sessions.find(s => s.id === id);
    if (session) {
      this.setData({ 
        currentSessionId: id,
        messages: session.messages,
        showSessionList: false
      });
    }
  },

  onNewSession() {
    this.createNewSession();
    this.setData({ showSessionList: false });
  },

  onDeleteSession(e: any) {
    const { id } = e.currentTarget.dataset;
    const sessions = this.data.sessions.filter(s => s.id !== id);
    
    if (id === this.data.currentSessionId) {
      if (sessions.length > 0) {
        this.setData({ 
          sessions,
          currentSessionId: sessions[0].id,
          messages: sessions[0].messages
        });
      } else {
        this.createNewSession();
        return;
      }
    } else {
      this.setData({ sessions });
    }
    
    this.saveSessions();
  },

  onShowAgentSettings() {
    this.setData({ showToolbox: false, showAgentSettings: true });
  },

  onCloseAgentSettings() {
    this.setData({ showAgentSettings: false });
  },

  onShowAvatarPicker() {
    this.setData({ showAvatarPicker: true });
  },

  onCloseAvatarPicker() {
    this.setData({ showAvatarPicker: false });
  },

  onSelectAvatar(e: any) {
    const { id } = e.currentTarget.dataset;
    const avatar = AGENT_AVATARS.find(a => a.id === id);
    if (avatar) {
      const agent: AgentConfig = {
        ...this.data.agent,
        name: avatar.name,
        avatar: avatar.avatar,
        personality: avatar.desc
      };
      this.setData({ agent, showAvatarPicker: false });
      wx.setStorageSync(STORAGE_KEYS.agentConfig, agent);
    }
  },

  onEmotionChange(e: any) {
    const level = parseInt(e.detail.value) + 1;
    const emotionDisplay = EMOTION_CONFIGS.find(em => em.level === level) || EMOTION_CONFIGS[1];
    const agent: AgentConfig = { ...this.data.agent, emotionLevel: level };
    this.setData({ agent, emotionDisplay });
    wx.setStorageSync(STORAGE_KEYS.agentConfig, agent);
  },

  onQuickQuestion(e: any) {
    const question = e.currentTarget.dataset.question;
    this.setData({ inputText: question, showToolbox: false });
  },

  onClearHistory() {
    wx.showModal({
      title: '清除历史对话',
      content: '确定清除所有聊天记录？',
      confirmText: '清除',
      cancelText: '取消',
      confirmColor: '#ff4d4f',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync(STORAGE_KEYS.sessions);
          this.setData({ sessions: [], showAgentSettings: false });
          this.createNewSession();
          wx.showToast({ title: '已清除', icon: 'success' });
        }
      },
    });
  },

  onShowContext() {
    this.setData({ showToolbox: false, showContextPanel: true });
  },

  onCloseContext() {
    this.setData({ showContextPanel: false });
  },

  onAboutAgent() {
    wx.showModal({
      title: '关于AI助手',
      content: `${this.data.agent.name} · AI家庭教育助手\n\n基于通义千问大模型，专注为家长提供科学的家庭教育建议和亲子沟通指导。\n\n遇到严重心理或教育问题，请咨询专业医生或心理咨询师。`,
      showCancel: false,
      confirmText: '我知道了',
    });
  },

  scrollToBottom() {
    setTimeout(() => {
      this.setData({ scrollTop: Date.now() });
    }, 50);
  },
});
