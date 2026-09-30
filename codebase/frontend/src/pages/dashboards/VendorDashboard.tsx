import { Store, Package, BarChart3, MapPin, Tag, ClipboardList } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { AccountSummaryCard } from "../../components/AccountSummaryCard";
import { ComingSoonCard } from "../../components/ComingSoonCard";
import { FeatureLinkCard } from "../../components/FeatureLinkCard";
import { useAuth } from "../../context/AuthContext";

export function VendorDashboard() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Welcome, {user.full_name.split(" ")[0]}</h1>
          <p className="text-ink-soft mt-1">Set up your business profile, locations, and catalog.</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1">
            <AccountSummaryCard user={user} />
          </div>
          <div className="lg:col-span-2 grid sm:grid-cols-2 gap-4">
            <FeatureLinkCard
              icon={<ClipboardList className="h-4.5 w-4.5" />}
              title="Orders"
              description="Accept and prepare incoming orders."
              to="/vendor/dashboard/orders"
            />
            <FeatureLinkCard
              icon={<Store className="h-4.5 w-4.5" />}
              title="Business profile"
              description="Tell customers who you are."
              to="/vendor/dashboard/profile"
            />
            <FeatureLinkCard
              icon={<MapPin className="h-4.5 w-4.5" />}
              title="Branches"
              description="Add and manage your business locations."
              to="/vendor/dashboard/branches"
            />
            <FeatureLinkCard
              icon={<Tag className="h-4.5 w-4.5" />}
              title="Categories"
              description="Organize your catalog into groups."
              to="/vendor/dashboard/categories"
            />
            <FeatureLinkCard
              icon={<Package className="h-4.5 w-4.5" />}
              title="Products"
              description="Build your catalog and manage availability."
              to="/vendor/dashboard/products"
            />
            <ComingSoonCard
              icon={<BarChart3 className="h-4.5 w-4.5" />}
              title="Sales & payouts"
              description="Track revenue and manage payouts."
            />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
