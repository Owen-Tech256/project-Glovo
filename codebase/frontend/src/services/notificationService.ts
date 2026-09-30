import { apiClient } from "./apiClient";
import type { ApiSuccess } from "../types/auth";
import type { AppNotification, NotificationPreference, NotificationTemplate } from "../types/growth";

export const notificationService = {
  async list(unreadOnly = false, page = 1) {
    const { data } = await apiClient.get<ApiSuccess<{ notifications: AppNotification[]; unread_count: number }>>(
      "/notifications", { params: { unread_only: unreadOnly, page } }
    );
    return data.data;
  },
  async markRead(notificationId: string) {
    const { data } = await apiClient.patch<ApiSuccess<{ notification: AppNotification }>>(`/notifications/${notificationId}/read`);
    return data.data.notification;
  },
  async markAllRead() {
    await apiClient.post("/notifications/read-all");
  },
  async getPreferences() {
    const { data } = await apiClient.get<ApiSuccess<{ preferences: NotificationPreference[] }>>("/notifications/preferences");
    return data.data.preferences;
  },
  async setPreference(category: string, channel: string, enabled: boolean) {
    const { data } = await apiClient.put<ApiSuccess<{ preference: NotificationPreference }>>("/notifications/preferences", {
      category, channel, enabled,
    });
    return data.data.preference;
  },

  // --- Admin templates ---
  async listTemplates() {
    const { data } = await apiClient.get<ApiSuccess<{ templates: NotificationTemplate[] }>>("/admin/notification-templates");
    return data.data.templates;
  },
  async createTemplate(input: { key: string; channel: string; category: string; title_template: string; body_template: string }) {
    const { data } = await apiClient.post<ApiSuccess<{ template: NotificationTemplate }>>("/admin/notification-templates", input);
    return data.data.template;
  },
  async updateTemplate(templateId: string, input: Partial<{ title_template: string; body_template: string; category: string; status: string }>) {
    const { data } = await apiClient.patch<ApiSuccess<{ template: NotificationTemplate }>>(`/admin/notification-templates/${templateId}`, input);
    return data.data.template;
  },
};
