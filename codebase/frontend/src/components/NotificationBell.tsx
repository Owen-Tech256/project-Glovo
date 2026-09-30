import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { notificationService } from "../services/notificationService";
import type { AppNotification } from "../types/growth";

const CATEGORY_ROUTE: Record<string, string> = {
  ORDER: "orders",
  PAYMENT: "orders",
  DELIVERY: "orders",
  REVIEW: "orders",
};

export function NotificationBell({ basePath }: { basePath: string }) {
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  function refresh() {
    notificationService
      .list(false, 1)
      .then((result) => {
        setUnreadCount(result.unread_count);
        setNotifications(result.notifications.slice(0, 6));
      })
      .catch(() => {});
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  async function handleOpenNotification(notification: AppNotification) {
    if (!notification.is_read) {
      await notificationService.markRead(notification.id).catch(() => {});
    }
    setOpen(false);
    refresh();
    const section = CATEGORY_ROUTE[notification.category];
    if (section && notification.entity_type === "ORDER" && notification.entity_id) {
      navigate(`${basePath}/${section}/${notification.entity_id}`);
    } else {
      navigate(`${basePath}/notifications`);
    }
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
        className="relative rounded-full p-2 text-ink-soft hover:bg-ink/[0.04] hover:text-ink transition-colors"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-lg border border-line bg-paper-raised shadow-lg">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <p className="text-sm font-medium text-ink">Notifications</p>
            {unreadCount > 0 && (
              <button
                className="text-xs text-primary hover:underline"
                onClick={() => notificationService.markAllRead().then(refresh)}
              >
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-ink-soft">You're all caught up.</p>
            ) : (
              notifications.map((notification) => (
                <button
                  key={notification.id}
                  onClick={() => handleOpenNotification(notification)}
                  className={`block w-full border-b border-line px-4 py-2.5 text-left last:border-0 hover:bg-ink/[0.03] ${
                    notification.is_read ? "" : "bg-primary-soft/40"
                  }`}
                >
                  <p className="text-sm font-medium text-ink">{notification.title}</p>
                  <p className="mt-0.5 text-xs text-ink-soft line-clamp-2">{notification.body}</p>
                </button>
              ))
            )}
          </div>
          <button
            onClick={() => {
              setOpen(false);
              navigate(`${basePath}/notifications`);
            }}
            className="block w-full rounded-b-lg border-t border-line px-4 py-2.5 text-center text-xs font-medium text-primary hover:bg-ink/[0.03]"
          >
            See all notifications
          </button>
        </div>
      )}
    </div>
  );
}
