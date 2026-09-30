import { useEffect, useState, type ReactNode } from "react";
import { BarChart3 } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Input } from "../../../components/ui/Input";
import { useToast } from "../../../context/ToastContext";
import { analyticsService } from "../../../services/analyticsService";
import type {
  OrdersMetrics,
  FinanceMetrics,
  VendorMetricRow,
  RiderMetricRow,
  DeliveryMetrics,
  CustomerMetrics,
  PromotionAdMetrics,
  SupportDisputeMetrics,
} from "../../../types/analytics";
import { SkeletonBlock } from "../../../components/ui/Skeleton";

type Tab = "orders" | "finance" | "vendors" | "riders" | "delivery" | "customers" | "promotions-ads" | "support-disputes";

const TABS: { id: Tab; label: string }[] = [
  { id: "orders", label: "Orders" },
  { id: "finance", label: "Finance" },
  { id: "vendors", label: "Vendors" },
  { id: "riders", label: "Riders" },
  { id: "delivery", label: "Delivery" },
  { id: "customers", label: "Customers" },
  { id: "promotions-ads", label: "Promotions & ads" },
  { id: "support-disputes", label: "Support & disputes" },
];

function StatGrid({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-md border border-line px-4 py-3">
          <p className="text-xs text-ink-soft">{item.label}</p>
          <p className="text-lg font-semibold text-ink mt-0.5">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

function BreakdownList({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return null;
  const max = Math.max(...entries.map(([, v]) => v), 1);
  return (
    <div>
      <p className="text-sm font-medium text-ink mb-2">{title}</p>
      <div className="space-y-1.5">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center gap-2 text-xs">
            <span className="w-36 shrink-0 text-ink-soft">{key.replace(/_/g, " ")}</span>
            <div className="flex-1 h-2 rounded-full bg-ink/[0.06] overflow-hidden">
              <div className="h-full bg-primary" style={{ width: `${(value / max) * 100}%` }} />
            </div>
            <span className="w-8 text-right text-ink">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AdminAnalyticsPage() {
  const { showError } = useToast();
  const [tab, setTab] = useState<Tab>("orders");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const range = { date_from: dateFrom || undefined, date_to: dateTo || undefined };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink flex items-center gap-2">
              <BarChart3 className="h-6 w-6" /> Analytics
            </h1>
            <p className="text-ink-soft mt-1">Operational and financial dashboards computed live from platform activity.</p>
          </div>
          <div className="flex items-end gap-3">
            <Input label="From" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            <Input label="To" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5 border-b border-line pb-3">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === t.id ? "bg-primary-soft text-primary-dark" : "text-ink-soft hover:bg-ink/[0.04] hover:text-ink"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "orders" && <OrdersTab range={range} showError={showError} />}
        {tab === "finance" && <FinanceTab range={range} showError={showError} />}
        {tab === "vendors" && <VendorsTab range={range} showError={showError} />}
        {tab === "riders" && <RidersTab range={range} showError={showError} />}
        {tab === "delivery" && <DeliveryTab range={range} showError={showError} />}
        {tab === "customers" && <CustomersTab range={range} showError={showError} />}
        {tab === "promotions-ads" && <PromotionsAdsTab range={range} showError={showError} />}
        {tab === "support-disputes" && <SupportDisputesTab range={range} showError={showError} />}
      </div>
    </DashboardLayout>
  );
}

interface RangeProps { range: { date_from?: string; date_to?: string }; showError: (m: string) => void }

function OrdersTab({ range, showError }: RangeProps) {
  const [data, setData] = useState<OrdersMetrics | null>(null);
  useEffect(() => { analyticsService.orders(range).then(setData).catch(() => showError("Could not load order analytics.")); }, [range.date_from, range.date_to, showError]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return <SkeletonBlock className="h-64" />;
  return (
    <Card>
      <CardBody className="space-y-5">
        <StatGrid items={[
          { label: "Total orders", value: data.total_orders },
          { label: "Delivered", value: data.delivered_orders },
          { label: "Cancelled", value: data.cancelled_orders },
          { label: "Completion rate", value: `${(data.completion_rate * 100).toFixed(1)}%` },
          { label: "Gross order value", value: `$${data.gross_order_value}` },
          { label: "Average order value", value: `$${data.average_order_value}` },
        ]} />
        <BreakdownList title="Orders by status" data={data.orders_by_status} />
      </CardBody>
    </Card>
  );
}

function FinanceTab({ range, showError }: RangeProps) {
  const [data, setData] = useState<FinanceMetrics | null>(null);
  useEffect(() => { analyticsService.finance(range).then(setData).catch(() => showError("Could not load finance analytics.")); }, [range.date_from, range.date_to, showError]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return <SkeletonBlock className="h-64" />;
  return (
    <Card>
      <CardBody>
        <StatGrid items={[
          { label: "Successful payments", value: `${data.successful_payments} / ${data.total_payment_attempts}` },
          { label: "Payment success rate", value: `${(data.payment_success_rate * 100).toFixed(1)}%` },
          { label: "Gross revenue", value: `$${data.gross_revenue}` },
          { label: "Commission revenue", value: `$${data.platform_commission_revenue}` },
          { label: "Ad revenue", value: `$${data.platform_ad_revenue}` },
          { label: "Net platform revenue", value: `$${data.net_platform_revenue}` },
          { label: "Total refunded", value: `$${data.total_refunded}` },
          { label: "Vendor payouts paid", value: `$${data.vendor_payouts_paid}` },
          { label: "Rider earnings accrued", value: `$${data.rider_earnings_accrued}` },
        ]} />
      </CardBody>
    </Card>
  );
}

function VendorsTab({ range, showError }: RangeProps) {
  const [rows, setRows] = useState<VendorMetricRow[]>([]);
  useEffect(() => { analyticsService.vendors(range).then(setRows).catch(() => showError("Could not load vendor analytics.")); }, [range.date_from, range.date_to, showError]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Card>
      <CardHeader className="font-medium text-ink">Top vendors by gross sales</CardHeader>
      {rows.length === 0 ? (
        <CardBody className="text-sm text-ink-soft">No vendor activity in this range.</CardBody>
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((v) => (
            <li key={v.vendor_id} className="flex items-center justify-between px-5 py-3 text-sm">
              <div>
                <p className="text-ink">{v.vendor_name}</p>
                <p className="text-xs text-ink-soft">{v.order_count} orders - avg ${v.average_order_value}</p>
              </div>
              <p className="text-ink font-medium">${v.net_sales} net</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function RidersTab({ range, showError }: RangeProps) {
  const [rows, setRows] = useState<RiderMetricRow[]>([]);
  useEffect(() => { analyticsService.riders(range).then(setRows).catch(() => showError("Could not load rider analytics.")); }, [range.date_from, range.date_to, showError]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Card>
      <CardHeader className="font-medium text-ink">Top riders by completed deliveries</CardHeader>
      {rows.length === 0 ? (
        <CardBody className="text-sm text-ink-soft">No rider activity in this range.</CardBody>
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((r) => (
            <li key={r.rider_id} className="flex items-center justify-between px-5 py-3 text-sm">
              <div>
                <p className="text-ink">{r.completed_deliveries} deliveries {r.rating_average ? `- ${r.rating_average} avg rating` : ""}</p>
                <p className="text-xs text-ink-soft">Acceptance {(r.acceptance_rate * 100).toFixed(0)}% of {r.offers_received} offers</p>
              </div>
              <p className="text-ink font-medium">${r.earnings}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function DeliveryTab({ range, showError }: RangeProps) {
  const [data, setData] = useState<DeliveryMetrics | null>(null);
  useEffect(() => { analyticsService.delivery(range).then(setData).catch(() => showError("Could not load delivery analytics.")); }, [range.date_from, range.date_to, showError]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return <SkeletonBlock className="h-64" />;
  return (
    <Card>
      <CardBody>
        <StatGrid items={[
          { label: "Total deliveries", value: data.total_deliveries },
          { label: "Completed", value: data.completed_deliveries },
          { label: "Cancelled", value: data.cancelled_deliveries },
          { label: "Failure rate", value: `${(data.failure_rate * 100).toFixed(1)}%` },
          { label: "Avg time to assign", value: data.avg_assignment_seconds !== null ? `${Math.round(data.avg_assignment_seconds)}s` : "-" },
          { label: "Avg time to pick up", value: data.avg_pickup_seconds !== null ? `${Math.round(data.avg_pickup_seconds)}s` : "-" },
          { label: "Avg total duration", value: data.avg_total_duration_seconds !== null ? `${Math.round(data.avg_total_duration_seconds / 60)}m` : "-" },
        ]} />
      </CardBody>
    </Card>
  );
}

function CustomersTab({ range, showError }: RangeProps) {
  const [data, setData] = useState<CustomerMetrics | null>(null);
  useEffect(() => { analyticsService.customers(range).then(setData).catch(() => showError("Could not load customer analytics.")); }, [range.date_from, range.date_to, showError]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return <SkeletonBlock className="h-64" />;
  return (
    <Card>
      <CardBody>
        <StatGrid items={[
          { label: "New registrations", value: data.new_registrations },
          { label: "Active customers", value: data.active_customers },
          { label: "Repeat customers", value: data.repeat_customers },
          { label: "Repeat rate", value: `${(data.repeat_rate * 100).toFixed(1)}%` },
          { label: "Avg orders / active customer", value: data.average_orders_per_active_customer },
        ]} />
      </CardBody>
    </Card>
  );
}

function PromotionsAdsTab({ range, showError }: RangeProps) {
  const [data, setData] = useState<PromotionAdMetrics | null>(null);
  useEffect(() => { analyticsService.promotionsAds(range).then(setData).catch(() => showError("Could not load promotion/ad analytics.")); }, [range.date_from, range.date_to, showError]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return <SkeletonBlock className="h-64" />;
  return (
    <Card>
      <CardBody>
        <StatGrid items={[
          { label: "Active promotions", value: data.active_promotions },
          { label: "Redemptions", value: data.promotion_redemptions },
          { label: "Discount given", value: `$${data.promotion_discount_total}` },
          { label: "Active ad campaigns", value: data.active_ad_campaigns },
          { label: "Impressions", value: data.ad_impressions },
          { label: "Clicks", value: data.ad_clicks },
          { label: "CTR", value: `${(data.ad_ctr * 100).toFixed(2)}%` },
          { label: "Ad spend", value: `$${data.ad_spend}` },
        ]} />
      </CardBody>
    </Card>
  );
}

function SupportDisputesTab({ range, showError }: RangeProps) {
  const [data, setData] = useState<SupportDisputeMetrics | null>(null);
  useEffect(() => { analyticsService.supportDisputes(range).then(setData).catch(() => showError("Could not load support/dispute analytics.")); }, [range.date_from, range.date_to, showError]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return <SkeletonBlock className="h-64" />;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="font-medium text-ink">Tickets</CardHeader>
        <CardBody className="space-y-5">
          <StatGrid items={[
            { label: "Total", value: data.tickets.total },
            { label: "Backlog", value: data.tickets.backlog },
            { label: "Avg resolution time", value: data.tickets.avg_resolution_seconds !== null ? `${Math.round(data.tickets.avg_resolution_seconds / 3600)}h` : "-" },
          ]} />
          <BreakdownList title="By status" data={data.tickets.by_status} />
          <BreakdownList title="By category" data={data.tickets.by_category} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader className="font-medium text-ink">Disputes</CardHeader>
        <CardBody className="space-y-5">
          <StatGrid items={[
            { label: "Total", value: data.disputes.total },
            { label: "Backlog", value: data.disputes.backlog },
            { label: "Avg resolution time", value: data.disputes.avg_resolution_seconds !== null ? `${Math.round(data.disputes.avg_resolution_seconds / 3600)}h` : "-" },
          ]} />
          <BreakdownList title="By status" data={data.disputes.by_status} />
          <BreakdownList title="By category" data={data.disputes.by_category} />
        </CardBody>
      </Card>
    </div>
  );
}
