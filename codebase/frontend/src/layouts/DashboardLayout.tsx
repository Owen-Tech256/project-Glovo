import { useState, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  LogOut,
  Menu,
  X,
  User as UserIcon,
  ShoppingBag,
  Store,
  Bike,
  Shield,
  Users,
  MapPin,
  Tag,
  Package,
  ShoppingCart,
  ClipboardList,
  Truck,
  FileCheck,
  Wallet,
  Landmark,
  Megaphone,
  Star,
  Sparkles,
  LifeBuoy,
  Gavel,
  BarChart3,
  FileBarChart,
  KeyRound,
} from "lucide-react";
import { BrandWordmark } from "../components/Logo";
import { NotificationBell } from "../components/NotificationBell";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useFocusTrap } from "../hooks/useFocusTrap";
import type { UserRole } from "../types/auth";
import { Badge } from "../components/ui/Badge";

interface NavItem {
  label: string;
  to: string;
  icon: ReactNode;
  end?: boolean;
}

const navByRole: Record<UserRole, NavItem[]> = {
  CUSTOMER: [
    { label: "Overview", to: "/customer/dashboard", icon: <LayoutDashboard className="h-4 w-4" />, end: true },
    { label: "Browse vendors", to: "/customer/dashboard/vendors", icon: <ShoppingBag className="h-4 w-4" /> },
    { label: "Cart", to: "/customer/dashboard/cart", icon: <ShoppingCart className="h-4 w-4" /> },
    { label: "My orders", to: "/customer/dashboard/orders", icon: <ClipboardList className="h-4 w-4" /> },
    { label: "Promotions", to: "/customer/dashboard/promotions", icon: <Tag className="h-4 w-4" /> },
    { label: "Addresses", to: "/customer/dashboard/addresses", icon: <MapPin className="h-4 w-4" /> },
    { label: "Support", to: "/customer/dashboard/support", icon: <LifeBuoy className="h-4 w-4" /> },
    { label: "My account", to: "/customer/dashboard/account", icon: <UserIcon className="h-4 w-4" /> },
  ],
  VENDOR: [
    { label: "Overview", to: "/vendor/dashboard", icon: <LayoutDashboard className="h-4 w-4" />, end: true },
    { label: "Orders", to: "/vendor/dashboard/orders", icon: <ClipboardList className="h-4 w-4" /> },
    { label: "Payouts", to: "/vendor/dashboard/payouts", icon: <Wallet className="h-4 w-4" /> },
    { label: "Promotions", to: "/vendor/dashboard/promotions", icon: <Tag className="h-4 w-4" /> },
    { label: "Ad campaigns", to: "/vendor/dashboard/campaigns", icon: <Megaphone className="h-4 w-4" /> },
    { label: "Reviews", to: "/vendor/dashboard/reviews", icon: <Star className="h-4 w-4" /> },
    { label: "Business profile", to: "/vendor/dashboard/profile", icon: <Store className="h-4 w-4" /> },
    { label: "Branches", to: "/vendor/dashboard/branches", icon: <MapPin className="h-4 w-4" /> },
    { label: "Categories", to: "/vendor/dashboard/categories", icon: <Tag className="h-4 w-4" /> },
    { label: "Products", to: "/vendor/dashboard/products", icon: <Package className="h-4 w-4" /> },
    { label: "Support", to: "/vendor/dashboard/support", icon: <LifeBuoy className="h-4 w-4" /> },
    { label: "My account", to: "/vendor/dashboard/account", icon: <UserIcon className="h-4 w-4" /> },
  ],
  RIDER: [
    { label: "Overview", to: "/rider/dashboard", icon: <LayoutDashboard className="h-4 w-4" />, end: true },
    { label: "Deliveries", to: "/rider/dashboard/deliveries", icon: <Bike className="h-4 w-4" /> },
    { label: "Wallet", to: "/rider/dashboard/wallet", icon: <Wallet className="h-4 w-4" /> },
    { label: "Reviews", to: "/rider/dashboard/reviews", icon: <Star className="h-4 w-4" /> },
    { label: "Zones", to: "/rider/dashboard/zones", icon: <MapPin className="h-4 w-4" /> },
    { label: "Documents", to: "/rider/dashboard/documents", icon: <FileCheck className="h-4 w-4" /> },
    { label: "Vehicle", to: "/rider/dashboard/vehicle", icon: <Truck className="h-4 w-4" /> },
    { label: "Support", to: "/rider/dashboard/support", icon: <LifeBuoy className="h-4 w-4" /> },
    { label: "My account", to: "/rider/dashboard/account", icon: <UserIcon className="h-4 w-4" /> },
  ],
  ADMIN: [
    { label: "Overview", to: "/admin/dashboard", icon: <LayoutDashboard className="h-4 w-4" />, end: true },
    { label: "Users", to: "/admin/dashboard/users", icon: <Users className="h-4 w-4" /> },
    { label: "Vendors", to: "/admin/dashboard/vendors", icon: <Store className="h-4 w-4" /> },
    { label: "Orders", to: "/admin/dashboard/orders", icon: <ClipboardList className="h-4 w-4" /> },
    { label: "Riders", to: "/admin/dashboard/riders", icon: <Bike className="h-4 w-4" /> },
    { label: "Deliveries", to: "/admin/dashboard/deliveries", icon: <Truck className="h-4 w-4" /> },
    { label: "Finance", to: "/admin/dashboard/finance", icon: <Landmark className="h-4 w-4" /> },
    { label: "Growth", to: "/admin/dashboard/growth", icon: <Sparkles className="h-4 w-4" /> },
    { label: "Support", to: "/admin/dashboard/support", icon: <LifeBuoy className="h-4 w-4" /> },
    { label: "Disputes", to: "/admin/dashboard/disputes", icon: <Gavel className="h-4 w-4" /> },
    { label: "Analytics", to: "/admin/dashboard/analytics", icon: <BarChart3 className="h-4 w-4" /> },
    { label: "Reports", to: "/admin/dashboard/reports", icon: <FileBarChart className="h-4 w-4" /> },
    { label: "Staff & roles", to: "/admin/dashboard/roles", icon: <KeyRound className="h-4 w-4" /> },
  ],
};

