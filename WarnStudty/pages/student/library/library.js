const API_BASE = 'https://wsapi.supermoxi.top';

function request(url, data, method) {
  method = method || 'POST';
  return new Promise(function(resolve, reject) {
    wx.request({
      url: API_BASE + url,
      data: data,
      method: method,
      header: { 'Content-Type': 'application/json' },
      success: function(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error('请求失败: ' + res.statusCode));
        }
      },
      fail: function(err) {
        reject(err);
      },
    });
  });
}

function bindParentByToken(token, childId) {
  return request('/api/child/bind', { token: token, child_id: childId });
}

function isValidStudentId(value) {
  return /^\d{9}$/.test(String(value || '').trim());
}

function ensureStudentId() {
  var existing =
    wx.getStorageSync('student_user_id') ||
    (wx.getStorageSync('user_role') === 'student' ? wx.getStorageSync('user_id') : '');
  if (isValidStudentId(existing)) {
    wx.setStorageSync('student_user_id', existing);
    wx.setStorageSync('student_id', existing);
    return existing;
  }
  var generated = String(Math.floor(100000000 + Math.random() * 900000000));
  wx.setStorageSync('student_user_id', generated);
  wx.setStorageSync('student_id', generated);
  if (!wx.getStorageSync('user_id')) {
    wx.setStorageSync('user_id', generated);
    wx.setStorageSync('user_role', 'student');
  }
  return generated;
}

function getUserId(role) {
  return ensureStudentId();
}

