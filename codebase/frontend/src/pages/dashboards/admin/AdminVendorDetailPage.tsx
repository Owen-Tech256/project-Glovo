import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Store, MapPin, Tag, Ban, CheckCircle2 } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardHeader, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { StatusBadge, Badge } from "../../../components/ui/Badge";
import { useToast } from "../../../context/ToastContext";
import { adminCatalogService } from "../../../services/adminCatalogService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Vendor, Branch, Category, Product } from "../../../types/catalog";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

export function AdminVendorDetailPage() {
  const { vendorId } = useParams<{ vendorId: string }>();
  const { showSuccess, showError } = useToast();
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [catalog, setCatalog] = useState<Array<Category & { products: Product[] }>>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    if (!vendorId) return;
    setLoading(true);
    Promise.all([
      adminCatalogService.getVendor(vendorId),
      adminCatalogService.listVendorBranches(vendorId),
      adminCatalogService.getVendorCatalog(vendorId),
    ])
      .then(([detail, branchList, categories]) => {
        setVendor(detail.vendor);
        setBranches(branchList);
        setCatalog(categories);
      })
      .catch(() => showError("Could not load this vendor."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [vendorId]); // eslint-disable-line react-hooks/exhaustive-deps

  const setVendorStatus = async (status: string) => {
    if (!vendorId) return;
    try {
      await adminCatalogService.updateVendorStatus(vendorId, status);
      showSuccess(`Vendor ${status.toLowerCase()}.`);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update vendor status."));
    }
  };

  const setBranchStatus = async (branch: Branch, status: string) => {
    try {
      await adminCatalogService.updateBranchStatus(branch.id, status);
      showSuccess(`Branch ${status.toLowerCase()}.`);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update branch status."));
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <SkeletonBlock className="h-64" />
      </DashboardLayout>
    );
  }

  if (!vendor) {
    return (
      <DashboardLayout>
        <p className="text-sm text-ink-soft">Vendor not found.</p>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link to="/admin/dashboard/vendors" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to vendors
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">{vendor.name}</h1>
            <p className="text-ink-soft mt-1">{vendor.email ?? "No email on file"} - {vendor.phone ?? "No phone on file"}</p>
          </div>
          <StatusBadge status={vendor.status} />
        </div>

        <Card>
          <CardHeader className="font-medium text-ink">Operational status</CardHeader>
          <CardBody className="flex flex-wrap gap-2">
            <Button
              variant={vendor.status === "ACTIVE" ? "secondary" : "primary"}
              size="sm"
              onClick={() => setVendorStatus("ACTIVE")}
              disabled={vendor.status === "ACTIVE"}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Activate
            </Button>
            <Button
              variant={vendor.status === "SUSPENDED" ? "secondary" : "primary"}
              size="sm"
              onClick={() => setVendorStatus("SUSPENDED")}
              disabled={vendor.status === "SUSPENDED"}
            >
              <Ban className="h-3.5 w-3.5" />
              Suspend
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setVendorStatus("DISABLED")}
              disabled={vendor.status === "DISABLED"}
            >
              Disable
            </Button>
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center gap-2 font-medium text-ink">
            <MapPin className="h-4 w-4 text-primary" />
            Branches ({branches.length})
          </CardHeader>
          {branches.length === 0 ? (
            <CardBody>
              <p className="text-sm text-ink-soft">No branches yet.</p>
            </CardBody>
          ) : (
            <ul className="divide-y divide-line">
              {branches.map((branch) => (
                <li key={branch.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div>
                    <p className="text-sm font-medium text-ink">{branch.name}</p>
                    <p className="text-xs text-ink-soft">{branch.address}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={branch.status} />
                    {branch.status !== "SUSPENDED" ? (
                      <Button variant="ghost" size="sm" onClick={() => setBranchStatus(branch, "SUSPENDED")}>
                        Suspend
                      </Button>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={() => setBranchStatus(branch, "ACTIVE")}>
                        Reactivate
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader className="flex items-center gap-2 font-medium text-ink">
            <Tag className="h-4 w-4 text-primary" />
            Catalog
          </CardHeader>
          {catalog.length === 0 ? (
            <CardBody>
              <p className="text-sm text-ink-soft">No categories yet.</p>
            </CardBody>
          ) : (
            <CardBody className="space-y-4">
              {catalog.map((category) => (
                <div key={category.id}>
                  <div className="flex items-center gap-2 mb-2">
                    <p className="text-sm font-medium text-ink">{category.name}</p>
                    <Badge tone={category.is_active ? "success" : "neutral"}>
                      {category.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  {category.products.length === 0 ? (
                    <p className="text-xs text-ink-soft pl-1">No products.</p>
                  ) : (
                    <ul className="pl-1 space-y-1">
                      {category.products.map((product) => (
                        <li key={product.id} className="flex items-center justify-between text-sm text-ink-soft">
                          <span className="flex items-center gap-2">
                            <Store className="h-3 w-3" />
                            {product.name}
                          </span>
                          <span className="flex items-center gap-2">
                            ${product.price}
                            <StatusBadge status={product.status} />
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </CardBody>
          )}
        </Card>
      </div>
    </DashboardLayout>
  );
}
