import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";

import { LandingPage } from "./pages/LandingPage";
import { VendorPortalPage } from "./pages/VendorPortalPage";
import { RiderPortalPage } from "./pages/RiderPortalPage";
import { AdminPortalPage } from "./pages/AdminPortalPage";
import { NotFoundPage } from "./pages/NotFoundPage";

import { LoginPage } from "./pages/auth/LoginPage";
import { CustomerRegisterPage } from "./pages/auth/CustomerRegisterPage";
import { VendorRegisterPage } from "./pages/auth/VendorRegisterPage";
import { RiderRegisterPage } from "./pages/auth/RiderRegisterPage";
import { ForgotPasswordPage } from "./pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/auth/ResetPasswordPage";

// Everything below is reachable only after authentication + a role check,
// so none of it belongs in the bundle a first-time visitor downloads to see
// the landing/login page. Each is its own on-demand chunk instead - a
// customer never even fetches the vendor/rider/admin portals' code, not
// just doesn't render it.
const CustomerDashboard = lazy(() => import("./pages/dashboards/CustomerDashboard").then((m) => ({ default: m.CustomerDashboard })));
const VendorDashboard = lazy(() => import("./pages/dashboards/VendorDashboard").then((m) => ({ default: m.VendorDashboard })));
const RiderDashboard = lazy(() => import("./pages/dashboards/RiderDashboard").then((m) => ({ default: m.RiderDashboard })));
const AdminDashboard = lazy(() => import("./pages/dashboards/AdminDashboard").then((m) => ({ default: m.AdminDashboard })));
const AccountPage = lazy(() => import("./pages/dashboards/AccountPage").then((m) => ({ default: m.AccountPage })));

const BusinessProfilePage = lazy(() => import("./pages/dashboards/vendor/BusinessProfilePage").then((m) => ({ default: m.BusinessProfilePage })));
const BranchesPage = lazy(() => import("./pages/dashboards/vendor/BranchesPage").then((m) => ({ default: m.BranchesPage })));
const CategoriesPage = lazy(() => import("./pages/dashboards/vendor/CategoriesPage").then((m) => ({ default: m.CategoriesPage })));
const ProductsPage = lazy(() => import("./pages/dashboards/vendor/ProductsPage").then((m) => ({ default: m.ProductsPage })));

const BrowseVendorsPage = lazy(() => import("./pages/dashboards/customer/BrowseVendorsPage").then((m) => ({ default: m.BrowseVendorsPage })));
const BranchCatalogPage = lazy(() => import("./pages/dashboards/customer/BranchCatalogPage").then((m) => ({ default: m.BranchCatalogPage })));
const AddressesPage = lazy(() => import("./pages/dashboards/customer/AddressesPage").then((m) => ({ default: m.AddressesPage })));
const CartPage = lazy(() => import("./pages/dashboards/customer/CartPage").then((m) => ({ default: m.CartPage })));
const CheckoutPage = lazy(() => import("./pages/dashboards/customer/CheckoutPage").then((m) => ({ default: m.CheckoutPage })));
const OrdersPage = lazy(() => import("./pages/dashboards/customer/OrdersPage").then((m) => ({ default: m.OrdersPage })));
const OrderDetailPage = lazy(() => import("./pages/dashboards/customer/OrderDetailPage").then((m) => ({ default: m.OrderDetailPage })));

const VendorOrderQueuePage = lazy(() => import("./pages/dashboards/vendor/OrderQueuePage").then((m) => ({ default: m.VendorOrderQueuePage })));
const VendorOrderDetailPage = lazy(() => import("./pages/dashboards/vendor/OrderDetailPage").then((m) => ({ default: m.VendorOrderDetailPage })));

