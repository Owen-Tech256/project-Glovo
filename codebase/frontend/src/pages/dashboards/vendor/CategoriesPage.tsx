import { useEffect, useState, type FormEvent } from "react";
import { Tag, Plus, Pencil, EyeOff, Eye } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Textarea } from "../../../components/ui/Textarea";
import { Modal } from "../../../components/ui/Modal";
import { Badge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { catalogService } from "../../../services/catalogService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { Category } from "../../../types/catalog";
import { SkeletonList } from "../../../components/ui/Skeleton";

const emptyForm = { name: "", description: "", image_url: "", sort_order: "0" };

export function CategoriesPage() {
  const { showSuccess, showError } = useToast();
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Category | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    catalogService
      .listMyCategories()
      .then(setCategories)
      .catch(() => showError("Could not load your categories."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [showError]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (category: Category) => {
    setEditing(category);
    setForm({
      name: category.name,
      description: category.description ?? "",
      image_url: category.image_url ?? "",
      sort_order: String(category.sort_order),
    });
    setModalOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        description: form.description || null,
        image_url: form.image_url || null,
        sort_order: Number(form.sort_order) || 0,
      };
      if (editing) {
        await catalogService.updateCategory(editing.id, payload);
        showSuccess("Category updated.");
      } else {
        await catalogService.createCategory(payload);
        showSuccess("Category created.");
      }
      setModalOpen(false);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not save this category."));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (category: Category) => {
    try {
      if (category.is_active) {
        await catalogService.deactivateCategory(category.id);
      } else {
        await catalogService.updateCategory(category.id, { is_active: true });
      }
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this category."));
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink">Categories</h1>
            <p className="text-ink-soft mt-1">Organize your catalog into groups customers can browse.</p>
          </div>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" />
            Add category
          </Button>
        </div>

        {loading ? (
          <SkeletonList />
        ) : categories.length === 0 ? (
          <EmptyState
            icon={<Tag className="h-5 w-5" />}
            title="No categories yet"
            description="Create a category before adding products, e.g. Pizzas, Drinks, Desserts."
          />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.map((category) => (
              <Card key={category.id}>
                <CardBody className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-ink">{category.name}</p>
                    <Badge tone={category.is_active ? "success" : "neutral"}>
                      {category.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  {category.description && (
                    <p className="text-sm text-ink-soft line-clamp-2">{category.description}</p>
                  )}
                  <div className="flex items-center gap-2 pt-1">
                    <Button variant="secondary" size="sm" onClick={() => openEdit(category)}>
                      <Pencil className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => toggleActive(category)}>
                      {category.is_active ? (
                        <>
                          <EyeOff className="h-3.5 w-3.5" />
                          Deactivate
                        </>
                      ) : (
                        <>
                          <Eye className="h-3.5 w-3.5" />
                          Reactivate
                        </>
                      )}
                    </Button>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit category" : "Add category"}>
        <form onSubmit={submit} className="space-y-4">
          <Input
            label="Category name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <Textarea
            label="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <Input
            label="Image URL"
            value={form.image_url}
            onChange={(e) => setForm({ ...form, image_url: e.target.value })}
            placeholder="https://..."
          />
          <Input
            label="Sort order"
            type="number"
            value={form.sort_order}
            onChange={(e) => setForm({ ...form, sort_order: e.target.value })}
            hint="Lower numbers appear first."
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saving}>
              {editing ? "Save changes" : "Create category"}
            </Button>
          </div>
        </form>
      </Modal>
    </DashboardLayout>
  );
}
