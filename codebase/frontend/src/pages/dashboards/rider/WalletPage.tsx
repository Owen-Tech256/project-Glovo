import { useCallback, useEffect, useState } from "react";
import { Wallet as WalletIcon, ArrowDownCircle } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { walletService } from "../../../services/walletService";
import type { RiderWallet, WalletTransaction } from "../../../types/payments";
import { SkeletonList } from "../../../components/ui/Skeleton";

const TYPE_LABELS: Record<WalletTransaction["type"], string> = {
  EARNING: "Delivery earning",
  ADJUSTMENT_CREDIT: "Admin credit",
  ADJUSTMENT_DEBIT: "Admin debit",
  PAYOUT_DEBIT: "Payout",
};

export function WalletPage() {
  const { showError } = useToast();
  const [wallet, setWallet] = useState<RiderWallet | null>(null);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([walletService.getWallet(), walletService.listTransactions()])
      .then(([w, tx]) => {
        setWallet(w);
        setTransactions(tx.transactions);
      })
      .catch(() => showError("Could not load your wallet."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Wallet</h1>
          <p className="text-ink-soft mt-1">Your delivery earnings and balance.</p>
        </div>

        {loading ? (
          <SkeletonList />
        ) : (
          <>
            <Card>
              <CardBody className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-soft text-primary-dark">
                  <WalletIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm text-ink-soft">Available balance</p>
                  <p className="font-display text-2xl font-semibold text-ink">
                    ${wallet ? Number(wallet.available_balance).toFixed(2) : "0.00"}
                  </p>
                  {wallet && Number(wallet.pending_balance) > 0 && (
                    <p className="text-xs text-ink-soft mt-1">${wallet.pending_balance} pending</p>
                  )}
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <p className="font-medium text-ink">Transaction history</p>
              </CardHeader>
              <CardBody>
                {transactions.length === 0 ? (
                  <EmptyState
                    icon={<ArrowDownCircle className="h-5 w-5" />}
                    title="No transactions yet"
                    description="Completed deliveries will show up here as earnings."
                  />
                ) : (
                  <ul className="space-y-3">
                    {transactions.map((tx) => {
                      const isDebit = tx.type === "ADJUSTMENT_DEBIT" || tx.type === "PAYOUT_DEBIT";
                      return (
                        <li key={tx.id} className="flex items-center justify-between text-sm">
                          <div>
                            <p className="text-ink">{TYPE_LABELS[tx.type]}</p>
                            {tx.description && <p className="text-xs text-ink-soft mt-0.5">{tx.description}</p>}
                            <p className="text-xs text-ink-soft mt-0.5">{new Date(tx.created_at).toLocaleString()}</p>
                          </div>
                          <span className={isDebit ? "text-danger font-medium" : "text-primary-dark font-medium"}>
                            {isDebit ? "-" : "+"}${tx.amount}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </CardBody>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
