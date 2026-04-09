/* library.ts - 随心学 */

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

function bindParentByToken(token: string, childId: string): Promise<{ success: boolean; error?: string }> {
  return request('/api/child/bind', { token, child_id: childId });
}

function getUserId(role: string = 'student'): string {
  return wx.getStorageSync('user_id') || 'student_001';
}

interface Todo {
  id: number; text: string; done: boolean;
  source: string;
}
interface Book {
  id: number; subject: string; grade: string; pub: string;
  added: boolean;
}

const ALL_BOOKS: Book[] = [
  { id: 1, subject: "数学", grade: "七年级", pub: "人教", added: false },
  { id: 2, subject: "英语", grade: "七年级", pub: "人教", added: false },
  { id: 3, subject: "语文", grade: "七年级", pub: "人教", added: false },
  { id: 4, subject: "道德与法治", grade: "七年级", pub: "人教", added: false },
  { id: 5, subject: "历史", grade: "七年级", pub: "人教", added: false },
  { id: 6, subject: "地理", grade: "七年级", pub: "人教", added: false },
  { id: 7, subject: "生物", grade: "七年级", pub: "人教", added: false },
  { id: 8, subject: "数学", grade: "七年级", pub: "北师", added: false },
  { id: 9, subject: "数学", grade: "七年级", pub: "沪教", added: false },
  { id: 10, subject: "数学", grade: "七年级", pub: "苏教", added: false },
  { id: 11, subject: "语文", grade: "七年级", pub: "苏教", added: false },
  { id: 12, subject: "数学", grade: "八年级", pub: "人教", added: false },
  { id: 13, subject: "英语", grade: "八年级", pub: "人教", added: false },
  { id: 14, subject: "物理", grade: "八年级", pub: "人教", added: false },
  { id: 15, subject: "语文", grade: "八年级", pub: "人教", added: false },
  { id: 16, subject: "道德与法治", grade: "八年级", pub: "人教", added: false },
  { id: 17, subject: "历史", grade: "八年级", pub: "人教", added: false },
  { id: 18, subject: "数学", grade: "八年级", pub: "北师", added: false },
  { id: 19, subject: "数学", grade: "八年级", pub: "沪教", added: false },
  { id: 20, subject: "数学", grade: "八年级", pub: "苏教", added: false },
  { id: 21, subject: "语文", grade: "八年级", pub: "苏教", added: false },
  { id: 22, subject: "数学", grade: "九年级", pub: "人教", added: false },
  { id: 23, subject: "英语", grade: "九年级", pub: "人教", added: false },
  { id: 24, subject: "物理", grade: "九年级", pub: "人教", added: false },
  { id: 25, subject: "化学", grade: "九年级", pub: "人教", added: false },
  { id: 26, subject: "语文", grade: "九年级", pub: "人教", added: false },
  { id: 27, subject: "数学", grade: "九年级", pub: "北师", added: false },
  { id: 28, subject: "数学", grade: "九年级", pub: "沪教", added: false },
  { id: 29, subject: "语文", grade: "九年级", pub: "苏教", added: false },
];

const SUBJECTS = ["数学","英语","语文","物理","化学","历史","地理","道法","生物"];
const GRADES = ["全部年级","七年级","八年级","九年级"];
const PUBS = ["全部出版社","人教","北师","沪教","苏教"];

