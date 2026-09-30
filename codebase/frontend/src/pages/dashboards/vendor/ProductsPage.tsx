import { useEffect, useState, type FormEvent } from "react";
import { Package, Plus, Pencil, Archive, ImagePlus, Trash2, MapPinned, RotateCcw } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { Select } from "../../../components/ui/Select";
import { Modal } from "../../../components/ui/Modal";
import { StatusBadge, Badge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { catalogService } from "../../../services/catalogService";
import { vendorService } from "../../../services/vendorService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Product, Category, Branch, BranchProduct } from "../../../types/catalog";
import { SkeletonList } from "../../../components/ui/Skeleton";

const emptyForm = { category_id: "", name: "", description: "", sku: "", price: "" };
const emptyImageForm = { image_url: "", alt_text: "" };

export function ProductsPage() {
  const { showSuccess, showError } = useToast();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const [imageModalProduct, setImageModalProduct] = useState<Product | null>(null);
  const [imageForm, setImageForm] = useState(emptyImageForm);
  const [savingImage, setSavingImage] = useState(false);

  const [availabilityProduct, setAvailabilityProduct] = useState<Product | null>(null);
  const [availability, setAvailability] = useState<Record<string, BranchProduct | null>>({});
  const [availabilityLoading, setAvailabilityLoading] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([catalogService.listMyProducts(), catalogService.listMyCategories(), vendorService.listMyBranches()])
      .then(([p, c, b]) => {
        setProducts(p);
        setCategories(c);
        setBranches(b);
      })
      .catch(() => showError("Could not load your products."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  const activeCategories = categories.filter((c) => c.is_active);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...emptyForm, category_id: activeCategories[0]?.id ?? "" });
    setModalOpen(true);
  };

  const openEdit = (product: Product) => {
    setEditing(product);
    setForm({
      category_id: product.category_id,
      name: product.name,
      description: product.description ?? "",
      sku: product.sku ?? "",
      price: product.price,
    });
    setModalOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = {
        category_id: form.category_id,
        name: form.name,
        description: form.description || null,
        sku: form.sku || null,
        price: form.price,
      };
      if (editing) {
        await catalogService.updateProduct(editing.id, payload);
        showSuccess("Product updated.");
      } else {
        await catalogService.createProduct(payload);
        showSuccess("Product created.");
      }
      setModalOpen(false);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not save this product."));
    } finally {
      setSaving(false);
    }
  };

  const toggleArchived = async (product: Product) => {
    try {
      if (product.status === "ACTIVE") {
        await catalogService.archiveProduct(product.id);
      } else {
        await catalogService.updateProduct(product.id, { status: "ACTIVE" });
      }
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this product."));
    }
  };

  const openImages = (product: Product) => {
    setImageModalProduct(product);
    setImageForm(emptyImageForm);
  };

  const submitImage = async (event: FormEvent) => {
    event.preventDefault();
    if (!imageModalProduct) return;
    setSavingImage(true);
    try {
      await catalogService.addImage(imageModalProduct.id, {
        image_url: imageForm.image_url,
        alt_text: imageForm.alt_text || null,
      });
      showSuccess("Image added.");
      setImageForm(emptyImageForm);
      const refreshed = await catalogService.listMyProducts();
      setProducts(refreshed);
      setImageModalProduct(refreshed.find((p) => p.id === imageModalProduct.id) ?? null);
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not add this image."));
    } finally {
      setSavingImage(false);
    }
  };

  const removeImage = async (imageId: string) => {
    if (!imageModalProduct) return;
    try {
      await catalogService.deleteImage(imageModalProduct.id, imageId);
      const refreshed = await catalogService.listMyProducts();
      setProducts(refreshed);
      setImageModalProduct(refreshed.find((p) => p.id === imageModalProduct.id) ?? null);
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not remove this image."));
    }
  };

  const openAvailability = async (product: Product) => {
    setAvailabilityProduct(product);
    setAvailabilityLoading(true);
    try {
      const entries = await Promise.all(
        branches.map(async (branch) => {
          const links = await catalogService.listBranchProducts(branch.id);
          return [branch.id, links.find((l) => l.product.id === product.id) ?? null] as const;
        })
      );
      setAvailability(Object.fromEntries(entries));
    } catch {
      showError("Could not load branch availability.");
    } finally {
      setAvailabilityLoading(false);
    }
  };

  const setBranchAvailability = async (branch: Branch, isAvailable: boolean) => {
    if (!availabilityProduct) return;
    try {
      const link = await catalogService.setBranchProduct(branch.id, availabilityProduct.id, {
        availability_status: isAvailable ? "AVAILABLE" : "UNAVAILABLE",
      });
      setAvailability((current) => ({ ...current, [branch.id]: link }));
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update availability for this branch."));
    }
  };

  const setPriceOverride = async (branch: Branch, priceOverride: string) => {
    if (!availabilityProduct) return;
    try {
      const link = await catalogService.setBranchProduct(branch.id, availabilityProduct.id, {
        price_override: priceOverride || null,
      });
      setAvailability((current) => ({ ...current, [branch.id]: link }));
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update the price for this branch."));
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Products</h1>
            <p className="text-ink-soft mt-1">Build your catalog, then choose where each item is available.</p>
          </div>
          <Button onClick={openCreate} disabled={activeCategories.length === 0}>
            <Plus className="h-4 w-4" />
            Add product
          </Button>
        </div>

        {loading ? (
          <SkeletonList />
        ) : categories.length === 0 ? (
          <EmptyState
            icon={<Package className="h-5 w-5" />}
            title="Create a category first"
            description="Products belong to a category. Add one from the Categories page, then come back here."
          />
        ) : products.length === 0 ? (
          <EmptyState
            icon={<Package className="h-5 w-5" />}
            title="No products yet"
            description="Add your first product to start building your catalog."
          />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {products.map((product) => {
              const category = categories.find((c) => c.id === product.category_id);
              return (
                <Card key={product.id}>
                  <CardBody className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-ink">{product.name}</p>
                        {category && <p className="text-xs text-ink-soft mt-0.5">{category.name}</p>}
                      </div>
                      <StatusBadge status={product.status} />
                    </div>
                    <p className="text-lg font-display font-semibold text-ink">${product.price}</p>
                    {product.images && product.images.length > 0 && (
                      <Badge tone="neutral">{product.images.length} image{product.images.length === 1 ? "" : "s"}</Badge>
                    )}
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <Button variant="secondary" size="sm" onClick={() => openEdit(product)}>
                        <Pencil className="h-3.5 w-3.5" />
                        Edit
                      </Button>
                      <Button variant="secondary" size="sm" onClick={() => openImages(product)}>
                        <ImagePlus className="h-3.5 w-3.5" />
                        Images
                      </Button>
                      <Button variant="secondary" size="sm" onClick={() => openAvailability(product)}>
                        <MapPinned className="h-3.5 w-3.5" />
                        Availability
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => toggleArchived(product)}>
                        {product.status === "ACTIVE" ? (
                          <>
                            <Archive className="h-3.5 w-3.5" />
                            Archive
                          </>
                        ) : (
                          <>
                            <RotateCcw className="h-3.5 w-3.5" />
                            Restore
                          </>
                        )}
                      </Button>
                    </div>
                  </CardBody>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Create / edit product */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit product" : "Add product"}>
        <form onSubmit={submit} className="space-y-4">
          <Select
            label="Category"
            value={form.category_id}
            onChange={(e) => setForm({ ...form, category_id: e.target.value })}
            required
          >
            {activeCategories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <Input
            label="Product name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <Textarea
            label="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Price"
              type="number"
              step="0.01"
              min="0"
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
              required
            />
            <Input label="SKU" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saving}>
              {editing ? "Save changes" : "Create product"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Images */}
      <Modal
        open={Boolean(imageModalProduct)}
        onClose={() => setImageModalProduct(null)}
        title={`Images - ${imageModalProduct?.name ?? ""}`}
      >
        <div className="space-y-4">
          <form onSubmit={submitImage} className="flex gap-2 items-end">
            <div className="flex-1">
              <Input
                label="Image URL"
                value={imageForm.image_url}
                onChange={(e) => setImageForm({ ...imageForm, image_url: e.target.value })}
                placeholder="https://..."
                required
              />
            </div>
            <Button type="submit" size="sm" isLoading={savingImage}>
              Add
            </Button>
          </form>
          {imageModalProduct?.images && imageModalProduct.images.length > 0 ? (
            <ul className="space-y-2">
              {imageModalProduct.images.map((img) => (
                <li key={img.id} className="flex items-center gap-3 rounded-md border border-line p-2">
                  <img src={img.image_url} alt={img.alt_text ?? ""} className="h-12 w-12 rounded-md object-cover bg-ink/5" />
                  <span className="flex-1 text-sm text-ink-soft truncate">{img.image_url}</span>
                  <button
                    onClick={() => removeImage(img.id)}
                    aria-label="Remove image"
                    className="text-ink-soft hover:text-danger p-1.5 rounded-md hover:bg-danger-soft shrink-0"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink-soft">No images yet.</p>
          )}
        </div>
      </Modal>

      {/* Branch availability */}
      <Modal
        open={Boolean(availabilityProduct)}
        onClose={() => setAvailabilityProduct(null)}
        title={`Availability - ${availabilityProduct?.name ?? ""}`}
        description="Choose which branches offer this product, and optionally override its price for that location."
        size="lg"
      >
        {availabilityLoading ? (
          <SkeletonList />
        ) : branches.length === 0 ? (
          <p className="text-sm text-ink-soft">Add a branch first from the Branches page.</p>
        ) : (
          <ul className="divide-y divide-line rounded-md border border-line">
            {branches.map((branch) => {
              const link = availability[branch.id];
              const isAvailable = link?.availability_status === "AVAILABLE";
              return (
                <li key={branch.id} className="flex flex-wrap items-center justify-between gap-3 px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-ink">{branch.name}</p>
                    <p className="text-xs text-ink-soft">
                      {link ? `Effective price: $${link.effective_price}` : "Not offered here"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder={availabilityProduct?.price}
                      defaultValue={link?.price_override ?? ""}
                      onBlur={(e) => setPriceOverride(branch, e.target.value)}
                      aria-label={`Price override for ${branch.name}`}
                      className="w-24 rounded-md border border-line-strong bg-paper-raised px-2 py-1.5 text-sm text-ink outline-none focus:border-primary"
                    />
                    <Button
                      variant={isAvailable ? "secondary" : "primary"}
                      size="sm"
                      onClick={() => setBranchAvailability(branch, !isAvailable)}
                    >
                      {isAvailable ? "Available" : "Unavailable"}
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Modal>
    </DashboardLayout>
  );
}
