import { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Toggle } from "../../../components/ui/Toggle";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { notificationService } from "../../../services/notificationService";
import type { AppNotification, NotificationCategory, NotificationPreference } from "../../../types/growth";
import { SkeletonList } from "../../../components/ui/Skeleton";

const CATEGORIES: NotificationCategory[] = ["ORDER", "PAYMENT", "DELIVERY", "PROMOTION", "REVIEW", "PAYOUT", "ADVERTISING", "ACCOUNT"];
const CHANNELS: Array<"EMAIL" | "SMS" | "PUSH"> = ["EMAIL", "SMS", "PUSH"];

export function NotificationsPage() {
  const { showError } = useToast();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    Promise.all([notificationService.list(false, 1), notificationService.getPreferences()])
      .then(([n, p]) => {
        setNotifications(n.notifications);
        setPreferences(p);
      })
      .catch(() => showError("Could not load your notifications."))
      .finally(() => setLoading(false));
  }

  useEffect(load, [showError]);

  function isEnabled(category: NotificationCategory, channel: "EMAIL" | "SMS" | "PUSH") {
    const pref = preferences.find((p) => p.category === category && p.channel === channel);
    return pref ? pref.enabled : true;
  }

  async function togglePreference(category: NotificationCategory, channel: "EMAIL" | "SMS" | "PUSH") {
    const next = !isEnabled(category, channel);
    try {
      const updated = await notificationService.setPreference(category, channel, next);
      setPreferences((prev) => {
        const rest = prev.filter((p) => !(p.category === category && p.channel === channel));
        return [...rest, updated];
      });
    } catch {
      showError("Could not update that preference.");
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Notifications</h1>
            <p className="text-ink-soft mt-1">Everything we've let you know about, and how you'd like to hear from us.</p>
          </div>
          {notifications.some((n) => !n.is_read) && (
            <Button size="sm" variant="secondary" onClick={() => notificationService.markAllRead().then(load)}>
              <Check className="h-3.5 w-3.5" /> Mark all read
            </Button>
          )}
        </div>

        {loading ? (
          <SkeletonList />
        ) : notifications.length === 0 ? (
          <EmptyState icon={<Bell className="h-5 w-5" />} title="No notifications yet" description="We'll let you know when something happens." />
        ) : (
          <Card>
            <CardBody className="space-y-0 divide-y divide-line">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0 ${notification.is_read ? "" : "bg-primary-soft/30 -mx-4 px-4"}`}
                >
                  <div>
                    <p className="text-sm font-medium text-ink">{notification.title}</p>
                    <p className="mt-0.5 text-sm text-ink-soft">{notification.body}</p>
                    <p className="mt-1 text-xs text-ink-soft">{new Date(notification.created_at).toLocaleString()}</p>
                  </div>
                  {!notification.is_read && (
                    <button
                      className="shrink-0 text-xs text-primary hover:underline"
                      onClick={() => notificationService.markRead(notification.id).then(load)}
                    >
                      Mark read
                    </button>
                  )}
                </div>
              ))}
            </CardBody>
          </Card>
        )}

        <Card>
          <CardHeader>
            <p className="font-medium text-ink">Email, SMS &amp; push preferences</p>
          </CardHeader>
          <CardBody className="space-y-3">
            <p className="text-xs text-ink-soft">In-app notifications always appear here. Turn channels on or off per topic below.</p>
            <div className="space-y-2">
              {CATEGORIES.map((category) => (
                <div key={category} className="flex items-center justify-between gap-3 py-1.5">
                  <span className="text-sm text-ink capitalize">{category.toLowerCase()}</span>
                  <div className="flex items-center gap-4">
                    {CHANNELS.map((channel) => (
                      <label key={channel} className="flex items-center gap-1.5 text-xs text-ink-soft">
                        {channel}
                        <Toggle checked={isEnabled(category, channel)} onChange={() => togglePreference(category, channel)} />
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>
    </DashboardLayout>
  );
}
