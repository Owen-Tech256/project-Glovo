import { useCallback, useEffect, useState } from "react";
import { Landmark, CreditCard, RotateCcw, Wallet, Percent, Scale, Plus } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Input } from "../../../components/ui/Input";
import { StatusBadge, Badge } from "../../../components/ui/Badge";
import { Alert } from "../../../components/ui/Alert";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { adminFinanceService } from "../../../services/adminFinanceService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Payment, Refund, VendorPayout, CommissionRule, ReconciliationSummary } from "../../../types/payments";
import { SkeletonList } from "../../../components/ui/Skeleton";

type Tab = "payments" | "refunds" | "payouts" | "commission" | "reconciliation";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "payments", label: "Payments", icon: <CreditCard className="h-4 w-4" /> },
  { id: "refunds", label: "Refunds", icon: <RotateCcw className="h-4 w-4" /> },
  { id: "payouts", label: "Payouts", icon: <Wallet className="h-4 w-4" /> },
  { id: "commission", label: "Commission rules", icon: <Percent className="h-4 w-4" /> },
  { id: "reconciliation", label: "Reconciliation", icon: <Scale className="h-4 w-4" /> },
];

export function AdminFinancePage() {
  const { showError, showSuccess } = useToast();
  const [tab, setTab] = useState<Tab>("payments");

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink flex items-center gap-2">
            <Landmark className="h-6 w-6" /> Finance
          </h1>
          <p className="text-ink-soft mt-1">Payments, refunds, payouts, commission and reconciliation across the platform.</p>
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
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {tab === "payments" && <PaymentsTab showError={showError} />}
        {tab === "refunds" && <RefundsTab showError={showError} showSuccess={showSuccess} />}
        {tab === "payouts" && <PayoutsTab showError={showError} showSuccess={showSuccess} />}
        {tab === "commission" && <CommissionTab showError={showError} showSuccess={showSuccess} />}
        {tab === "reconciliation" && <ReconciliationTab showError={showError} />}
      </div>
    </DashboardLayout>
  );
}

