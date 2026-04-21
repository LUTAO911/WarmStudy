/* knowledge.ts - 心理知识库页面 */

interface KnowledgeItem {
  id: string;
  title: string;
  category: string;
  content: string;
  keywords: string[];
  emotions: string[];
}

const getApiBase = (): string => {
  const app = getApp<IAppOption>();
  return app?.globalData?.apiBase || "http://localhost:8000";
};

Page({
  data: {
    categories: [] as string[],
    selectedCategory: '全部',
    knowledgeList: [] as KnowledgeItem[],
    filteredList: [] as KnowledgeItem[],
    showDetail: false,
    selectedItem: null as KnowledgeItem | null,
    loading: false,
  },

  onLoad(options?: { id?: string }) {
    this.loadCategories();
    this.loadKnowledge(options?.id);
  },

  loadCategories() {
    // 使用后端API获取分类
    wx.request({
      url: `${getApiBase()}/api/agent/psychology/categories`,
      method: 'GET',
      success: (res) => {
        if (res.data.ok) {
          const cats = ['全部', ...res.data.categories];
          this.setData({ categories: cats });
        } else {
          // fallback到默认分类
          this.setData({
            categories: ['全部', '考试心理', '压力管理', '人际关系', '情绪管理', '亲子沟通', '自我认知']
          });
        }
      },
      fail: () => {
        this.setData({
          categories: ['全部', '考试心理', '压力管理', '人际关系', '情绪管理', '亲子沟通', '自我认知']
        });
      }
    });
  },

  loadKnowledge(targetId?: string) {
    this.setData({ loading: true });

    // 调用后端API获取知识列表
    wx.request({
      url: `${getApiBase()}/api/agent/psychology/knowledge`,
      method: 'GET',
      data: {
        q: '心理',
        user_type: 'student',
        n: 20
      },
      success: (res) => {
        if (res.data.ok && res.data.results) {
          const selectedItem =
            targetId
              ? res.data.results.find((item: KnowledgeItem) => item.id === targetId) || null
              : null;
          this.setData({
            knowledgeList: res.data.results,
            filteredList: res.data.results,
            loading: false,
            selectedItem,
            showDetail: !!selectedItem
          });
        } else {
          this.setData({ loading: false });
        }
      },
      fail: () => {
        this.setData({ loading: false });
      }
    });
  },

  onCategoryChange(e: any) {
    const category = e.currentTarget.dataset.category as string;
    this.setData({ selectedCategory: category });

    if (category === '全部') {
      this.setData({ filteredList: this.data.knowledgeList });
    } else {
      const filtered = this.data.knowledgeList.filter(
        (item: KnowledgeItem) => item.category === category
      );
      this.setData({ filteredList: filtered });
    }
  },

  onKnowledgeTap(e: any) {
    const item = e.currentTarget.dataset.item as KnowledgeItem;
    this.setData({ selectedItem: item, showDetail: true });
  },

  closeDetail() {
    this.setData({ showDetail: false, selectedItem: null });
  },

  onShareAppMessage() {
    return {
      title: '心理知识 - 暖学帮',
      path: '/pages/student/library/knowledge/knowledge'
    };
  }
});
