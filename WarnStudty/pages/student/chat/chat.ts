import { studentChat, getCurrentTime, getUserId } from "../../../utils/api";

declare const requirePlugin: ((pluginName: string) => any) | undefined;

interface Message {
  id: number;
  role: "ai" | "user";
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
  {
    id: "default",
    name: "心理助手",
    avatar: "/images/ai.png",
    desc: "理性陪伴",
  },
  {
    id: "wise",
    name: "学习顾问",
    avatar: "/images/ai.png",
    desc: "分析清晰",
  },
  {
    id: "friendly",
    name: "倾听伙伴",
    avatar: "/images/ai.png",
    desc: "稳重温和",
  },
];

const EMOTION_CONFIGS: EmotionConfig[] = [
  { level: 1, label: "平静", color: "#95de64", icon: "●" },
  { level: 2, label: "温和", color: "#ffc53d", icon: "●" },
  { level: 3, label: "关切", color: "#ff7a45", icon: "●" },
  { level: 4, label: "专注", color: "#69c0ff", icon: "●" },
  { level: 5, label: "积极", color: "#ff85c0", icon: "●" },
];

const STORAGE_KEYS = {
  sessions: "student_sessions",
  agentConfig: "student_agent_config",
  childInfo: "child_info",
  pendingPrompt: "student_pending_chat_prompt",
} as const;

let recordRecognitionManager: any = null;
let studentKeyboardHeightHandler:
  | ((res: { height: number }) => void)
  | null = null;
try {
  const plugin =
    typeof requirePlugin === "function" ? requirePlugin("WechatSI") : null;
  if (plugin && typeof plugin.getRecordRecognitionManager === "function") {
    recordRecognitionManager = plugin.getRecordRecognitionManager();
  }
} catch (_e) {
  recordRecognitionManager = null;
}

interface ChatPageData {
  statusBarHeight: number;
  inputText: string;
  scrollTop: number;
  loading: boolean;
  messages: Message[];
  inputMode: "text" | "voice";
  voiceState: "idle" | "recording" | "transcribing";
  keyboardHeight: number;
  inputAreaHeight: number;
  showToolbox: boolean;
  showAgentSettings: boolean;
  showSessionList: boolean;
  showAvatarPicker: boolean;
  showContextMenu: boolean;
  showContextPanel: boolean;
  showInfoModal: boolean;
  contextMenuFor: number | null;
  contextMenuRole: "" | "ai" | "user";
  contextMenuPos: { x: number; y: number };
  currentSessionId: string;
  sessions: Session[];
  agent: AgentConfig;
  emotionDisplay: EmotionConfig;
  streamingContent: string;
  abortController: AbortController | null;
  stopRequested: boolean;
  editingMessageId: number | null;
  editText: string;
  childInfo: ChildInfo;
}

const data: ChatPageData = {
  statusBarHeight: 20,
  inputText: "",
  scrollTop: 0,
  loading: false,
  messages: [],
  inputMode: "text",
  voiceState: "idle",
  keyboardHeight: 0,
  inputAreaHeight: 64,
  showToolbox: false,
  showAgentSettings: false,
  showSessionList: false,
  showAvatarPicker: false,
  showContextMenu: false,
  showContextPanel: false,
  showInfoModal: false,
  contextMenuFor: null,
  contextMenuRole: "",
  contextMenuPos: { x: 0, y: 0 },
  currentSessionId: "",
  sessions: [],
  agent: {
    name: "心理助手",
    avatar: "/images/ai.png",
    personality: "理性陪伴",
    emotionLevel: 2,
  },
  emotionDisplay: EMOTION_CONFIGS[1],
  streamingContent: "",
  abortController: null,
  stopRequested: false,
  editingMessageId: null,
  editText: "",
  childInfo: {
    name: "",
    gender: "",
    age: "",
    grade: "",
  },
};

