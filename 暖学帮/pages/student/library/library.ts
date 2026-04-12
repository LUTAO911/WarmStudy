/* library.ts - 心理成长中心 */

const API_BASE = 'http://localhost:8000';

function request(url: string, data?: any, method: string = 'POST'): Promise<any> {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}${url}`,
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

interface PsychCard {
  id: string;
  title: string;
  desc: string;
  icon: string;
  bgColor: string;
  path: string;
  tag?: string;
}

interface KnowledgeItem {
  id: string;
  title: string;
  category: string;
  summary: string;
  readTime: string;
  isNew?: boolean;
}

interface ReportData {
  weekEmotion: number[];
  averageScore: number;
  trend: 'up' | 'down' | 'stable';
  suggestions: string[];
}

const PSYCH_CARDS: PsychCard[] = [
  { 
    id: 'checkin', 
    title: '心理打卡', 
    desc: '记录今日心情',
    icon: '📝',
    bgColor: '#fff3e0',
    path: '/pages/student/chat/chat',
    tag: '每日'
  },
  { 
    id: 'report', 
    title: '心理周报', 
    desc: '查看情绪变化',
    icon: '📊',
    bgColor: '#e3f2fd',
    path: '/pages/student/report/week'
  },
  { 
    id: 'knowledge', 
    title: '心理知识', 
    desc: '学习心理知识',
    icon: '📚',
    bgColor: '#f3e5f5',
    path: '/pages/student/library/knowledge',
    tag: '推荐'
  },
  { 
    id: 'relax', 
    title: '放松训练', 
    desc: '正念冥想放松',
    icon: '🧘',
    bgColor: '#e8f5e9',
    path: '/pages/student/relax/home'
  },
  { 
    id: 'consult', 
    title: '心理咨询', 
    desc: 'AI陪伴倾诉',
    icon: '💬',
    bgColor: '#fce4ec',
    path: '/pages/student/chat/chat'
  },
  { 
    id: 'test', 
    title: '心理测评', 
    desc: '专业量表测试',
    icon: '✨',
    bgColor: '#fff8e1',
    path: '/pages/student/assessment/start'
  },
];

const KNOWLEDGE_LIST: KnowledgeItem[] = [
  { 
    id: '1', 
    title: '如何应对考试焦虑？', 
    category: '考试心理',
    summary: '考试前感到紧张是很常见的反应...',
    readTime: '5分钟',
    isNew: true
  },
  { 
    id: '2', 
    title: '和同学闹矛盾了怎么办？', 
    category: '人际关系',
    summary: '朋友之间的摩擦很正常...',
    readTime: '4分钟'
  },
  { 
    id: '3', 
    title: '家长总是不理解我怎么办？', 
    category: '亲子沟通',
    summary: '代沟是很多家庭都会遇到的问题...',
    readTime: '6分钟',
    isNew: true
  },
  { 
    id: '4', 
    title: '学习压力大怎么放松？', 
    category: '压力管理',
    summary: '当学习压力让你喘不过气时...',
    readTime: '3分钟'
  },
  { 
    id: '5', 
    title: '如何克服拖延症？', 
    category: '自我管理',
    summary: '拖延是很多学生都面临的难题...',
    readTime: '5分钟'
  },
];

Page({
  data: {
    userInfo: {
      name: "李明",
      grade: "七年级",
      class: "（3）班",
      todayMood: 0.8,
      moodLabel: '心情不错',
      moodIcon: '😊',
    } as {
      name: string; grade: string; class: string; 
      todayMood: number; moodLabel: string; moodIcon: string;
    },
    psychCards: PSYCH_CARDS as PsychCard[],
    knowledgeList: KNOWLEDGE_LIST as KnowledgeItem[],
    showKnowledgeModal: false,
    selectedKnowledge: null as KnowledgeItem | null,
    showMoodPicker: false,
    todayChecked: false,
    todayMoodValue: 3,
    weekData: [75, 80, 65, 85, 70, 90, 78] as number[],
    reportData: {
      averageScore: 77,
      trend: 'up' as const,
      suggestions: ['继续保持良好作息', '适当增加运动时间', '多与朋友交流']
    } as ReportData,
  },

  onLoad() {
    this.loadUserInfo();
    this.checkTodayStatus();
  },

  loadUserInfo() {
    const info = wx.getStorageSync("user_info");
    if (info) {
      const moodLabels = ['很差', '不太好', '一般', '还不错', '很棒'];
      const moodIcons = ['😢', '😔', '😐', '😊', '🥰'];
      const moodIndex = Math.round((info.todayMood || 0.6) * 4);
      this.setData({
        userInfo: {
          ...info,
          todayMood: info.todayMood || 0.8,
          moodLabel: moodLabels[moodIndex],
          moodIcon: moodIcons[moodIndex],
        }
      });
    }
  },

  checkTodayStatus() {
    const lastCheck = wx.getStorageSync("last_mood_checkin");
    const today = new Date().toDateString();
    this.setData({ todayChecked: lastCheck === today });
  },

  onPsychCardTap(e: any) {
    const card = e.currentTarget.dataset.card as PsychCard;
    
    switch (card.id) {
      case 'checkin':
        this.onMoodCheckin();
        break;
      case 'report':
        this.showWeeklyReport();
        break;
      case 'knowledge':
        this.showKnowledgeList();
        break;
      case 'relax':
        this.startRelax();
        break;
      case 'consult':
        wx.switchTab({ url: '/pages/student/chat/chat' });
        break;
      case 'test':
        this.startAssessment();
        break;
      default:
        wx.navigateTo({ url: card.path });
    }
  },

  onMoodCheckin() {
    this.setData({ showMoodPicker: true });
  },

  onMoodSelect(e: any) {
    const moodValue = e.currentTarget.dataset.value;
    const moodLabels = ['很差', '不太好', '一般', '还不错', '很棒'];
    const moodIcons = ['😢', '😔', '😐', '😊', '🥰'];
    
    const userInfo = this.data.userInfo;
    userInfo.todayMood = moodValue / 4;
    userInfo.moodLabel = moodLabels[moodValue - 1];
    userInfo.moodIcon = moodIcons[moodValue - 1];
    
    wx.setStorageSync("user_info", userInfo);
    wx.setStorageSync("last_mood_checkin", new Date().toDateString());
    
    this.setData({
      userInfo,
      showMoodPicker: false,
      todayChecked: true,
    });
    
    wx.showToast({ title: '打卡成功 🌸', icon: 'success' });
    
    // 调用后端API记录
    request('/api/psychology/checkin', {
      mood: moodValue,
      timestamp: Date.now()
    }).catch(() => {});
  },

  closeMoodPicker() {
    this.setData({ showMoodPicker: false });
  },

  showWeeklyReport() {
    wx.navigateTo({ url: '/pages/student/report/week' });
  },

  showKnowledgeList() {
    wx.navigateTo({ url: '/pages/student/library/knowledge' });
  },

  onKnowledgeTap(e: any) {
    const item = e.currentTarget.dataset.item as KnowledgeItem;
    this.setData({ selectedKnowledge: item, showKnowledgeModal: true });
  },

  closeKnowledgeModal() {
    this.setData({ showKnowledgeModal: false, selectedKnowledge: null });
  },

  readKnowledge() {
    const item = this.data.selectedKnowledge;
    if (item) {
      wx.navigateTo({
        url: `/pages/student/library/knowledge-detail?id=${item.id}`
      });
    }
    this.closeKnowledgeModal();
  },

  startRelax() {
    wx.navigateTo({ url: '/pages/student/relax/home' });
  },

  startAssessment() {
    wx.navigateTo({ url: '/pages/student/assessment/start' });
  },

  getWeekChart() {
    const ctx = wx.createCanvasContext('weekChart');
    const data = this.data.weekData;
    const max = 100;
    const min = 0;
    const height = 120;
    const width = 280;
    const stepX = width / (data.length - 1);
    
    // 绘制折线
    ctx.setStrokeStyle('#69c0ff');
    ctx.setLineWidth(2);
    ctx.beginPath();
    
    data.forEach((value, index) => {
      const x = index * stepX;
      const y = height - ((value - min) / (max - min)) * height;
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
    
    // 绘制点
    ctx.setFillStyle('#69c0ff');
    data.forEach((value, index) => {
      const x = index * stepX;
      const y = height - ((value - min) / (max - min)) * height;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fill();
    });
    
    ctx.draw();
  },

  onShareAppMessage() {
    return {
      title: '暖学帮 - 心理成长中心',
      path: '/pages/student/library/library'
    };
  }
});