Page({
  data: {
    userInfo: {
      name: "李明",
      grade: "七年级",
      class: "（3）班",
      studentId: "学号 2024001",
      parentBound: false,
      todayMood: 0.8,
    } as {
      name: string; grade: string; class: string;
      studentId: string; parentBound: boolean; todayMood: number;
    },
    wrongBookCount: 12,
    subjectList: ["全部科目", ...SUBJECTS],
    gradeList: GRADES,
    pubList: PUBS,
    selSubject: 0, selGrade: 0, selPub: 0,
    showResult: false,
    filterResult: [] as Book[],
    myBooks: [] as Book[],
    bookGroups: [] as { subject: string; open: boolean; books: Book[] }[],
    manageMode: false,
    todoList: [] as Todo[],
    sourceMap: { auto: "自动", manual: "手动", psych: "心理任务" } as Record<string, string>,
  },

  onLoad() {
    this.loadUserInfo();
    this.loadTodos();
    this.loadMyBooks();
    this.loadWrongBookCount();
  },

  loadUserInfo() {
    const info = wx.getStorageSync("user_info");
    if (info) {
      this.setData({ userInfo: info });
    }
  },

  onBindParent() {
    const { userInfo } = this.data;
    if (userInfo.parentBound) {
      wx.showModal({
        title: "已绑定家长",
        content: `${userInfo.name}的家长`,
        showCancel: false,
      });
      return;
    }
    wx.scanCode({
      success: (res) => {
        const result = res.result as string;
        const match = result.match(/nuanxue:\/\/bind\/(.+)/);
        if (!match) {
          wx.showToast({ title: "二维码无效", icon: "none" });
          return;
        }
        const token = match[1];
        const childId = getUserId('student');
        wx.showLoading({ title: '绑定中...', mask: true });
        bindParentByToken(token, childId)
          .then((apiRes: any) => {
            wx.hideLoading();
            if (apiRes.success) {
              const updated = { ...this.data.userInfo, parentBound: true };
              wx.setStorageSync("user_info", updated);
              this.setData({ userInfo: updated });
              wx.showToast({ title: "绑定成功", icon: "success" });
            } else {
              wx.showToast({ title: apiRes.error || "绑定失败", icon: "none" });
            }
          })
          .catch(() => {
            wx.hideLoading();
            wx.showToast({ title: "绑定失败，请重试", icon: "none" });
          });
      },
      fail: () => {
        wx.showToast({ title: "扫码失败", icon: "none" });
      },
    });
  },

  loadWrongBookCount() {
    const count = wx.getStorageSync("wrong_book_count");
    if (count) this.setData({ wrongBookCount: count });
  },

  onFeatureTap(e: any) {
    const type = e.currentTarget.dataset.type as string;
    switch (type) {
      case "textbook":
        wx.pageScrollTo({ selector: ".section", duration: 300 });
        break;
      case "grade":
        wx.showModal({
          title: "智学网查成绩",
          content: "智学网接口对接开发中，预计下次版本可用。届时可一键同步历次考试成绩。",
          showCancel: false,
          confirmText: "我知道了",
        });
        break;
      case "aitest":
        wx.showModal({
          title: "AI出题测试",
          content: "选择教材和知识点，AI将生成一套专属练习题。\n\n功能开发中，敬请期待！",
          showCancel: false,
          confirmText: "期待",
        });
        break;
      case "analysis":
        wx.showModal({
          title: "成绩分析",
          content: "根据你的成绩数据，AI将诊断薄弱知识点并推荐学习节奏调整方案。\n\n功能开发中！",
          showCancel: false,
          confirmText: "期待",
        });
        break;
      case "wrongbook":
        wx.showModal({
          title: "错题本",
          content: `已收录 ${this.data.wrongBookCount} 道错题\n\n点击任意题目可查看详细解答和同类题练习`,
          confirmText: "去看看",
          cancelText: "先不做",
          success: (res: any) => {
            if (res.confirm) {
              wx.showToast({ title: "功能开发中", icon: "none" });
            }
          },
        });
        break;
    }
  },

  loadTodos() {
    const list: Todo[] = wx.getStorageSync("todo_list") || [];
    const hasPsychTodo = list.some((t: Todo) => t.source === "psych");
    if (!hasPsychTodo) {
      list.unshift({
        id: Date.now(), text: "完成今日心理状态打卡", done: false,
        source: "psych",
      });
    }
    this.setData({ todoList: list });
  },

  onAddTodo() {
    wx.showModal({
      title: "添加任务",
      editable: true,
      placeholderText: "输入任务内容",
      success: (res: any) => {
        if (res.confirm && res.content && res.content.trim()) {
          const list: Todo[] = [...this.data.todoList];
          list.push({
            id: Date.now(), text: res.content.trim(),
            done: false, source: "manual",
          });
          wx.setStorageSync("todo_list", list);
          this.setData({ todoList: list });
          wx.showToast({ title: "已添加", icon: "success" });
        }
      },
    });
  },

  onToggleTodo(e: any) {
    const id = e.currentTarget.dataset.id;
    const list: Todo[] = this.data.todoList.map((t: Todo) =>
      t.id === id ? { ...t, done: !t.done } : t
    );
    wx.setStorageSync("todo_list", list);
    this.setData({ todoList: list });
  },

  onDelTodo(e: any) {
    const id = e.currentTarget.dataset.id;
    const list: Todo[] = this.data.todoList.filter((t: Todo) => t.id !== id);
    wx.setStorageSync("todo_list", list);
    this.setData({ todoList: list });
  },

  onSubjectChange(e: any) {
    this.setData({ selSubject: e.detail.value, showResult: false });
  },
  onGradeChange(e: any) {
    this.setData({ selGrade: e.detail.value, showResult: false });
  },
  onPubChange(e: any) {
    this.setData({ selPub: e.detail.value, showResult: false });
  },

  onConfirmFilter() {
    const { selSubject, selGrade, selPub } = this.data;
    const sub = SUBJECTS[selSubject - 1] || "";
    const grade = GRADES[selGrade] || "";
    const pub = PUBS[selPub] || "";
    const myIds: number[] = wx.getStorageSync("my_book_ids") || [];

    let result = ALL_BOOKS;
    if (sub) result = result.filter((b) => b.subject === sub);
    if (grade !== "全部年级") result = result.filter((b) => b.grade === grade);
    if (pub !== "全部出版社") result = result.filter((b) => b.pub === pub);

    const books = result.map((b) => ({ ...b, added: myIds.indexOf(b.id) >= 0 }));
    this.setData({ filterResult: books, showResult: true });
  },

  loadMyBooks() {
    const ids: number[] = wx.getStorageSync("my_book_ids") || [];
    const myBooks = ALL_BOOKS.filter((b) => ids.indexOf(b.id) >= 0);
    this.setData({ myBooks });
    this.buildGroups(myBooks);
  },

  buildGroups(books: Book[]) {
    const map: Record<string, Book[]> = {};
    for (const b of books) {
      if (!map[b.subject]) map[b.subject] = [];
      map[b.subject].push(b);
    }
    const groups = Object.keys(map).map((subject) => ({
      subject, open: false, books: map[subject],
    }));
    this.setData({ bookGroups: groups });
  },

  onAddMyBook(e: any) {
    const id = e.currentTarget.dataset.id;
    const ids: number[] = wx.getStorageSync("my_book_ids") || [];
    if (ids.indexOf(id) < 0) {
      ids.push(id);
      wx.setStorageSync("my_book_ids", ids);
    }
    const filterResult = this.data.filterResult.map((b: Book) =>
      b.id === id ? { ...b, added: true } : b
    );
    const myBooks = ALL_BOOKS.filter((b) => ids.indexOf(b.id) >= 0);
    this.setData({ filterResult, myBooks });
    this.buildGroups(myBooks);
    wx.showToast({ title: "已添加", icon: "success", duration: 800 });
  },

  onDelMyBook(e: any) {
    const id = e.currentTarget.dataset.id;
    let ids: number[] = wx.getStorageSync("my_book_ids") || [];
    ids = ids.filter((i: number) => i !== id);
    wx.setStorageSync("my_book_ids", ids);
    const myBooks = ALL_BOOKS.filter((b) => ids.indexOf(b.id) >= 0);
    this.setData({ myBooks });
    this.buildGroups(myBooks);
    wx.showToast({ title: "已删除", icon: "none", duration: 800 });
  },

  onManageBooks() {
    this.setData({ manageMode: !this.data.manageMode });
  },

  onToggleGroup(e: any) {
    const sub = e.currentTarget.dataset.sub;
    const groups = this.data.bookGroups.map((g: any) =>
      g.subject === sub ? { ...g, open: !g.open } : g
    );
    this.setData({ bookGroups: groups });
  },

  onQueryGrade(e: any) {
    const book: Book = e.currentTarget.dataset.book;
    wx.showModal({
      title: book.subject + " · " + book.grade,
      content: "成绩查询功能接入智学网接口后可用\n目前显示最近成绩",
      showCancel: false,
    });
  },
});
