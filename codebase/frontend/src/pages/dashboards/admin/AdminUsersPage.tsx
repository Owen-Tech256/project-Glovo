import { useCallback, useEffect, useState } from "react";
import { Users, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Modal } from "../../../components/ui/Modal";
import { Textarea } from "../../../components/ui/Textarea";
import { StatusBadge, Badge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { adminUsersService, type UserDetail } from "../../../services/adminUsersService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { User } from "../../../types/auth";
import { SkeletonList } from "../../../components/ui/Skeleton";

const ROLES = ["CUSTOMER", "VENDOR", "RIDER", "ADMIN"];
const STATUSES = ["ACTIVE", "SUSPENDED", "DEACTIVATED"];

export function AdminUsersPage() {
  const { showSuccess, showError } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  const [detail, setDetail] = useState<UserDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [newStatus, setNewStatus] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    adminUsersService
      .listUsers({ role: role || undefined, status: status || undefined, q: query || undefined, page })
      .then((r) => {
        setUsers(r.users);
        setTotalPages(r.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not load users."))
      .finally(() => setLoading(false));
  }, [role, status, query, page, showError]);

  useEffect(load, [load]);

  async function openDetail(userId: string) {
    try {
      const d = await adminUsersService.getUser(userId);
      setDetail(d);
      setNewStatus(d.status);
      setReason("");
      setDetailOpen(true);
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not load this user."));
    }
  }

  async function saveStatus() {
    if (!detail) return;
    setSaving(true);
    try {
      await adminUsersService.updateStatus(detail.id, newStatus, reason || undefined);
      showSuccess("User status updated.");
      setDetailOpen(false);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this user's status."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink flex items-center gap-2">
              <Users className="h-6 w-6" /> Users
            </h1>
            <p className="text-ink-soft mt-1">Search and manage any account on the platform.</p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <Input label="Search" icon={<Search className="h-4 w-4" />} value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Name or email" />
            <div className="w-40">
              <Select label="Role" value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }}>
                <option value="">All roles</option>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </Select>
            </div>
            <div className="w-40">
              <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
                <option value="">All statuses</option>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </Select>
            </div>
          </div>
        </div>

        {loading ? (
          <SkeletonList />
        ) : users.length === 0 ? (
          <EmptyState icon={<Users className="h-5 w-5" />} title="No users found" description="No accounts match this filter." />
        ) : (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {users.map((u) => (
                  <li key={u.id}>
                    <button onClick={() => openDetail(u.id)} className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left hover:bg-ink/[0.02]">
                      <div>
                        <p className="font-medium text-ink">{u.full_name}</p>
                        <p className="text-xs text-ink-soft mt-0.5">{u.email}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge tone="neutral">{u.role}</Badge>
                        <StatusBadge status={u.status} />
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3">
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                  <ChevronLeft className="h-3.5 w-3.5" /> Previous
                </Button>
                <span className="text-sm text-ink-soft">Page {page} of {totalPages}</span>
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                  Next <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
          </>
        )}

        <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={detail?.full_name ?? "User"}>
          {detail && (
            <div className="space-y-4">
              <CardBody className="p-0 space-y-1 text-sm">
                <p className="text-ink-soft">{detail.email}{detail.phone ? ` - ${detail.phone}` : ""}</p>
                <p className="text-ink-soft">Role: {detail.role} {detail.admin_role ? `(${detail.admin_role})` : ""}</p>
                <p className="text-ink-soft">Joined {new Date(detail.created_at).toLocaleDateString()}</p>
                {detail.vendor && <p className="text-ink-soft">Vendor: {detail.vendor.name} ({detail.vendor.status})</p>}
                {detail.rider && <p className="text-ink-soft">Rider onboarding: {detail.rider.onboarding_status}, operational: {detail.rider.operational_status}</p>}
              </CardBody>
              <Select label="Status" value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </Select>
              <Textarea label="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} rows={2} />
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setDetailOpen(false)}>Cancel</Button>
                <Button isLoading={saving} disabled={newStatus === detail.status} onClick={saveStatus}>Save</Button>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </DashboardLayout>
  );
}