var ALL_BOOKS = [
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

var SUBJECTS = ["数学","英语","语文","物理","化学","历史","地理","道法","生物"];
var GRADES = ["全部年级","七年级","八年级","九年级"];
var PUBS = ["全部出版社","人教","北师","沪教","苏教"];

Page({
  data: {
    userInfo: {
      name: "李明",
      grade: "七年级",
      class: "（3）班",
      studentId: "",
      parentBound: false,
      todayMood: 0.8,
    },
    wrongBookCount: 12,
    subjectList: ["全部科目"].concat(SUBJECTS),
    gradeList: GRADES,
    pubList: PUBS,
    selSubject: 0, selGrade: 0, selPub: 0,
    showResult: false,
    filterResult: [],
    myBooks: [],
    bookGroups: [],
    manageMode: false,
    todoList: [],
    sourceMap: { auto: "自动", manual: "手动", psych: "心理任务" },
  },

  onLoad: function() {
    this.loadUserInfo();
    this.loadTodos();
    this.loadMyBooks();
    this.loadWrongBookCount();
  },

  loadUserInfo: function() {
    var info = wx.getStorageSync("user_info");
    var studentId = ensureStudentId();
    if (info) {
      this.setData({ userInfo: Object.assign({}, info, { studentId: studentId }) });
    } else {
      this.setData({ userInfo: Object.assign({}, this.data.userInfo, { studentId: studentId }) });
    }
  },

  onCopyStudentId: function() {
    var studentId = ensureStudentId();
    wx.setClipboardData({
      data: studentId,
      success: function() {
        wx.showToast({ title: "孩子ID已复制", icon: "success" });
      },
    });
  },

  onBindParent: function() {
    var self = this;
    var userInfo = this.data.userInfo;
    if (userInfo.parentBound) {
      wx.showModal({
        title: "已绑定家长",
        content: userInfo.name + "的家长",
        showCancel: false,
      });
      return;
    }
    wx.scanCode({
      success: function(res) {
        var result = res.result;
        var match = result.match(/nuanxue:\/\/bind\/(.+)/);
        if (!match) {
          wx.showToast({ title: "二维码无效", icon: "none" });
          return;
        }
        var token = match[1];
        var childId = getUserId('student');
        wx.showLoading({ title: '绑定中...', mask: true });
        bindParentByToken(token, childId)
          .then(function(apiRes) {
            wx.hideLoading();
            if (apiRes.success) {
              var updated = Object.assign({}, self.data.userInfo, { parentBound: true });
              wx.setStorageSync("user_info", updated);
              self.setData({ userInfo: updated });
              wx.showToast({ title: "绑定成功", icon: "success" });
            } else {
              wx.showToast({ title: apiRes.error || "绑定失败", icon: "none" });
            }
          })
          .catch(function() {
            wx.hideLoading();
            wx.showToast({ title: "绑定失败，请重试", icon: "none" });
          });
      },
      fail: function() {
        wx.showToast({ title: "扫码失败", icon: "none" });
      },
    });
  },

  loadWrongBookCount: function() {
    var count = wx.getStorageSync("wrong_book_count");
    if (count) this.setData({ wrongBookCount: count });
  },

  onFeatureTap: function(e) {
    var type = e.currentTarget.dataset.type;
    var self = this;
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
          content: "已收录 " + self.data.wrongBookCount + " 道错题\n\n点击任意题目可查看详细解答和同类题练习",
          confirmText: "去看看",
          cancelText: "先不做",
          success: function(res) {
            if (res.confirm) {
              wx.showToast({ title: "功能开发中", icon: "none" });
            }
          },
        });
        break;
    }
  },

  loadTodos: function() {
    var list = wx.getStorageSync("todo_list") || [];
    var hasPsychTodo = list.some(function(t) { return t.source === "psych"; });
    if (!hasPsychTodo) {
      list.unshift({
        id: Date.now(), text: "完成今日心理状态打卡", done: false,
        source: "psych",
      });
    }
    this.setData({ todoList: list });
  },

  onAddTodo: function() {
    var self = this;
    wx.showModal({
      title: "添加任务",
      editable: true,
      placeholderText: "输入任务内容",
      success: function(res) {
        if (res.confirm && res.content && res.content.trim()) {
          var list = self.data.todoList.slice();
          list.push({
            id: Date.now(), text: res.content.trim(),
            done: false, source: "manual",
          });
          wx.setStorageSync("todo_list", list);
          self.setData({ todoList: list });
          wx.showToast({ title: "已添加", icon: "success" });
        }
      },
    });
  },

  onToggleTodo: function(e) {
    var id = e.currentTarget.dataset.id;
    var list = this.data.todoList.map(function(t) {
      return t.id === id ? Object.assign({}, t, { done: !t.done }) : t;
    });
    wx.setStorageSync("todo_list", list);
    this.setData({ todoList: list });
  },

  onDelTodo: function(e) {
    var id = e.currentTarget.dataset.id;
    var list = this.data.todoList.filter(function(t) { return t.id !== id; });
    wx.setStorageSync("todo_list", list);
    this.setData({ todoList: list });
  },

  onSubjectChange: function(e) {
    this.setData({ selSubject: e.detail.value, showResult: false });
  },
  onGradeChange: function(e) {
    this.setData({ selGrade: e.detail.value, showResult: false });
  },
  onPubChange: function(e) {
    this.setData({ selPub: e.detail.value, showResult: false });
  },

  onConfirmFilter: function() {
    var selSubject = this.data.selSubject;
    var selGrade = this.data.selGrade;
    var selPub = this.data.selPub;
    var sub = SUBJECTS[selSubject - 1] || "";
    var grade = GRADES[selGrade] || "";
    var pub = PUBS[selPub] || "";
    var myIds = wx.getStorageSync("my_book_ids") || [];

    var result = ALL_BOOKS.slice();
    if (sub) result = result.filter(function(b) { return b.subject === sub; });
    if (grade !== "全部年级") result = result.filter(function(b) { return b.grade === grade; });
    if (pub !== "全部出版社") result = result.filter(function(b) { return b.pub === pub; });

    var books = result.map(function(b) { return Object.assign({}, b, { added: myIds.indexOf(b.id) >= 0 }); });
    this.setData({ filterResult: books, showResult: true });
  },

  loadMyBooks: function() {
    var ids = wx.getStorageSync("my_book_ids") || [];
    var myBooks = ALL_BOOKS.filter(function(b) { return ids.indexOf(b.id) >= 0; });
    this.setData({ myBooks: myBooks });
    this.buildGroups(myBooks);
  },

  buildGroups: function(books) {
    var map = {};
    for (var i = 0; i < books.length; i++) {
      var b = books[i];
      if (!map[b.subject]) map[b.subject] = [];
      map[b.subject].push(b);
    }
    var groups = Object.keys(map).map(function(subject) {
      return { subject: subject, open: false, books: map[subject] };
    });
    this.setData({ bookGroups: groups });
  },

  onAddMyBook: function(e) {
    var id = e.currentTarget.dataset.id;
    var ids = wx.getStorageSync("my_book_ids") || [];
    if (ids.indexOf(id) < 0) {
      ids.push(id);
      wx.setStorageSync("my_book_ids", ids);
    }
    var filterResult = this.data.filterResult.map(function(b) {
      return b.id === id ? Object.assign({}, b, { added: true }) : b;
    });
    var myBooks = ALL_BOOKS.filter(function(b) { return ids.indexOf(b.id) >= 0; });
    this.setData({ filterResult: filterResult, myBooks: myBooks });
    this.buildGroups(myBooks);
    wx.showToast({ title: "已添加", icon: "success", duration: 800 });
  },

  onDelMyBook: function(e) {
    var id = e.currentTarget.dataset.id;
    var ids = wx.getStorageSync("my_book_ids") || [];
    ids = ids.filter(function(i) { return i !== id; });
    wx.setStorageSync("my_book_ids", ids);
    var myBooks = ALL_BOOKS.filter(function(b) { return ids.indexOf(b.id) >= 0; });
    this.setData({ myBooks: myBooks });
    this.buildGroups(myBooks);
    wx.showToast({ title: "已删除", icon: "none", duration: 800 });
  },

  onManageBooks: function() {
    this.setData({ manageMode: !this.data.manageMode });
  },

  onToggleGroup: function(e) {
    var sub = e.currentTarget.dataset.sub;
    var groups = this.data.bookGroups.map(function(g) {
      return g.subject === sub ? Object.assign({}, g, { open: !g.open }) : g;
    });
    this.setData({ bookGroups: groups });
  },

  onQueryGrade: function(e) {
    var book = e.currentTarget.dataset.book;
    wx.showModal({
      title: book.subject + " · " + book.grade,
      content: "成绩查询功能接入智学网接口后可用\n目前显示最近成绩",
      showCancel: false,
    });
  },
});
