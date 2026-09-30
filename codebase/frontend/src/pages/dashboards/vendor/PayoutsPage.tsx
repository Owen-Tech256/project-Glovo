import { useCallback, useEffect, useState } from "react";
import { Wallet as WalletIcon, Landmark, X } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Input } from "../../../components/ui/Input";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { vendorFinanceService } from "../../../services/vendorFinanceService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { VendorFinancialSummary, VendorPayout } from "../../../types/payments";
import { SkeletonList } from "../../../components/ui/Skeleton";

export function PayoutsPage() {
  const { showError, showSuccess } = useToast();
  const [summary, setSummary] = useState<VendorFinancialSummary | null>(null);
  const [payouts, setPayouts] = useState<VendorPayout[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [destination, setDestination] = useState("");
  const [amount, setAmount] = useState("");
  const [requesting, setRequesting] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([vendorFinanceService.getFinancialSummary(), vendorFinanceService.listPayouts()])
      .then(([s, p]) => {
        setSummary(s);
        setPayouts(p.payouts);
      })
      .catch(() => showError("Could not load your financial summary."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRequestPayout() {
    setRequesting(true);
    try {
      await vendorFinanceService.requestPayout(destination, amount || undefined);
      showSuccess("Payout requested.");
      setModalOpen(false);
      setDestination("");
      setAmount("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not request a payout."));
    } finally {
      setRequesting(false);
    }
  }

  async function handleCancel(payoutId: string) {
    try {
      await vendorFinanceService.cancelPayout(payoutId);
      showSuccess("Payout cancelled.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not cancel this payout."));
    }
  }

  const availableForPayout = summary ? Number(summary.available_for_payout) : 0;

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Payouts</h1>
            <p className="text-ink-soft mt-1">Your earnings and payout history.</p>
          </div>
          <Button onClick={() => setModalOpen(true)} disabled={availableForPayout <= 0}>
            Request payout
          </Button>
        </div>

        {loading ? (
          <SkeletonList />
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Card>
                <CardBody className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-soft text-primary-dark">
                    <WalletIcon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm text-ink-soft">Available for payout</p>
                    <p className="font-display text-2xl font-semibold text-ink">${availableForPayout.toFixed(2)}</p>
                  </div>
                </CardBody>
              </Card>
              <Card>
                <CardBody className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink/[0.04] text-ink-soft">
                    <Landmark className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm text-ink-soft">Lifetime paid out</p>
                    <p className="font-display text-2xl font-semibold text-ink">
                      ${summary ? Number(summary.lifetime_paid_out).toFixed(2) : "0.00"}
                    </p>
                  </div>
                </CardBody>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <p className="font-medium text-ink">Payout history</p>
              </CardHeader>
              <CardBody>
                {payouts.length === 0 ? (
                  <EmptyState
                    icon={<Landmark className="h-5 w-5" />}
                    title="No payouts yet"
                    description="Request a payout once you have earnings available."
                  />
                ) : (
                  <ul className="space-y-3">
                    {payouts.map((payout) => (
                      <li key={payout.id} className="flex items-center justify-between text-sm">
                        <div>
                          <p className="text-ink">${payout.amount} to {payout.destination_reference}</p>
                          {payout.failure_reason && <p className="text-xs text-danger mt-0.5">{payout.failure_reason}</p>}
                          <p className="text-xs text-ink-soft mt-0.5">
                            {payout.requested_at ? new Date(payout.requested_at).toLocaleString() : ""}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusBadge status={payout.status} />
                          {payout.status === "REQUESTED" && (
                            <button
                              onClick={() => handleCancel(payout.id)}
                              aria-label="Cancel payout"
                              className="text-ink-soft hover:text-danger"
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardBody>
            </Card>
          </>
        )}
      </div>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Request a payout"
        description={`Up to $${availableForPayout.toFixed(2)} is available.`}
      >
        <div className="space-y-4">
          <Input
            label="Destination"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="Bank account ending in 1234"
          />
          <Input
            label="Amount (optional - leave blank for the full available balance)"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder={availableForPayout.toFixed(2)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button isLoading={requesting} disabled={!destination.trim()} onClick={handleRequestPayout}>
              Request payout
            </Button>
          </div>
        </div>
      </Modal>
    </DashboardLayout>
  );
}
