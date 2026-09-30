import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, Minus, Plus, ShoppingCart, Trash2 } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Alert } from "../../../components/ui/Alert";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { cartService } from "../../../services/cartService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Cart } from "../../../types/cart";
import { SkeletonList } from "../../../components/ui/Skeleton";

const ISSUE_LABELS: Record<string, string> = {
  BRANCH_UNAVAILABLE: "This branch is not currently accepting orders.",
  PRODUCT_UNAVAILABLE: "is no longer available and won't be included in your order.",
  CART_EMPTY: "Your cart is empty.",
  ADDRESS_OUT_OF_RANGE: "The selected address is outside this branch's delivery area.",
};

export function CartPage() {
  const [searchParams] = useSearchParams();
  const branchId = searchParams.get("branch");
  const navigate = useNavigate();
  const { showError } = useToast();

  const [carts, setCarts] = useState<Cart[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingItemId, setPendingItemId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    const request = branchId
      ? cartService.getCartForBranch(branchId).then((cart) => [cart])
      : cartService.listActiveCarts();
    request
      .then((result) => setCarts(result.filter((c): c is Cart => c !== null && c.id !== null)))
      .catch(() => showError("Could not load your cart."))
      .finally(() => setLoading(false));
  }, [branchId, showError]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleQuantityChange(itemId: string, quantity: number) {
    setPendingItemId(itemId);
    try {
      if (quantity <= 0) {
        await cartService.removeItem(itemId);
      } else {
        await cartService.updateItemQuantity(itemId, quantity);
      }
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update your cart."));
    } finally {
      setPendingItemId(null);
    }
  }

  async function handleRemove(itemId: string) {
    setPendingItemId(itemId);
    try {
      await cartService.removeItem(itemId);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not remove that item."));
    } finally {
      setPendingItemId(null);
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-3xl">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Your cart</h1>
          <p className="text-ink-soft mt-1">Review your items before checking out.</p>
        </div>

        {loading ? (
          <SkeletonList />
        ) : carts.length === 0 ? (
          <EmptyState
            icon={<ShoppingCart className="h-5 w-5" />}
            title="Your cart is empty"
            description="Browse vendors and add a few items to get started."
          />
        ) : (
          <div className="space-y-6">
            {carts.map((cart) => (
              <Card key={cart.branch_id}>
                <CardBody className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="font-display text-lg font-semibold text-ink">{cart.branch_name}</p>
                    <p className="text-sm text-ink-soft">
                      {cart.item_count} item{cart.item_count === 1 ? "" : "s"}
                    </p>
                  </div>

                  {cart.has_issues && (
                    <Alert tone="danger">
                      <div className="space-y-1">
                        {cart.issues.map((issue, index) => (
                          <p key={index}>
                            {issue.product_name ? <strong>{issue.product_name}</strong> : null}{" "}
                            {ISSUE_LABELS[issue.reason] ?? "This item has an issue."}
                          </p>
                        ))}
                      </div>
                    </Alert>
                  )}

                  <div className="divide-y divide-line">
                    {cart.items.map((item) => (
                      <div key={item.id} className="flex items-center gap-3 py-3">
                        {item.product?.images?.[0] && (
                          <img
                            src={item.product.images[0].image_url}
                            alt={item.product.name}
                            className="h-14 w-14 shrink-0 rounded-md object-cover bg-ink/5"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-ink truncate">{item.product?.name ?? "Unknown item"}</p>
                          <p className="text-sm text-ink-soft">
                            ${item.current_unit_price ?? item.unit_price_snapshot} each
                            {item.price_changed && (
                              <span className="ml-1.5 inline-flex items-center gap-1 text-warning">
                                <AlertTriangle className="h-3 w-3" /> price changed
                              </span>
                            )}
                          </p>
                          {!item.is_available && (
                            <p className="text-sm text-danger mt-0.5">No longer available</p>
                          )}
                        </div>
                        <div className="flex items-center gap-1 rounded-md border border-line-strong px-1.5 py-1">
                          <button
                            onClick={() => handleQuantityChange(item.id, item.quantity - 1)}
                            disabled={pendingItemId === item.id}
                            aria-label="Decrease quantity"
                            className="flex h-6 w-6 items-center justify-center rounded text-ink-soft hover:bg-ink/[0.05] disabled:opacity-50"
                          >
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="w-5 text-center text-sm font-medium text-ink">{item.quantity}</span>
                          <button
                            onClick={() => handleQuantityChange(item.id, item.quantity + 1)}
                            disabled={pendingItemId === item.id}
                            aria-label="Increase quantity"
                            className="flex h-6 w-6 items-center justify-center rounded text-ink-soft hover:bg-ink/[0.05] disabled:opacity-50"
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>
                        <p className="w-16 text-right text-sm font-medium text-ink">
                          ${item.line_total ?? "-"}
                        </p>
                        <button
                          onClick={() => handleRemove(item.id)}
                          disabled={pendingItemId === item.id}
                          aria-label="Remove item"
                          className="text-ink-soft hover:text-danger disabled:opacity-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center justify-between border-t border-line pt-4">
                    <p className="text-sm text-ink-soft">Subtotal</p>
                    <p className="font-display text-lg font-semibold text-ink">${cart.subtotal}</p>
                  </div>

                  <Button
                    fullWidth
                    disabled={cart.has_issues || cart.item_count === 0}
                    onClick={() => navigate(`/customer/dashboard/checkout?branch=${cart.branch_id}`)}
                  >
                    Proceed to checkout
                  </Button>
                </CardBody>
              </Card>
            ))}
          </div>
        )}

        <Link to="/customer/dashboard/vendors" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" />
          Continue browsing
        </Link>
      </div>
    </DashboardLayout>
  );
}
