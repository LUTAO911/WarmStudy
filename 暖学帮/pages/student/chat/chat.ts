import { studentChat, getCurrentTime, getUserId } from '../../../utils/api';

interface Message {
  id: number;
  role: 'ai' | 'user';
  content: string;
  time: string;
  showTime?: boolean;
  emotion?: number;
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

interface ChildInfo {
  name: string;
  gender: string;
  age: string;
  grade: string;
}

interface EmotionConfig {
  level: number;
  label: string;
  color: string;
  icon: string;
}

interface AgentAvatar {
  id: string;
  name: string;
  avatar: string;
  desc: string;
}

const AGENT_AVATARS: AgentAvatar[] = [
  { id: 'default', name: '暖暖', avatar: '/assets/avatar/pet/avatar.png', desc: '温暖贴心' },
  { id: 'wise', name: '智慧导师', avatar: '/assets/avatar/pet/avatar.png', desc: '睿智沉稳' },
  { id: 'friendly', name: '知心姐姐', avatar: '/assets/avatar/pet/avatar.png', desc: '亲切友善' },
];

const EMOTION_CONFIGS: EmotionConfig[] = [
  { level: 1, label: '平静', color: '#95de64', icon: '😌' },
  { level: 2, label: '温暖', color: '#ffc53d', icon: '😊' },
  { level: 3, label: '关切', color: '#ff7a45', icon: '🤗' },
  { level: 4, label: '专注', color: '#69c0ff', icon: '🧐' },
  { level: 5, label: '热情', color: '#ff85c0', icon: '💖' },
];

const STORAGE_KEYS = {
  sessions: 'student_sessions',
  agentConfig: 'student_agent_config',
  childInfo: 'child_info',
} as const;

Page({
  data: {
    inputText: '',
    scrollTop: 0,
    loading: false,
    messages: [] as Message[],
    inputMode: 'text' as 'text' | 'voice',
    voiceState: 'idle' as 'idle' | 'recording' | 'transcribing',
    keyboardHeight: 0,
    inputAreaHeight: 120,
    showToolbox: false,
    showAgentSettings: false,
    showSessionList: false,
    showAvatarPicker: false,
    showContextMenu: false,
    showContextPanel: false,
    showInfoModal: false,
    contextMenuFor: null as number | null,
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
    abortController: null as any,
    editingMessageId: null as number | null,
    editText: '',
    childInfo: {
      name: '',
      gender: '',
      age: '',
      grade: ''
    } as ChildInfo
  },

  onLoad() {
    this.checkChildInfo();
    this.loadAgentConfig();

    wx.onKeyboardHeightChange((res: any) => {
      this.setData({ keyboardHeight: res.height });
    });
  },

  onUnload() {
    try { wx.offKeyboardHeightChange(() => {}); } catch (e) {}
    if (this.data.abortController) {
      this.data.abortController.abort();
    }
  },

  checkChildInfo() {
    const childInfo = wx.getStorageSync(STORAGE_KEYS.childInfo) as ChildInfo | undefined;
    if (!childInfo || !childInfo.name) {
      this.setData({ showInfoModal: true });
    } else {
      this.setData({ childInfo });
      this.loadSessions();
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
    const childInfo = this.data.childInfo;
    const greeting: Message = {
      id: Date.now(),
      role: 'ai',
      content: childInfo.name ?
        `你好，${childInfo.name}！我是你的好朋友暖暖 🌟\n\n也一名专业的AI心理辅导老师。今天过得怎么样？有什么想聊的，或者有什么烦心事，都可以告诉我哦~` :
        '你好呀～我是你的好朋友暖暖 🌟\n\n也是一名专业的AI心理辅导老师。有什么想聊的，或者有什么烦心事，都可以告诉我哦',
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

  onNameInput(e: any) {
    const childInfo = { ...this.data.childInfo };
    childInfo.name = e.detail.value;
    this.setData({ childInfo });
  },

  onGenderSelect(e: any) {
    const childInfo = { ...this.data.childInfo };
    childInfo.gender = e.currentTarget.dataset.gender;
    this.setData({ childInfo });
  },

  onAgeInput(e: any) {
    const childInfo = { ...this.data.childInfo };
    childInfo.age = e.detail.value;
    this.setData({ childInfo });
  },

  onGradeInput(e: any) {
    const childInfo = { ...this.data.childInfo };
    childInfo.grade = e.detail.value;
    this.setData({ childInfo });
  },

  onSubmitInfo() {
    const childInfo = this.data.childInfo;
    if (!childInfo.name || !childInfo.gender || !childInfo.age || !childInfo.grade) {
      wx.showToast({ title: '请填写完整信息', icon: 'none' });
      return;
    }

    wx.setStorageSync(STORAGE_KEYS.childInfo, childInfo);
    this.setData({ showInfoModal: false });
    this.createNewSession();
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
        '今天心情不太好',
        '最近学习压力有点大',
        '和同学闹矛盾了',
      ];
      const text = mockTexts[Math.floor(Math.random() * mockTexts.length)];
      this.addUserMessage(text + ' 🎤');
      this.callAI(text);
    }, 1000);
  },

  onSend() {
    const inputText = this.data.inputText.trim();
    if (!inputText || this.data.loading) return;

    if (this.data.editingMessageId) {
      this.confirmEdit();
      return;
    }

    this.addUserMessage(inputText);
    this.setData({ inputText: '', inputAreaHeight: 120 });
    this.callAI(inputText);
  },

  addUserMessage(content: string) {
    const now = Date.now();
    const messages = [...this.data.messages];
    const lastMsg = messages[messages.length - 1];
    const showTime = !lastMsg || this.shouldShowTime(lastMsg.time, getCurrentTime());

    const msg: Message = {
      id: now,
      role: 'user',
      content,
      time: getCurrentTime(),
      showTime,
      canWithdraw: true,
    };

    messages.push(msg);
    this.setData({ messages, loading: true });
    this.saveSessions();
    this.scrollToBottom();
  },

  addAIMessage(content: string, emotion: number = 2) {
    const messages = [...this.data.messages];
    const lastMsg = messages[messages.length - 1];
    const showTime = !lastMsg || this.shouldShowTime(lastMsg.time, getCurrentTime());

    const msg: Message = {
      id: Date.now(),
      role: 'ai',
      content,
      time: getCurrentTime(),
      showTime,
      emotion,
    };

    messages.push(msg);
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

  callAI(text: string) {
    const userId = getUserId();
    const childInfo = this.data.childInfo;

    this.setData({ streamingContent: '', loading: true });

    studentChat(userId, text, childInfo)
      .then((res: any) => {
        if (res.success) {
          const emotion = this.detectEmotion(res.response || '');
          this.addAIMessage(res.response, emotion);
        } else {
          throw new Error('AI回复失败');
        }
      })
      .catch((err: any) => {
        console.error('发送消息失败:', err);
        this.addAIMessage(this.fallbackResponse(text), 2);
      });
  },

  detectEmotion(text: string): number {
    if (text.includes('😊') || text.includes('很高兴') || text.includes('太棒了')) return 5;
    if (text.includes('🤗') || text.includes('理解') || text.includes('支持')) return 3;
    if (text.includes('🧐') || text.includes('建议') || text.includes('可以尝试')) return 4;
    if (text.includes('😌') || text.includes('放心') || text.includes('正常')) return 1;
    return 2;
  },

  fallbackResponse(text: string): string {
    const q = text.toLowerCase();
    if (q.includes('心情') || q.includes('难过') || q.includes('伤心')) {
      return '听到你心情不好，我有点担心你 🌸\n\n不管发生什么，我都在这里陪着你。要不要说说发生了什么？有时候把心里的话说出来会好受一些的。';
    }
    if (q.includes('学习') || q.includes('考试') || q.includes('作业')) {
      return '学习确实会让人感到压力呢 📚\n\n不要太苛责自己哦，每个人都会有累的时候。适当休息也很重要，记得照顾好自己呀～';
    }
    if (q.includes('朋友') || q.includes('同学') || q.includes('矛盾')) {
      return '和朋友相处中遇到问题是很常见的呢 💭\n\n要不要说说具体发生了什么事？也许我可以帮你想想办法～';
    }
    return '谢谢你和我说这些 🌟\n\n我在这里认真听你说哦，有什么想聊的尽管告诉我～';
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

  onMessageLongPress(e: any) {
    const id = e.currentTarget.dataset.id;
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
        success: () => {
          wx.showToast({ title: '已复制', icon: 'success' });
        }
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

  onShowToolbox() {
    this.setData({ showToolbox: true });
  },

  onCloseToolbox() {
    this.setData({ showToolbox: false });
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
      title: '清空历史对话',
      content: '确定清空所有聊天记录吗？',
      confirmText: '清空',
      cancelText: '取消',
      confirmColor: '#ff4d4f',
      success: (res: any) => {
        if (res.confirm) {
          wx.removeStorageSync(STORAGE_KEYS.sessions);
          this.setData({ sessions: [], showAgentSettings: false });
          this.createNewSession();
          wx.showToast({ title: '已清空', icon: 'success' });
        }
      }
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
      content: `${this.data.agent.name} · AI心理辅导老师\n\n专注为学生提供心理陪伴和情感支持，帮你度过每一个开心或不那么开心的日子 🌈\n\n记住，我永远在这里陪着你！`,
      showCancel: false,
      confirmText: '我知道了',
    });
  },

  scrollToBottom() {
    setTimeout(() => {
      this.setData({ scrollTop: Date.now() });
    }, 50);
  },

  onScroll(e: any) {
    this.setData({ scrollTop: e.detail.scrollTop });
  },
});