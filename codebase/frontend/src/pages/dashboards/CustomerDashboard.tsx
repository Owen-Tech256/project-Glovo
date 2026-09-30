import { ShoppingBag, MapPin, ShoppingCart, ClipboardList } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { AccountSummaryCard } from "../../components/AccountSummaryCard";
import { FeatureLinkCard } from "../../components/FeatureLinkCard";
import { useAuth } from "../../context/AuthContext";

export function CustomerDashboard() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Welcome back, {user.full_name.split(" ")[0]}</h1>
          <p className="text-ink-soft mt-1">Here's your account at a glance.</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1">
            <AccountSummaryCard user={user} />
          </div>
          <div className="lg:col-span-2 grid sm:grid-cols-2 gap-4">
            <FeatureLinkCard
              icon={<ShoppingBag className="h-4.5 w-4.5" />}
              title="Browse vendors"
              description="Discover local shops and restaurants near you."
              to="/customer/dashboard/vendors"
            />
            <FeatureLinkCard
              icon={<ShoppingCart className="h-4.5 w-4.5" />}
              title="Cart"
              description="Review items you've added and check out."
              to="/customer/dashboard/cart"
            />
            <FeatureLinkCard
              icon={<ClipboardList className="h-4.5 w-4.5" />}
              title="My orders"
              description="Track current orders and view past ones."
              to="/customer/dashboard/orders"
            />
            <FeatureLinkCard
              icon={<MapPin className="h-4.5 w-4.5" />}
              title="Manage addresses"
              description="Save delivery addresses for faster checkout."
              to="/customer/dashboard/addresses"
            />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