const AdminVendorsPage = lazy(() => import("./pages/dashboards/admin/AdminVendorsPage").then((m) => ({ default: m.AdminVendorsPage })));
const AdminVendorDetailPage = lazy(() => import("./pages/dashboards/admin/AdminVendorDetailPage").then((m) => ({ default: m.AdminVendorDetailPage })));
const AdminOrdersPage = lazy(() => import("./pages/dashboards/admin/AdminOrdersPage").then((m) => ({ default: m.AdminOrdersPage })));
const AdminOrderDetailPage = lazy(() => import("./pages/dashboards/admin/AdminOrderDetailPage").then((m) => ({ default: m.AdminOrderDetailPage })));
const AdminRidersPage = lazy(() => import("./pages/dashboards/admin/AdminRidersPage").then((m) => ({ default: m.AdminRidersPage })));
const AdminRiderDetailPage = lazy(() => import("./pages/dashboards/admin/AdminRiderDetailPage").then((m) => ({ default: m.AdminRiderDetailPage })));
const AdminDeliveriesPage = lazy(() => import("./pages/dashboards/admin/AdminDeliveriesPage").then((m) => ({ default: m.AdminDeliveriesPage })));
const AdminDeliveryDetailPage = lazy(() => import("./pages/dashboards/admin/AdminDeliveryDetailPage").then((m) => ({ default: m.AdminDeliveryDetailPage })));

const DeliveriesPage = lazy(() => import("./pages/dashboards/rider/DeliveriesPage").then((m) => ({ default: m.DeliveriesPage })));
const VehiclePage = lazy(() => import("./pages/dashboards/rider/VehiclePage").then((m) => ({ default: m.VehiclePage })));
const DocumentsPage = lazy(() => import("./pages/dashboards/rider/DocumentsPage").then((m) => ({ default: m.DocumentsPage })));
const ZonesPage = lazy(() => import("./pages/dashboards/rider/ZonesPage").then((m) => ({ default: m.ZonesPage })));
const WalletPage = lazy(() => import("./pages/dashboards/rider/WalletPage").then((m) => ({ default: m.WalletPage })));

const PayoutsPage = lazy(() => import("./pages/dashboards/vendor/PayoutsPage").then((m) => ({ default: m.PayoutsPage })));
const AdminFinancePage = lazy(() => import("./pages/dashboards/admin/AdminFinancePage").then((m) => ({ default: m.AdminFinancePage })));

const VendorPromotionsPage = lazy(() => import("./pages/dashboards/vendor/PromotionsPage").then((m) => ({ default: m.PromotionsPage })));
const CampaignsPage = lazy(() => import("./pages/dashboards/vendor/CampaignsPage").then((m) => ({ default: m.CampaignsPage })));
const VendorReviewsPage = lazy(() => import("./pages/dashboards/vendor/ReviewsPage").then((m) => ({ default: m.VendorReviewsPage })));
const CustomerPromotionsPage = lazy(() => import("./pages/dashboards/customer/PromotionsPage").then((m) => ({ default: m.CustomerPromotionsPage })));
const NotificationsPage = lazy(() => import("./pages/dashboards/shared/NotificationsPage").then((m) => ({ default: m.NotificationsPage })));
const AdminGrowthPage = lazy(() => import("./pages/dashboards/admin/AdminGrowthPage").then((m) => ({ default: m.AdminGrowthPage })));

