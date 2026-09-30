import { ShieldCheck } from "lucide-react";
import { PortalLandingPage } from "./PortalLandingPage";

export function AdminPortalPage() {
  return (
    <PortalLandingPage
      icon={<ShieldCheck className="h-5 w-5" />}
      eyebrow="Admin Portal"
      title="Operate the Routeley marketplace."
      description="Admin accounts are provisioned directly by the platform team and are not available through public registration. If you've been issued admin credentials, log in below."
      bullets={[
        "Account provisioning is handled outside the public app, for security",
        "Full platform oversight tools arrive in later phases",
        "Contact your platform team if you need admin access",
      ]}
    />
  );
}
