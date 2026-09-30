import { useCallback, useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Package, Phone, Minus, Plus, ShoppingCart } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { vendorService } from "../../../services/vendorService";
import { catalogService } from "../../../services/catalogService";
import { cartService } from "../../../services/cartService";
import type { Vendor, Branch, BranchProduct } from "../../../types/catalog";
import type { Cart } from "../../../types/cart";
import { SkeletonList } from "../../../components/ui/Skeleton";

export function BranchCatalogPage() {
  const { vendorId, branchId } = useParams<{ vendorId: string; branchId: string }>();
  const navigate = useNavigate();
  const { showError } = useToast();
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [products, setProducts] = useState<BranchProduct[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingProductId, setPendingProductId] = useState<string | null>(null);

  const loadCart = useCallback(() => {
    if (!branchId) return;
    cartService.getCartForBranch(branchId).then(setCart).catch(() => undefined);
  }, [branchId]);

  useEffect(() => {
    if (!vendorId || !branchId) return;
    setLoading(true);
    Promise.all([
      vendorService.getPublicVendor(vendorId),
      vendorService.listPublicVendorBranches(vendorId),
      catalogService.listPublicBranchProducts(branchId),
      cartService.getCartForBranch(branchId),
    ])
      .then(([v, branches, links, branchCart]) => {
        setVendor(v);
        setBranch(branches.find((b) => b.id === branchId) ?? null);
        setProducts(links);
        setCart(branchCart);
      })
      .catch(() => showError("Could not load this vendor's catalog."))
      .finally(() => setLoading(false));
  }, [vendorId, branchId, showError]);

  const byCategory = products.reduce<Record<string, BranchProduct[]>>((acc, link) => {
    const key = link.product.category_id;
    acc[key] = acc[key] ?? [];
    acc[key].push(link);
    return acc;
  }, {});

  const cartItemFor = (productId: string) => cart?.items.find((item) => item.product?.id === productId);

  async function handleAdd(productId: string) {
    if (!branchId) return;
    setPendingProductId(productId);
    try {
      const updated = await cartService.addItem(branchId, productId, 1);
      setCart(updated);
    } catch {
      showError("Could not add that item to your cart.");
    } finally {
      setPendingProductId(null);
    }
  }

  async function handleSetQuantity(productId: string, quantity: number) {
    const item = cartItemFor(productId);
    if (!item) return;
    setPendingProductId(productId);
    try {
      if (quantity <= 0) {
        await cartService.removeItem(item.id);
      } else {
        await cartService.updateItemQuantity(item.id, quantity);
      }
      loadCart();
    } catch {
      showError("Could not update your cart.");
    } finally {
      setPendingProductId(null);
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-20">
        <Link to="/customer/dashboard/vendors" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to search
        </Link>

        {loading ? (
          <SkeletonList />
        ) : !vendor || !branch ? (
          <EmptyState icon={<Package className="h-5 w-5" />} title="Not found" description="This vendor or branch is no longer available." />
        ) : (
          <>
            <div>
              <h1 className="font-display text-2xl font-semibold text-ink">{vendor.name}</h1>
              <p className="text-ink-soft mt-1">{branch.name} - {branch.address}</p>
              {branch.phone && (
                <p className="text-sm text-ink-soft mt-1 flex items-center gap-1.5">
                  <Phone className="h-3.5 w-3.5" />
                  {branch.phone}
                </p>
              )}
              {vendor.description && <p className="text-sm text-ink-soft mt-2 max-w-2xl">{vendor.description}</p>}
            </div>

            {products.length === 0 ? (
              <EmptyState
                icon={<Package className="h-5 w-5" />}
                title="No products available"
                description="This branch hasn't added any available products yet."
              />
            ) : (
              <div className="space-y-6">
                {Object.values(byCategory).map((items) => (
                  <div key={items[0].product.category_id}>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {items.map((link) => {
                        const cartItem = cartItemFor(link.product.id);
                        const isPending = pendingProductId === link.product.id;
                        return (
                          <Card key={link.id}>
                            {link.product.images?.[0] && (
                              <img
                                src={link.product.images[0].image_url}
                                alt={link.product.images[0].alt_text ?? link.product.name}
                                className="h-32 w-full rounded-t-lg object-cover bg-ink/5"
                              />
                            )}
                            <CardBody className="space-y-2">
                              <p className="font-medium text-ink">{link.product.name}</p>
                              {link.product.description && (
                                <p className="text-sm text-ink-soft line-clamp-2">{link.product.description}</p>
                              )}
                              <p className="text-base font-display font-semibold text-ink">${link.effective_price}</p>

                              {cartItem ? (
                                <div className="flex items-center justify-between rounded-md border border-line-strong px-2 py-1.5">
                                  <button
                                    onClick={() => handleSetQuantity(link.product.id, cartItem.quantity - 1)}
                                    disabled={isPending}
                                    aria-label="Decrease quantity"
                                    className="flex h-7 w-7 items-center justify-center rounded text-ink-soft hover:bg-ink/[0.05] disabled:opacity-50"
                                  >
                                    <Minus className="h-3.5 w-3.5" />
                                  </button>
                                  <span className="text-sm font-medium text-ink">{cartItem.quantity}</span>
                                  <button
                                    onClick={() => handleSetQuantity(link.product.id, cartItem.quantity + 1)}
                                    disabled={isPending}
                                    aria-label="Increase quantity"
                                    className="flex h-7 w-7 items-center justify-center rounded text-ink-soft hover:bg-ink/[0.05] disabled:opacity-50"
                                  >
                                    <Plus className="h-3.5 w-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <Button size="sm" fullWidth isLoading={isPending} onClick={() => handleAdd(link.product.id)}>
                                  Add to cart
                                </Button>
                              )}
                            </CardBody>
                          </Card>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {cart && cart.item_count > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-paper-raised/95 backdrop-blur px-4 py-3 sm:pl-64">
          <div className="mx-auto flex max-w-3xl items-center justify-between">
            <p className="text-sm text-ink">
              <span className="font-medium">{cart.item_count}</span> item{cart.item_count === 1 ? "" : "s"} - ${cart.subtotal}
            </p>
            <Button size="sm" onClick={() => navigate(`/customer/dashboard/cart?branch=${branchId}`)}>
              <ShoppingCart className="h-4 w-4" />
              View cart
            </Button>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