Page({
  data,

  onLoad() {
    const win =
      typeof wx.getWindowInfo === "function"
        ? wx.getWindowInfo()
        : wx.getSystemInfoSync();

    this.setData({ statusBarHeight: win.statusBarHeight || 20 });

    this.checkChildInfo();
    this.loadAgentConfig();
    this.initVoiceRecognition();

    studentKeyboardHeightHandler = (res: { height: number }) => {
      this.setData({ keyboardHeight: res.height });
    };
    wx.onKeyboardHeightChange(studentKeyboardHeightHandler);
  },

  onShow() {
    this.consumePendingPrompt();
  },

  onUnload() {
    try {
      if (studentKeyboardHeightHandler) {
        wx.offKeyboardHeightChange(studentKeyboardHeightHandler);
        studentKeyboardHeightHandler = null;
      }
    } catch (_e) {
      /* empty */
    }
    const abortController = (this.data as ChatPageData).abortController;
    if (abortController) {
      abortController.abort();
    }
  },

  checkChildInfo() {
    const childInfo = wx.getStorageSync(STORAGE_KEYS.childInfo) as
      | ChildInfo
      | undefined;
    if (!childInfo || !childInfo.name) {
      this.setData({ showInfoModal: true });
    } else {
      this.setData({ childInfo });
      this.loadSessions();
    }
  },

  loadSessions() {
    const sessions =
      (wx.getStorageSync(STORAGE_KEYS.sessions) as Session[]) || [];
    if (sessions.length > 0) {
      const currentSession = sessions[0];
      this.setData({
        sessions,
        currentSessionId: currentSession.id,
        messages: currentSession.messages,
      });
    } else {
      this.createNewSession();
    }
  },

  loadAgentConfig() {
    const agent = wx.getStorageSync(STORAGE_KEYS.agentConfig) as
      | AgentConfig
      | undefined;
    if (agent) {
      const normalizedAgent: AgentConfig = {
        ...agent,
        avatar: "/images/ai.png",
      };
      const emotionDisplay =
        EMOTION_CONFIGS.find((e) => e.level === normalizedAgent.emotionLevel) ||
        EMOTION_CONFIGS[1];
      this.setData({ agent: normalizedAgent, emotionDisplay });
      wx.setStorageSync(STORAGE_KEYS.agentConfig, normalizedAgent);
    }
  },

  createNewSession() {
    const sessionId = `session_${Date.now()}`;
    const childInfo = (this.data as ChatPageData).childInfo;
    const greeting: Message = {
      id: Date.now(),
      role: "ai",
      content: childInfo.name
        ? `你好，${childInfo.name}！我是你的好朋友暖暖 🌟\n\n也是一名专业的AI心理辅导老师。今天过得怎么样？如果有烦心事，可以慢慢告诉我。`
        : "你好呀～我是你的好朋友暖暖 🌟\n\n也是一名专业的AI心理辅导老师。如果你有烦心事，我会认真听你说。",
      time: getCurrentTime(),
      showTime: true,
      emotion: 2,
    };

    const newSession: Session = {
      id: sessionId,
      title: "新对话",
      lastMessage: greeting.content.substring(0, 20) + "...",
      time: getCurrentTime(),
      messages: [greeting],
    };

    const sessions = [newSession, ...(this.data as ChatPageData).sessions];
    this.setData({
      sessions,
      currentSessionId: sessionId,
      messages: [greeting],
    });
    this.saveSessions();
  },

  saveSessions() {
    const sessions = [...(this.data as ChatPageData).sessions];
    const currentSessionId = (this.data as ChatPageData).currentSessionId;
    const messages = (this.data as ChatPageData).messages;
    const sessionIndex = sessions.findIndex(
      (s: Session) => s.id === currentSessionId,
    );
    if (sessionIndex >= 0) {
      sessions[sessionIndex].messages = messages;
      if (messages.length > 1) {
        sessions[sessionIndex].title = messages[1].content.substring(0, 15);
        sessions[sessionIndex].lastMessage = messages[
          messages.length - 1
        ].content.substring(0, 30);
      }
      sessions[sessionIndex].time = getCurrentTime();
    }
    wx.setStorageSync(STORAGE_KEYS.sessions, sessions);
  },

  onNameInput(e: { detail: { value: string } }) {
    const childInfo = { ...(this.data as ChatPageData).childInfo };
    childInfo.name = e.detail.value;
    this.setData({ childInfo });
  },

  onGenderSelect(e: { currentTarget: { dataset: { gender: string } } }) {
    const childInfo = { ...(this.data as ChatPageData).childInfo };
    childInfo.gender = e.currentTarget.dataset.gender;
    this.setData({ childInfo });
  },

  onAgeInput(e: { detail: { value: string } }) {
    const childInfo = { ...(this.data as ChatPageData).childInfo };
    childInfo.age = e.detail.value;
    this.setData({ childInfo });
  },

  onGradeInput(e: { detail: { value: string } }) {
    const childInfo = { ...(this.data as ChatPageData).childInfo };
    childInfo.grade = e.detail.value;
    this.setData({ childInfo });
  },

  onSubmitInfo() {
    const childInfo = { ...(this.data as ChatPageData).childInfo };
    if (
      !childInfo.name ||
      !childInfo.gender ||
      !childInfo.age ||
      !childInfo.grade
    ) {
      wx.showToast({ title: "请填写完整信息", icon: "none" });
      return;
    }

    wx.setStorageSync(STORAGE_KEYS.childInfo, childInfo);
    wx.setStorageSync("user_info", {
      name: childInfo.name,
      grade: childInfo.grade,
      class: "",
      todayMood: 0.8,
      moodLabel: "心情不错",
      moodIcon: "😊",
    });
    wx.setStorageSync("student_profile_completed", true);
    this.setData({ showInfoModal: false });
    this.createNewSession();
  },

  onTextInput(e: { detail: { value: string } }) {
    this.setData({ inputText: e.detail.value });
    this.updateInputHeight(e.detail.value);
  },

  updateInputHeight(text: string) {
    const lines = (text.match(/\n/g) || []).length + 1;
    const baseH = 64;
    const lineH = 28;
    const maxH = 140;
    const h = Math.min(baseH + (lines - 1) * lineH, maxH);
    this.setData({ inputAreaHeight: h });
  },

  onTextareaFocus() {
    this.scrollToBottom();
  },

  onToggleInputMode() {
    const next =
      (this.data as ChatPageData).inputMode === "text" ? "voice" : "text";
    this.setData({ inputMode: next, showToolbox: false });
    if (next === "voice") wx.hideKeyboard();
  },

  initVoiceRecognition() {
    if (!recordRecognitionManager || (this as any)._voiceInited) return;

    (this as any)._voiceInited = true;

    recordRecognitionManager.onStop((res: any) => {
      const result = (res && res.result ? res.result : "").trim();
      this.setData({ voiceState: "idle" });

      if (!result) {
        wx.showToast({ title: "未识别到语音", icon: "none" });
        return;
      }

      this.setData({ inputMode: "text", inputText: result });
      this.updateInputHeight(result);
      this.onSend();
    });

    recordRecognitionManager.onError(() => {
      this.setData({ voiceState: "idle" });
      wx.showToast({ title: "语音识别失败", icon: "none" });
    });
  },

  consumePendingPrompt() {
    const prompt = wx.getStorageSync(STORAGE_KEYS.pendingPrompt);
    if (
      typeof prompt !== "string" ||
      !prompt.trim() ||
      (this.data as ChatPageData).loading
    ) {
      return;
    }

    wx.removeStorageSync(STORAGE_KEYS.pendingPrompt);

    const text = prompt.trim();
    this.setData({ inputMode: "text", inputText: text });
    this.updateInputHeight(text);
    this.addUserMessage(text);
    this.setData({ inputText: "", inputAreaHeight: 64 });
    this.callAI(text);
  },

  onVoiceStart() {
    if ((this.data as ChatPageData).inputMode !== "voice") return;
    if (!recordRecognitionManager) {
      wx.showToast({ title: "语音识别插件不可用", icon: "none" });
      return;
    }

    this.setData({ voiceState: "recording" });
    wx.vibrateShort({ type: "medium" });
    recordRecognitionManager.start({
      lang: "zh_CN",
      duration: 60000,
    });
  },

  onVoiceEnd() {
    if ((this.data as ChatPageData).voiceState !== "recording") return;
    if (!recordRecognitionManager) return;

    this.setData({ voiceState: "transcribing" });
    recordRecognitionManager.stop();
  },

  onSend() {
    const inputText = (this.data as ChatPageData).inputText.trim();
    if (!inputText || (this.data as ChatPageData).loading) return;

    if ((this.data as ChatPageData).editingMessageId) {
      this.confirmEdit();
      return;
    }

    this.addUserMessage(inputText);
    this.setData({ inputText: "", inputAreaHeight: 64 });
    this.callAI(inputText);
  },

  addUserMessage(content: string) {
    const now = Date.now();
    const messages = [...(this.data as ChatPageData).messages];
    const lastMsg = messages[messages.length - 1];
    const showTime =
      !lastMsg || this.shouldShowTime(lastMsg.time, getCurrentTime());

    const msg: Message = {
      id: now,
      role: "user",
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
    const messages = [...(this.data as ChatPageData).messages];
    const lastMsg = messages[messages.length - 1];
    const showTime =
      !lastMsg || this.shouldShowTime(lastMsg.time, getCurrentTime());

    const msg: Message = {
      id: Date.now(),
      role: "ai",
      content,
      time: getCurrentTime(),
      showTime,
      emotion,
    };

    messages.push(msg);
    this.setData({
      messages,
      loading: false,
      streamingContent: "",
    });
    this.saveSessions();
    this.scrollToBottom();
  },

  shouldShowTime(lastTime: string, currentTime: string): boolean {
    const lastParts = lastTime.split(":");
    const currentParts = currentTime.split(":");
    if (lastParts.length !== 2 || currentParts.length !== 2) return false;

    const lastMinutes = parseInt(lastParts[0]) * 60 + parseInt(lastParts[1]);
    const currentMinutes =
      parseInt(currentParts[0]) * 60 + parseInt(currentParts[1]);

    return currentMinutes - lastMinutes >= 5;
  },

  callAI(text: string) {
    const userId = getUserId();

    this.setData({ streamingContent: "", loading: true, stopRequested: false });

    studentChat(userId, text)
      .then(
        (res: {
          success: boolean;
          response: string;
          emotion?: string;
          crisis_level?: string;
          type?: string;
        }) => {
          if ((this.data as ChatPageData).stopRequested) {
            this.setData({ stopRequested: false });
            return;
          }
          if (res.success) {
            // 优先使用后端返回的情绪，后端没返回则前端检测
            let emotion: number;
            if (res.emotion) {
              emotion = this.emotionStrToLevel(res.emotion);
            } else {
              emotion = this.detectEmotion(res.response || "");
            }

            // 如果是危机干预，增加特殊标记
            if (res.type === "crisis_intervention") {
              console.warn("危机检测:", res.crisis_level);
            }

            this.addAIMessage(res.response, emotion);
          } else {
            throw new Error("AI鍥炲澶辫触");
          }
        },
      )
      .catch((_err: Error) => {
        if ((this.data as ChatPageData).stopRequested) {
          this.setData({ stopRequested: false });
          return;
        }
        console.error("鍙戦€佹秷鎭け璐?", _err);
        this.addAIMessage(this.fallbackResponse(text), 2);
      });
  },

  /**
   * 灏嗗悗绔繑鍥炵殑鎯呯华瀛楃涓茶浆鎹负鍓嶇emotion level
   * emotion level: 1=骞抽潤, 2=娓╂殩, 3=鍏冲垏, 4=涓撴敞, 5=鐑儏
   */
  emotionStrToLevel(emotion: string): number {
    const map: Record<string, number> = {
      happy: 5,
      开心: 5,
      hopeful: 4,
      有希望: 4,
      anxious: 3,
      焦虑: 3,
      sad: 3,
      难过: 3,
      angry: 2,
      生气: 2,
      fearful: 2,
      害怕: 2,
      neutral: 1,
      平静: 1,
      ashamed: 2,
      羞愧: 2,
    };
    return map[emotion.toLowerCase()] || 2;
  },

  detectEmotion(text: string): number {
    if (
      text.includes("😊") ||
      text.includes("很高兴") ||
      text.includes("太棒了")
    )
      return 5;
    if (text.includes("🤗") || text.includes("理解") || text.includes("支持"))
      return 3;
    if (
      text.includes("🧐") ||
      text.includes("建议") ||
      text.includes("可以尝试")
    )
      return 4;
    if (text.includes("😌") || text.includes("放心") || text.includes("正常"))
      return 1;
    return 2;
  },

  fallbackResponse(text: string): string {
    const q = text.toLowerCase();
    if (q.includes("心情") || q.includes("难过") || q.includes("伤心")) {
      return "听到你心情不好，我有点担心你 🌸\n\n不管发生什么，我都在这里陪着你。要不要说说发生了什么？有时候把心里的话说出来会好受一些的。";
    }
    if (q.includes("学习") || q.includes("考试") || q.includes("作业")) {
      return "学习确实会让人感到压力呢 📚\n\n不要太苛责自己哦，每个人都会有累的时候。适当休息也很重要，记得照顾好自己呀～";
    }
    if (q.includes("朋友") || q.includes("同学") || q.includes("矛盾")) {
      return "和朋友相处中遇到问题是很常见的呢 💭\n\n要不要说说具体发生了什么事？也许我可以帮你想想办法～";
    }
    return "谢谢你和我说这些 🌟\n\n我在这里认真听你说哦，你可以把想法慢慢告诉我。";
  },

  onStopStreaming() {
    const abortController = (this.data as ChatPageData).abortController;
    const streamingContent = (this.data as ChatPageData).streamingContent;

    this.setData({
      loading: false,
      stopRequested: true,
      streamingContent: "",
      abortController: null,
    });

    if (abortController) {
      abortController.abort();
    }

    if (streamingContent) {
      this.addAIMessage(streamingContent + " [已中断]", 2);
    }
  },

  onMessageLongPress(e: {
    currentTarget: { dataset: { id: number } };
    touches: { clientX: number; clientY: number }[];
  }) {
    const id = e.currentTarget.dataset.id;
    const messages = (this.data as ChatPageData).messages;
    const message = messages.find((m: Message) => m.id === id);
    if (!message) return;

    const touch = e.touches[0];
    this.setData({
      showContextMenu: true,
      contextMenuFor: id,
      contextMenuRole: message.role,
      contextMenuPos: { x: touch.clientX, y: touch.clientY - 100 },
    });
  },

  onCopyMessage() {
    const messages = (this.data as ChatPageData).messages;
    const contextMenuFor = (this.data as ChatPageData).contextMenuFor;
    const message = messages.find((m: Message) => m.id === contextMenuFor);
    if (message) {
      wx.setClipboardData({
        data: message.content,
        success: () => {
          wx.showToast({ title: "已复制", icon: "success" });
        },
      });
    }
    this.closeContextMenu();
  },

  onWithdrawMessage() {
    const messages = [...(this.data as ChatPageData).messages];
    const contextMenuFor = (this.data as ChatPageData).contextMenuFor;
    const index = messages.findIndex((m: Message) => m.id === contextMenuFor);

    if (index >= 0) {
      const msgRole = messages[index].role;
      if (msgRole === "user") {
        const editText = messages[index].content;
        messages.splice(index, 1);

        if (index < messages.length) {
          const nextRole = messages[index].role;
          if (nextRole === "ai") {
            messages.splice(index, 1);
          }
        }

        this.setData({
          messages,
          editingMessageId: contextMenuFor,
          editText,
          inputText: editText,
        });
        this.updateInputHeight(editText);
        this.saveSessions();
      }
    }
    this.closeContextMenu();
  },

  onEditMessage() {
    const messages = (this.data as ChatPageData).messages;
    const contextMenuFor = (this.data as ChatPageData).contextMenuFor;
    const message = messages.find((m: Message) => m.id === contextMenuFor);
    if (message && message.role === "user") {
      this.setData({
        editingMessageId: message.id,
        editText: message.content,
        inputText: message.content,
      });
      this.updateInputHeight(message.content);
    }
    this.closeContextMenu();
  },

  confirmEdit() {
    const messages = [...(this.data as ChatPageData).messages];
    const editingMessageId = (this.data as ChatPageData).editingMessageId;
    const inputText = (this.data as ChatPageData).inputText;
    const index = messages.findIndex((m: Message) => m.id === editingMessageId);

    if (index >= 0 && inputText.trim()) {
      messages[index].content = inputText.trim();
      messages[index].time = getCurrentTime();

      if (index + 1 < messages.length && messages[index + 1].role === "ai") {
        messages.splice(index + 1, 1);
      }

      this.setData({
        messages,
        editingMessageId: null,
        editText: "",
        inputText: "",
        inputAreaHeight: 64,
      });
      this.saveSessions();
      this.callAI(inputText.trim());
    }
  },

  cancelEdit() {
    this.setData({
      editingMessageId: null,
      editText: "",
      inputText: "",
      inputAreaHeight: 64,
    });
  },

  closeContextMenu() {
    this.setData({
      showContextMenu: false,
      contextMenuFor: null,
      contextMenuRole: "",
    });
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

  onSelectSession(e: { currentTarget: { dataset: { id: string } } }) {
    const id = e.currentTarget.dataset.id;
    const sessions = (this.data as ChatPageData).sessions;
    const session = sessions.find((s: Session) => s.id === id);
    if (session) {
      this.setData({
        currentSessionId: id,
        messages: session.messages,
        showSessionList: false,
      });
    }
  },

  onNewSession() {
    this.createNewSession();
    this.setData({ showSessionList: false });
  },

  onDeleteSession(e: { currentTarget: { dataset: { id: string } } }) {
    const id = e.currentTarget.dataset.id;
    const sessions = (this.data as ChatPageData).sessions.filter(
      (s: Session) => s.id !== id,
    );
    const currentSessionId = (this.data as ChatPageData).currentSessionId;

    if (id === currentSessionId) {
      if (sessions.length > 0) {
        this.setData({
          sessions,
          currentSessionId: sessions[0].id,
          messages: sessions[0].messages,
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

  onSelectAvatar(e: { currentTarget: { dataset: { id: string } } }) {
    const id = e.currentTarget.dataset.id;
    const avatar = AGENT_AVATARS.find((a) => a.id === id);
    if (avatar) {
      const agent: AgentConfig = {
        ...(this.data as ChatPageData).agent,
        name: avatar.name,
        avatar: "/images/ai.png",
        personality: avatar.desc,
      };
      this.setData({ agent, showAvatarPicker: false });
      wx.setStorageSync(STORAGE_KEYS.agentConfig, agent);
    }
  },

  onEmotionChange(e: { detail: { value: string } }) {
    const level = parseInt(e.detail.value) + 1;
    const emotionDisplay =
      EMOTION_CONFIGS.find((em) => em.level === level) || EMOTION_CONFIGS[1];
    const agent: AgentConfig = {
      ...(this.data as ChatPageData).agent,
      emotionLevel: level,
    };
    this.setData({ agent, emotionDisplay });
    wx.setStorageSync(STORAGE_KEYS.agentConfig, agent);
  },

  onQuickQuestion(e: { currentTarget: { dataset: { question: string } } }) {
    const question = e.currentTarget.dataset.question;
    this.setData({ inputText: question, showToolbox: false });
  },

  onClearHistory() {
    wx.showModal({
      title: "清空历史对话",
      content: "确定清空所有聊天记录吗？",
      confirmText: "清空",
      cancelText: "取消",
      success: (res: { confirm: boolean }) => {
        if (res.confirm) {
          wx.removeStorageSync(STORAGE_KEYS.sessions);
          this.setData({ sessions: [], showAgentSettings: false });
          this.createNewSession();
          wx.showToast({ title: "已清空", icon: "success" });
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
      title: "鍏充簬AI鍔╂墜",
      content: `${(this.data as ChatPageData).agent.name} 路 AI蹇冪悊杈呭鑰佸笀\n\n涓撴敞涓哄鐢熸彁渚涘績鐞嗛櫔浼村拰鎯呮劅鏀寔锛屽府浣犲害杩囨瘡涓€涓紑蹇冩垨涓嶉偅涔堝紑蹇冪殑鏃ュ瓙 馃寛\n\n璁颁綇锛屾垜姘歌繙鍦ㄨ繖閲岄櫔鐫€浣狅紒`,
      confirmText: "鎴戠煡閬撲簡",
    });
  },

  scrollToBottom() {
    setTimeout(() => {
      this.setData({ scrollTop: Date.now() });
    }, 50);
  },

  onScroll(e: { detail: { scrollTop: number } }) {
    this.setData({ scrollTop: e.detail.scrollTop });
  },
});