const SupportPage = lazy(() => import("./pages/dashboards/shared/SupportPage").then((m) => ({ default: m.SupportPage })));
const SupportTicketDetailPage = lazy(() => import("./pages/dashboards/shared/SupportTicketDetailPage").then((m) => ({ default: m.SupportTicketDetailPage })));
const DisputeDetailPage = lazy(() => import("./pages/dashboards/shared/DisputeDetailPage").then((m) => ({ default: m.DisputeDetailPage })));
const AdminSupportPage = lazy(() => import("./pages/dashboards/admin/AdminSupportPage").then((m) => ({ default: m.AdminSupportPage })));
const AdminSupportTicketDetailPage = lazy(() => import("./pages/dashboards/admin/AdminSupportTicketDetailPage").then((m) => ({ default: m.AdminSupportTicketDetailPage })));
const AdminDisputesPage = lazy(() => import("./pages/dashboards/admin/AdminDisputesPage").then((m) => ({ default: m.AdminDisputesPage })));
const AdminDisputeDetailPage = lazy(() => import("./pages/dashboards/admin/AdminDisputeDetailPage").then((m) => ({ default: m.AdminDisputeDetailPage })));
const AdminAnalyticsPage = lazy(() => import("./pages/dashboards/admin/AdminAnalyticsPage").then((m) => ({ default: m.AdminAnalyticsPage })));
const AdminReportsPage = lazy(() => import("./pages/dashboards/admin/AdminReportsPage").then((m) => ({ default: m.AdminReportsPage })));
const AdminRolesPage = lazy(() => import("./pages/dashboards/admin/AdminRolesPage").then((m) => ({ default: m.AdminRolesPage })));
const AdminUsersPage = lazy(() => import("./pages/dashboards/admin/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage })));

import { GuestOnlyRoute, RoleRoute, FullScreenSpinner } from "./routes/guards";

function App() {
  return (
    <Suspense fallback={<FullScreenSpinner />}>
      <Routes>
      {/* Public marketing + portal pages */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/vendor" element={<VendorPortalPage />} />
      <Route path="/rider" element={<RiderPortalPage />} />
      <Route path="/admin" element={<AdminPortalPage />} />

      {/* Guest-only auth pages */}
      <Route path="/login" element={<GuestOnlyRoute><LoginPage /></GuestOnlyRoute>} />
      <Route path="/register" element={<GuestOnlyRoute><CustomerRegisterPage /></GuestOnlyRoute>} />
      <Route path="/vendor/register" element={<GuestOnlyRoute><VendorRegisterPage /></GuestOnlyRoute>} />
      <Route path="/rider/register" element={<GuestOnlyRoute><RiderRegisterPage /></GuestOnlyRoute>} />
      <Route path="/forgot-password" element={<GuestOnlyRoute><ForgotPasswordPage /></GuestOnlyRoute>} />
      <Route path="/reset-password" element={<GuestOnlyRoute><ResetPasswordPage /></GuestOnlyRoute>} />

      {/* Customer dashboard */}
      <Route path="/customer/dashboard" element={<RoleRoute allowed={["CUSTOMER"]}><CustomerDashboard /></RoleRoute>} />
      <Route path="/customer/dashboard/vendors" element={<RoleRoute allowed={["CUSTOMER"]}><BrowseVendorsPage /></RoleRoute>} />
      <Route
        path="/customer/dashboard/vendors/:vendorId/branches/:branchId"
        element={<RoleRoute allowed={["CUSTOMER"]}><BranchCatalogPage /></RoleRoute>}
      />
      <Route path="/customer/dashboard/addresses" element={<RoleRoute allowed={["CUSTOMER"]}><AddressesPage /></RoleRoute>} />
      <Route path="/customer/dashboard/cart" element={<RoleRoute allowed={["CUSTOMER"]}><CartPage /></RoleRoute>} />
      <Route path="/customer/dashboard/checkout" element={<RoleRoute allowed={["CUSTOMER"]}><CheckoutPage /></RoleRoute>} />
      <Route path="/customer/dashboard/orders" element={<RoleRoute allowed={["CUSTOMER"]}><OrdersPage /></RoleRoute>} />
      <Route path="/customer/dashboard/orders/:orderId" element={<RoleRoute allowed={["CUSTOMER"]}><OrderDetailPage /></RoleRoute>} />
      <Route path="/customer/dashboard/promotions" element={<RoleRoute allowed={["CUSTOMER"]}><CustomerPromotionsPage /></RoleRoute>} />
      <Route path="/customer/dashboard/support" element={<RoleRoute allowed={["CUSTOMER"]}><SupportPage /></RoleRoute>} />
      <Route path="/customer/dashboard/support/:ticketId" element={<RoleRoute allowed={["CUSTOMER"]}><SupportTicketDetailPage /></RoleRoute>} />
      <Route path="/customer/dashboard/disputes/:disputeId" element={<RoleRoute allowed={["CUSTOMER"]}><DisputeDetailPage /></RoleRoute>} />
      <Route path="/customer/dashboard/notifications" element={<RoleRoute allowed={["CUSTOMER"]}><NotificationsPage /></RoleRoute>} />
      <Route path="/customer/dashboard/account" element={<RoleRoute allowed={["CUSTOMER"]}><AccountPage /></RoleRoute>} />

      {/* Vendor dashboard */}
      <Route path="/vendor/dashboard" element={<RoleRoute allowed={["VENDOR"]}><VendorDashboard /></RoleRoute>} />
      <Route path="/vendor/dashboard/profile" element={<RoleRoute allowed={["VENDOR"]}><BusinessProfilePage /></RoleRoute>} />
      <Route path="/vendor/dashboard/branches" element={<RoleRoute allowed={["VENDOR"]}><BranchesPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/categories" element={<RoleRoute allowed={["VENDOR"]}><CategoriesPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/products" element={<RoleRoute allowed={["VENDOR"]}><ProductsPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/orders" element={<RoleRoute allowed={["VENDOR"]}><VendorOrderQueuePage /></RoleRoute>} />
      <Route path="/vendor/dashboard/orders/:orderId" element={<RoleRoute allowed={["VENDOR"]}><VendorOrderDetailPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/payouts" element={<RoleRoute allowed={["VENDOR"]}><PayoutsPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/promotions" element={<RoleRoute allowed={["VENDOR"]}><VendorPromotionsPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/campaigns" element={<RoleRoute allowed={["VENDOR"]}><CampaignsPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/reviews" element={<RoleRoute allowed={["VENDOR"]}><VendorReviewsPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/support" element={<RoleRoute allowed={["VENDOR"]}><SupportPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/support/:ticketId" element={<RoleRoute allowed={["VENDOR"]}><SupportTicketDetailPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/disputes/:disputeId" element={<RoleRoute allowed={["VENDOR"]}><DisputeDetailPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/notifications" element={<RoleRoute allowed={["VENDOR"]}><NotificationsPage /></RoleRoute>} />
      <Route path="/vendor/dashboard/account" element={<RoleRoute allowed={["VENDOR"]}><AccountPage /></RoleRoute>} />

      {/* Rider dashboard */}
      <Route path="/rider/dashboard" element={<RoleRoute allowed={["RIDER"]}><RiderDashboard /></RoleRoute>} />
      <Route path="/rider/dashboard/deliveries" element={<RoleRoute allowed={["RIDER"]}><DeliveriesPage /></RoleRoute>} />
      <Route path="/rider/dashboard/wallet" element={<RoleRoute allowed={["RIDER"]}><WalletPage /></RoleRoute>} />
      <Route path="/rider/dashboard/zones" element={<RoleRoute allowed={["RIDER"]}><ZonesPage /></RoleRoute>} />
      <Route path="/rider/dashboard/documents" element={<RoleRoute allowed={["RIDER"]}><DocumentsPage /></RoleRoute>} />
      <Route path="/rider/dashboard/vehicle" element={<RoleRoute allowed={["RIDER"]}><VehiclePage /></RoleRoute>} />
      <Route path="/rider/dashboard/reviews" element={<RoleRoute allowed={["RIDER"]}><VendorReviewsPage isRider /></RoleRoute>} />
      <Route path="/rider/dashboard/support" element={<RoleRoute allowed={["RIDER"]}><SupportPage /></RoleRoute>} />
      <Route path="/rider/dashboard/support/:ticketId" element={<RoleRoute allowed={["RIDER"]}><SupportTicketDetailPage /></RoleRoute>} />
      <Route path="/rider/dashboard/disputes/:disputeId" element={<RoleRoute allowed={["RIDER"]}><DisputeDetailPage /></RoleRoute>} />
      <Route path="/rider/dashboard/notifications" element={<RoleRoute allowed={["RIDER"]}><NotificationsPage /></RoleRoute>} />
      <Route path="/rider/dashboard/account" element={<RoleRoute allowed={["RIDER"]}><AccountPage /></RoleRoute>} />

      {/* Admin dashboard */}
      <Route path="/admin/dashboard" element={<RoleRoute allowed={["ADMIN"]}><AdminDashboard /></RoleRoute>} />
      <Route path="/admin/dashboard/users" element={<RoleRoute allowed={["ADMIN"]}><AdminUsersPage /></RoleRoute>} />
      <Route path="/admin/dashboard/vendors" element={<RoleRoute allowed={["ADMIN"]}><AdminVendorsPage /></RoleRoute>} />
      <Route path="/admin/dashboard/vendors/:vendorId" element={<RoleRoute allowed={["ADMIN"]}><AdminVendorDetailPage /></RoleRoute>} />
      <Route path="/admin/dashboard/orders" element={<RoleRoute allowed={["ADMIN"]}><AdminOrdersPage /></RoleRoute>} />
      <Route path="/admin/dashboard/orders/:orderId" element={<RoleRoute allowed={["ADMIN"]}><AdminOrderDetailPage /></RoleRoute>} />
      <Route path="/admin/dashboard/riders" element={<RoleRoute allowed={["ADMIN"]}><AdminRidersPage /></RoleRoute>} />
      <Route path="/admin/dashboard/riders/:riderId" element={<RoleRoute allowed={["ADMIN"]}><AdminRiderDetailPage /></RoleRoute>} />
      <Route path="/admin/dashboard/deliveries" element={<RoleRoute allowed={["ADMIN"]}><AdminDeliveriesPage /></RoleRoute>} />
      <Route path="/admin/dashboard/deliveries/:deliveryId" element={<RoleRoute allowed={["ADMIN"]}><AdminDeliveryDetailPage /></RoleRoute>} />
      <Route path="/admin/dashboard/finance" element={<RoleRoute allowed={["ADMIN"]}><AdminFinancePage /></RoleRoute>} />
      <Route path="/admin/dashboard/growth" element={<RoleRoute allowed={["ADMIN"]}><AdminGrowthPage /></RoleRoute>} />
      <Route path="/admin/dashboard/support" element={<RoleRoute allowed={["ADMIN"]}><AdminSupportPage /></RoleRoute>} />
      <Route path="/admin/dashboard/support/:ticketId" element={<RoleRoute allowed={["ADMIN"]}><AdminSupportTicketDetailPage /></RoleRoute>} />
      <Route path="/admin/dashboard/disputes" element={<RoleRoute allowed={["ADMIN"]}><AdminDisputesPage /></RoleRoute>} />
      <Route path="/admin/dashboard/disputes/:disputeId" element={<RoleRoute allowed={["ADMIN"]}><AdminDisputeDetailPage /></RoleRoute>} />
      <Route path="/admin/dashboard/analytics" element={<RoleRoute allowed={["ADMIN"]}><AdminAnalyticsPage /></RoleRoute>} />
      <Route path="/admin/dashboard/reports" element={<RoleRoute allowed={["ADMIN"]}><AdminReportsPage /></RoleRoute>} />
      <Route path="/admin/dashboard/roles" element={<RoleRoute allowed={["ADMIN"]}><AdminRolesPage /></RoleRoute>} />
      <Route path="/admin/dashboard/notifications" element={<RoleRoute allowed={["ADMIN"]}><NotificationsPage /></RoleRoute>} />

      <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}

export default App;