const roleLabel: Record<UserRole, string> = {
  CUSTOMER: "Customer",
  VENDOR: "Business",
  RIDER: "Rider",
  ADMIN: "Admin",
};

const dashboardBasePath: Record<UserRole, string> = {
  CUSTOMER: "/customer/dashboard",
  VENDOR: "/vendor/dashboard",
  RIDER: "/rider/dashboard",
  ADMIN: "/admin/dashboard",
};

export function DashboardLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const mobileNavRef = useFocusTrap<HTMLDivElement>(mobileNavOpen, () => setMobileNavOpen(false));

  if (!user) return null;
  const items = navByRole[user.role];

  const handleLogout = async () => {
    try {
      await logout();
      showSuccess("You have been logged out.");
      navigate("/login");
    } catch {
      showError("Something went wrong while logging out.");
    }
  };

  return (
    <div className="min-h-screen bg-paper flex">
      {/* Sidebar - desktop */}
      <aside className="hidden md:flex md:w-64 md:flex-col border-r border-line bg-paper-raised">
        <div className="h-16 flex items-center px-6 border-b border-line">
          <BrandWordmark />
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-primary-soft text-primary-dark" : "text-ink-soft hover:bg-ink/[0.04] hover:text-ink"
                }`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-line">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-ink-soft hover:bg-ink/[0.04] hover:text-ink transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </div>
      </aside>

      {/* Mobile nav drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-ink/40" onClick={() => setMobileNavOpen(false)} />
          <aside ref={mobileNavRef} tabIndex={-1} className="absolute left-0 top-0 h-full w-64 bg-paper-raised flex flex-col">
            <div className="h-16 flex items-center justify-between px-4 border-b border-line">
              <BrandWordmark />
              <button onClick={() => setMobileNavOpen(false)} aria-label="Close menu">
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 px-3 py-4 space-y-1">
              {items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium ${
                      isActive ? "bg-primary-soft text-primary-dark" : "text-ink-soft"
                    }`
                  }
                >
                  {item.icon}
                  {item.label}
                </NavLink>
              ))}
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-ink-soft"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </button>
            </nav>
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-line bg-paper-raised flex items-center justify-between px-4 md:px-8">
          <button className="md:hidden" onClick={() => setMobileNavOpen(true)} aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </button>
          <div className="hidden md:block" />
          <div className="flex items-center gap-3">
            <NotificationBell basePath={dashboardBasePath[user.role]} />
            <Badge tone="primary" icon={<Shield className="h-3 w-3" />}>
              {roleLabel[user.role]}
            </Badge>
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-full bg-primary text-white flex items-center justify-center text-sm font-semibold">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <span className="hidden sm:block text-sm font-medium text-ink">{user.full_name}</span>
            </div>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
