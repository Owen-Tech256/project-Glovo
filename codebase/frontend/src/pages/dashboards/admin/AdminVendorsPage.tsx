import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Store, ChevronLeft, ChevronRight } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { adminCatalogService } from "../../../services/adminCatalogService";
import type { Vendor } from "../../../types/catalog";
import { SkeletonList } from "../../../components/ui/Skeleton";

export function AdminVendorsPage() {
  const { showError } = useToast();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    adminCatalogService
      .listVendors(page, status || undefined)
      .then((result) => {
        setVendors(result.vendors);
        setTotalPages(result.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load vendors."))
      .finally(() => setLoading(false));
  }, [page, status, showError]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Vendors</h1>
            <p className="text-ink-soft mt-1">Oversee vendor accounts, locations, and catalogs across the platform.</p>
          </div>
          <div className="w-44">
            <Select
              label="Status"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="SUSPENDED">Suspended</option>
              <option value="DISABLED">Disabled</option>
            </Select>
          </div>
        </div>

        {loading ? (
          <SkeletonList />
        ) : vendors.length === 0 ? (
          <EmptyState icon={<Store className="h-5 w-5" />} title="No vendors found" description="No vendors match this filter yet." />
        ) : (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {vendors.map((vendor) => (
                  <li key={vendor.id}>
                    <Link
                      to={`/admin/dashboard/vendors/${vendor.id}`}
                      className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-ink/[0.02]"
                    >
                      <div>
                        <p className="font-medium text-ink">{vendor.name}</p>
                        <p className="text-xs text-ink-soft mt-0.5">{vendor.email ?? "No email on file"}</p>
                      </div>
                      <StatusBadge status={vendor.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3">
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Previous
                </Button>
                <span className="text-sm text-ink-soft">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
