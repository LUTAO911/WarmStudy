const { getChildPsychReportDetail } = require("../../../utils/api.js");

const LEVEL_LABELS: Record<string, string> = {
  normal: "正常",
  mild: "轻度",
  moderate: "中度",
  concerning: "偏高",
  severe: "严重",
};

const LEVEL_DESCS: Record<string, string> = {
  normal: "心理状态良好",
  mild: "存在轻度波动",
  moderate: "存在一定压力",
  concerning: "需要关注",
  severe: "建议就医",
};

const TYPE_LABELS: Record<string, string> = {
  weekly: "心理健康综合评估",
  pressure: "感知压力评估",
  communication: "亲子沟通评估",
};

Page({
  data: {
    report: null as any,
    reportLevelLabel: LEVEL_LABELS,
    reportTypeLabel: TYPE_LABELS,
    levelDesc: "",
    levelClass: "",
  },

  onLoad(options: any) {
    if (options.id) {
      this.loadReportDetail(options.id);
    }
    if (options.child_id) {
      this.setData({ childId: options.child_id });
    }
  },

  loadReportDetail(reportId: number) {
    wx.showLoading({ title: "加载中..." });
    getChildPsychReportDetail(String(reportId))
      .then((res: any) => {
        wx.hideLoading();
        if (res.success && res.report) {
          const report = res.report;
          const level = report.level || "normal";
          this.setData({
            report,
            levelDesc: LEVEL_DESCS[level] || "",
            levelClass: level,
          });
          wx.setNavigationBarTitle({
            title: TYPE_LABELS[report.scale_id] || "心理测评报告",
          });
        } else {
          wx.showToast({ title: "加载失败", icon: "none" });
        }
      })
      .catch(() => {
        wx.hideLoading();
        wx.showToast({ title: "加载失败", icon: "none" });
      });
  },
});
