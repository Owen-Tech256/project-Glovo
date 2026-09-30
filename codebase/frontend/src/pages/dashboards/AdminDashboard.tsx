import { Users, Store, Bike, ShieldCheck, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { Card, CardBody } from "../../components/ui/Card";
import { Alert } from "../../components/ui/Alert";
import { useAuth } from "../../context/AuthContext";
import { useAdminStats } from "../../hooks/useAdminStats";

const roleCards = [
  { key: "CUSTOMER", label: "Customers", icon: <Users className="h-4.5 w-4.5" /> },
  { key: "VENDOR", label: "Vendors", icon: <Store className="h-4.5 w-4.5" /> },
  { key: "RIDER", label: "Riders", icon: <Bike className="h-4.5 w-4.5" /> },
  { key: "ADMIN", label: "Admins", icon: <ShieldCheck className="h-4.5 w-4.5" /> },
];

export function AdminDashboard() {
  const { user } = useAuth();
  const { stats, isLoading, error } = useAdminStats();
  if (!user) return null;

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Platform overview</h1>
          <p className="text-ink-soft mt-1">Welcome back, {user.full_name.split(" ")[0]}.</p>
        </div>

        {error && <Alert tone="danger">{error}</Alert>}

        {isLoading ? (
          <div className="flex items-center gap-2 text-ink-soft text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading platform stats...
          </div>
        ) : stats ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {roleCards.map((card) => (
              <Card key={card.key}>
                <CardBody className="space-y-3">
                  <div className="h-9 w-9 rounded-md bg-primary-soft text-primary-dark flex items-center justify-center">
                    {card.icon}
                  </div>
                  <div>
                    <p className="text-2xl font-display font-semibold text-ink">{stats.users_by_role[card.key] ?? 0}</p>
                    <p className="text-sm text-ink-soft">{card.label}</p>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        ) : null}

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">User management</h3>
              <p className="text-sm text-ink-soft mb-2">Search, review, and suspend any account on the platform.</p>
              <Link to="/admin/dashboard/users" className="text-sm font-medium text-primary hover:underline">
                Manage users →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Vendor management</h3>
              <p className="text-sm text-ink-soft mb-2">Review vendor accounts, branches, and catalogs.</p>
              <Link to="/admin/dashboard/vendors" className="text-sm font-medium text-primary hover:underline">
                Manage vendors →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Order oversight</h3>
              <p className="text-sm text-ink-soft mb-2">Read-only visibility into orders platform-wide.</p>
              <Link to="/admin/dashboard/orders" className="text-sm font-medium text-primary hover:underline">
                View orders →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Rider management</h3>
              <p className="text-sm text-ink-soft mb-2">Verify onboarding, review documents, and oversee riders.</p>
              <Link to="/admin/dashboard/riders" className="text-sm font-medium text-primary hover:underline">
                Manage riders →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Delivery monitoring</h3>
              <p className="text-sm text-ink-soft mb-2">Track dispatch and reassign deliveries when needed.</p>
              <Link to="/admin/dashboard/deliveries" className="text-sm font-medium text-primary hover:underline">
                View deliveries →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Support</h3>
              <p className="text-sm text-ink-soft mb-2">Triage and respond to tickets from customers, vendors, and riders.</p>
              <Link to="/admin/dashboard/support" className="text-sm font-medium text-primary hover:underline">
                Open queue →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Disputes</h3>
              <p className="text-sm text-ink-soft mb-2">Investigate and resolve disputes, including refunds.</p>
              <Link to="/admin/dashboard/disputes" className="text-sm font-medium text-primary hover:underline">
                Review disputes →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Analytics</h3>
              <p className="text-sm text-ink-soft mb-2">Live dashboards across orders, finance, vendors, and more.</p>
              <Link to="/admin/dashboard/analytics" className="text-sm font-medium text-primary hover:underline">
                View analytics →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Reports</h3>
              <p className="text-sm text-ink-soft mb-2">Generate CSV exports of platform activity.</p>
              <Link to="/admin/dashboard/reports" className="text-sm font-medium text-primary hover:underline">
                Generate report →
              </Link>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <h3 className="font-medium text-ink mb-1">Staff & roles</h3>
              <p className="text-sm text-ink-soft mb-2">Define operational-staff permissions and review the audit trail.</p>
              <Link to="/admin/dashboard/roles" className="text-sm font-medium text-primary hover:underline">
                Manage roles →
              </Link>
            </CardBody>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
