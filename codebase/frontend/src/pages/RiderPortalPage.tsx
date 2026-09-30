import { Bike } from "lucide-react";
import { PortalLandingPage } from "./PortalLandingPage";

export function RiderPortalPage() {
  return (
    <PortalLandingPage
      icon={<Bike className="h-5 w-5" />}
      eyebrow="Rider Portal"
      title="Deliver on a schedule that works for you."
      description="Create your rider account, get verified, and start accepting delivery jobs — going online, tracking offers, and completing deliveries are all live."
      bullets={[
        "Your own secure rider account",
        "Document verification and vehicle setup",
        "Live delivery offers, pickup, and drop-off tracking",
      ]}
      registerTo="/rider/register"
      registerLabel="Create rider account"
    />
  );
}
