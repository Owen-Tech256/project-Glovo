import { Store } from "lucide-react";
import { PortalLandingPage } from "./PortalLandingPage";

export function VendorPortalPage() {
  return (
    <PortalLandingPage
      icon={<Store className="h-5 w-5" />}
      eyebrow="Business Portal"
      title="Bring your shop to nearby customers."
      description="Set up your business account now. Branches, product catalogs, and order management are on the way next — Phase 1 gets your account ready."
      bullets={[
        "One account, and later, multiple branches",
        "Server-verified access — only you manage your business account",
        "Built to grow into full catalog and order tools",
      ]}
      registerTo="/vendor/register"
      registerLabel="Create business account"
    />
  );
}