function PaymentsTab({ showError }: { showError: (msg: string) => void }) {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    adminFinanceService
      .listPayments({})
      .then((r) => setPayments(r.payments))
      .catch(() => showError("Could not load payments."))
      .finally(() => setLoading(false));
  }, [showError]);

  if (loading) return <SkeletonList />;

  return (
    <Card>
      <CardBody>
        {payments.length === 0 ? (
          <EmptyState icon={<CreditCard className="h-5 w-5" />} title="No payments yet" description="Payments will appear here once customers start paying for orders." />
        ) : (
          <ul className="space-y-3">
            {payments.map((p) => (
              <li key={p.id} className="flex items-center justify-between text-sm">
                <div>
                  <p className="text-ink">${p.amount} - {p.order_number ?? p.order_id}</p>
                  <p className="text-xs text-ink-soft mt-0.5">{p.method} via {p.provider} - {new Date(p.created_at).toLocaleString()}</p>
                </div>
                <StatusBadge status={p.status} />
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function RefundsTab({ showError, showSuccess }: { showError: (msg: string) => void; showSuccess: (msg: string) => void }) {
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    adminFinanceService
      .listRefunds({})
      .then((r) => setRefunds(r.refunds))
      .catch(() => showError("Could not load refunds."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(action: (id: string) => Promise<unknown>, id: string, successMsg: string) {
    setBusyId(id);
    try {
      await action(id);
      showSuccess(successMsg);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this refund."));
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <SkeletonList />;

  return (
    <Card>
      <CardBody>
        {refunds.length === 0 ? (
          <EmptyState icon={<RotateCcw className="h-5 w-5" />} title="No refunds yet" description="Customer refund requests will appear here." />
        ) : (
          <ul className="space-y-3">
            {refunds.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-3 text-sm">
                <div>
                  <p className="text-ink">${r.amount}</p>
                  <p className="text-xs text-ink-soft mt-0.5">{r.reason}</p>
                  {r.failure_reason && <p className="text-xs text-danger mt-0.5">{r.failure_reason}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge status={r.status} />
                  {r.status === "REQUESTED" && (
                    <>
                      <Button size="sm" isLoading={busyId === r.id} onClick={() => act(adminFinanceService.approveRefund, r.id, "Refund approved.")}>
                        Approve
                      </Button>
                      <Button size="sm" variant="secondary" isLoading={busyId === r.id} onClick={() => act((id) => adminFinanceService.rejectRefund(id), r.id, "Refund rejected.")}>
                        Reject
                      </Button>
                    </>
                  )}
                  {r.status === "FAILED" && (
                    <Button size="sm" variant="secondary" isLoading={busyId === r.id} onClick={() => act(adminFinanceService.retryRefund, r.id, "Refund retried.")}>
                      Retry
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function PayoutsTab({ showError, showSuccess }: { showError: (msg: string) => void; showSuccess: (msg: string) => void }) {
  const [payouts, setPayouts] = useState<VendorPayout[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    adminFinanceService
      .listPayouts({})
      .then((r) => setPayouts(r.payouts))
      .catch(() => showError("Could not load payouts."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(() => {
    load();
  }, [load]);

  async function retry(id: string) {
    setBusyId(id);
    try {
      await adminFinanceService.retryPayout(id);
      showSuccess("Payout retried.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not retry this payout."));
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <SkeletonList />;

  return (
    <Card>
      <CardBody>
        {payouts.length === 0 ? (
          <EmptyState icon={<Wallet className="h-5 w-5" />} title="No payouts yet" description="Vendor payout requests will appear here." />
        ) : (
          <ul className="space-y-3">
            {payouts.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-3 text-sm">
                <div>
                  <p className="text-ink">${p.amount} to {p.destination_reference}</p>
                  {p.failure_reason && <p className="text-xs text-danger mt-0.5">{p.failure_reason}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge status={p.status} />
                  {p.status === "FAILED" && (
                    <Button size="sm" variant="secondary" isLoading={busyId === p.id} onClick={() => retry(p.id)}>
                      Retry
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function CommissionTab({ showError, showSuccess }: { showError: (msg: string) => void; showSuccess: (msg: string) => void }) {
  const [rules, setRules] = useState<CommissionRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [rate, setRate] = useState("");
  const [fixed, setFixed] = useState("0");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    adminFinanceService
      .listCommissionRules()
      .then(setRules)
      .catch(() => showError("Could not load commission rules."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate() {
    setCreating(true);
    try {
      await adminFinanceService.createCommissionRule({ name, percentage_rate: rate, fixed_amount: fixed });
      showSuccess("Commission rule created.");
      setModalOpen(false);
      setName("");
      setRate("");
      setFixed("0");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not create this commission rule."));
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(rule: CommissionRule) {
    try {
      await adminFinanceService.updateCommissionRule(rule.id, { status: rule.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" });
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this rule."));
    }
  }

  if (loading) return <SkeletonList />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setModalOpen(true)}>
          <Plus className="h-3.5 w-3.5" /> New rule
        </Button>
      </div>
      <Card>
        <CardBody>
          {rules.length === 0 ? (
            <EmptyState icon={<Percent className="h-5 w-5" />} title="No commission rules yet" description="A default rate applies automatically until you configure one." />
          ) : (
            <ul className="space-y-3">
              {rules.map((rule) => (
                <li key={rule.id} className="flex items-center justify-between gap-3 text-sm">
                  <div>
                    <p className="text-ink">{rule.name}</p>
                    <p className="text-xs text-ink-soft mt-0.5">
                      {(Number(rule.percentage_rate) * 100).toFixed(2)}% + ${rule.fixed_amount} - {rule.scope_type}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge tone={rule.status === "ACTIVE" ? "success" : "neutral"}>{rule.status}</Badge>
                    <Button size="sm" variant="secondary" onClick={() => toggleStatus(rule)}>
                      {rule.status === "ACTIVE" ? "Deactivate" : "Activate"}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New commission rule" description="Applies platform-wide going forward.">
        <div className="space-y-4">
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Standard rate" />
          <Input label="Percentage rate (0-1)" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="0.15" />
          <Input label="Fixed amount" value={fixed} onChange={(e) => setFixed(e.target.value)} placeholder="0.00" />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button isLoading={creating} disabled={!name.trim() || !rate.trim()} onClick={handleCreate}>
              Create rule
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function ReconciliationTab({ showError }: { showError: (msg: string) => void }) {
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    adminFinanceService
      .getReconciliationSummary()
      .then(setSummary)
      .catch(() => showError("Could not load the reconciliation summary."))
      .finally(() => setLoading(false));
  }, [showError]);

  if (loading) return <SkeletonList />;
  if (!summary) return null;

  return (
    <div className="space-y-4">
      <Alert tone={summary.balanced ? "success" : "danger"}>
        {summary.balanced
          ? `Ledger is balanced - total debits and credits both equal $${summary.total_debits}.`
          : `Ledger is out of balance: debits $${summary.total_debits} vs credits $${summary.total_credits}.`}
      </Alert>
      <Card>
        <CardHeader>
          <p className="font-medium text-ink">Account balances</p>
        </CardHeader>
        <CardBody>
          <ul className="space-y-2 text-sm">
            {summary.accounts.map((a) => (
              <li key={a.account_id} className="flex items-center justify-between">
                <span className="text-ink-soft">
                  {a.account_type.replace(/_/g, " ").toLowerCase()} {a.owner_id ? `(#${a.owner_id})` : ""}
                </span>
                <span className="text-ink font-medium">${a.reconciled_balance}</span>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
