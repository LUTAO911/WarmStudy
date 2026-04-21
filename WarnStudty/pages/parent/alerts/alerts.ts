const api = require("../../../utils/api.js");
const { getParentAlerts, markAlertRead, markAllAlertsRead } = api;

// 定义 ParentAlert 类型
interface ParentAlert {
  id: number;
  child_id: string;
  child_name: string;
  alert_type: string;
  title: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

const alertTypeMap: Record<
  string,
  { icon: string; color: string; label: string; bg: string }
> = {
  emotion_drop: { icon: "😊", color: "#ff9800", label: "情绪", bg: "#fff8e1" },
  no_checkin: { icon: "📋", color: "#9e9e9e", label: "打卡", bg: "#f5f5f5" },
  test_concerning: {
    icon: "📊",
    color: "#f44336",
    label: "测评",
    bg: "#ffebee",
  },
  chat_silence: { icon: "💬", color: "#2196f3", label: "互动", bg: "#e3f2fd" },
};

Page({
  data: {
    alerts: [] as ParentAlert[],
    loading: false,
    hasMore: true,
    offset: 0,
    limit: 20,
    alertTypeMap,
  },

  onLoad() {
    this.loadAlerts(true);
  },

  onShow() {
    // 每次进来刷新未读数（已读状态可能变了）
    this.loadAlerts(false);
  },

  loadAlerts(reset: boolean) {
    if (this.data.loading) return;
    const account = wx.getStorageSync("parent_account") || {};
    const parentId = String(
      account.id || wx.getStorageSync("parent_user_id") || "parent_001",
    );
    const offset = reset ? 0 : this.data.offset;

    this.setData({ loading: true });
    getParentAlerts(parentId, this.data.limit, offset)
      .then((res: any) => {
        if (res.success) {
          const alerts = reset
            ? res.alerts
            : [...this.data.alerts, ...res.alerts];
          this.setData({
            alerts,
            offset: offset + res.alerts.length,
            hasMore: res.alerts.length >= this.data.limit,
          });
        }
      })
      .catch(() => {
        wx.showToast({ title: "加载失败", icon: "none" });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onTapAlert(e: any) {
    const alert = e.currentTarget.dataset.alert as ParentAlert;
    if (!alert.is_read) {
      const account = wx.getStorageSync("parent_account") || {};
      const parentId = String(
        account.id || wx.getStorageSync("parent_user_id") || "parent_001",
      );
      markAlertRead(alert.id, parentId)
        .then(() => {
          // 更新本地状态
          const alerts = this.data.alerts.map((a) =>
            a.id === alert.id ? { ...a, is_read: true } : a,
          );
          this.setData({ alerts });
        })
        .catch(() => {});
    }
  },

  onMarkAllRead() {
    const account = wx.getStorageSync("parent_account") || {};
    const parentId = String(
      account.id || wx.getStorageSync("parent_user_id") || "parent_001",
    );
    markAllAlertsRead(parentId)
      .then((res: any) => {
        if (res.success) {
          const alerts = this.data.alerts.map((a) => ({ ...a, is_read: true }));
          this.setData({ alerts });
          wx.showToast({
            title: `已读 ${res.marked_count} 条`,
            icon: "success",
          });
        }
      })
      .catch(() => {});
  },

  onReachBottom() {
    if (this.data.hasMore) {
      this.loadAlerts(false);
    }
  },
});
