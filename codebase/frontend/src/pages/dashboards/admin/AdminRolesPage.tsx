import { useCallback, useEffect, useState } from "react";
import { KeyRound, Plus, History } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Badge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { adminRbacService } from "../../../services/adminRbacService";
import { adminAuditService } from "../../../services/adminAuditService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { AdminRole, AdminPermission, AuditEvent } from "../../../types/admin";
import type { User } from "../../../types/auth";
import { SkeletonList } from "../../../components/ui/Skeleton";

type Tab = "roles" | "staff" | "audit";

export function AdminRolesPage() {
  const [tab, setTab] = useState<Tab>("roles");

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink flex items-center gap-2">
            <KeyRound className="h-6 w-6" /> Staff & roles
          </h1>
          <p className="text-ink-soft mt-1">Define what operational staff can do, and see who changed what.</p>
        </div>

        <div className="flex flex-wrap gap-1.5 border-b border-line pb-3">
          {(["roles", "staff", "audit"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
                tab === t ? "bg-primary-soft text-primary-dark" : "text-ink-soft hover:bg-ink/[0.04] hover:text-ink"
              }`}
            >
              {t === "audit" ? "Audit log" : t}
            </button>
          ))}
        </div>

        {tab === "roles" && <RolesTab />}
        {tab === "staff" && <StaffTab />}
        {tab === "audit" && <AuditTab />}
      </div>
    </DashboardLayout>
  );
}

function RolesTab() {
  const { showSuccess, showError } = useToast();
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [permissions, setPermissions] = useState<AdminPermission[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([adminRbacService.listRoles(), adminRbacService.listPermissions()])
      .then(([r, p]) => { setRoles(r); setPermissions(p); })
      .catch(() => showError("Could not load roles."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(load, [load]);

  function togglePermission(key: string) {
    setSelectedKeys((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  }

  async function createRole() {
    setCreating(true);
    try {
      await adminRbacService.createRole(name, description, selectedKeys);
      showSuccess("Role created.");
      setModalOpen(false);
      setName("");
      setDescription("");
      setSelectedKeys([]);
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not create this role."));
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <SkeletonList />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setModalOpen(true)}>
          <Plus className="h-3.5 w-3.5" /> New role
        </Button>
      </div>
      <Card>
        <ul className="divide-y divide-line">
          {roles.map((role) => (
            <li key={role.id} className="px-5 py-3.5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-ink flex items-center gap-2">
                    {role.name}
                    {role.is_system && <Badge tone="neutral">System</Badge>}
                    <Badge tone={role.status === "ACTIVE" ? "success" : "neutral"}>{role.status}</Badge>
                  </p>
                  <p className="text-xs text-ink-soft mt-0.5">{role.description} - {role.staff_count} staff assigned</p>
                </div>
              </div>
              {role.permissions && role.permissions.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {role.permissions.map((key) => (
                    <span key={key} className="rounded-full bg-ink/[0.05] px-2 py-0.5 text-xs text-ink-soft">{key}</span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New admin role" size="lg">
        <div className="space-y-4">
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="REGIONAL_OPS" />
          <Input label="Description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this role is for" />
          <div>
            <p className="text-sm font-medium text-ink mb-2">Permissions</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
              {permissions.map((perm) => (
                <label key={perm.key} className="flex items-start gap-2 text-sm rounded-md border border-line px-3 py-2 cursor-pointer hover:bg-ink/[0.02]">
                  <input
                    type="checkbox"
                    className="mt-0.5"
                    checked={selectedKeys.includes(perm.key)}
                    onChange={() => togglePermission(perm.key)}
                  />
                  <span>
                    <span className="block text-ink font-medium">{perm.key}</span>
                    <span className="block text-xs text-ink-soft">{perm.description}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button isLoading={creating} disabled={!name.trim()} onClick={createRole}>Create role</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function StaffTab() {
  const { showSuccess, showError } = useToast();
  const [staff, setStaff] = useState<User[]>([]);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([adminRbacService.listStaff(undefined, 1), adminRbacService.listRoles()])
      .then(([s, r]) => { setStaff(s.staff); setRoles(r); })
      .catch(() => showError("Could not load staff."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(load, [load]);

  async function changeRole(userId: string, roleId: string) {
    setSavingId(userId);
    try {
      await adminRbacService.assignStaffRole(userId, roleId || null);
      showSuccess("Staff role updated.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not update this staff member's role."));
    } finally {
      setSavingId(null);
    }
  }

  if (loading) return <SkeletonList />;
  if (staff.length === 0) {
    return <EmptyState icon={<KeyRound className="h-5 w-5" />} title="No staff accounts" description="Admin accounts will appear here." />;
  }

  return (
    <Card>
      <ul className="divide-y divide-line">
        {staff.map((member) => (
          <li key={member.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
            <div>
              <p className="text-sm font-medium text-ink">{member.full_name}</p>
              <p className="text-xs text-ink-soft">{member.email}</p>
            </div>
            <div className="w-56">
              <Select
                label="Role"
                value={roles.find((r) => r.name === member.admin_role)?.id ?? ""}
                onChange={(e) => changeRole(member.id, e.target.value)}
                disabled={savingId === member.id}
              >
                <option value="">Unrestricted (no role)</option>
                {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </Select>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function AuditTab() {
  const { showError } = useToast();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    adminAuditService
      .listEvents({ page: 1 })
      .then((r) => setEvents(r.events))
      .catch(() => showError("Could not load the audit trail."))
      .finally(() => setLoading(false));
  }, [showError]);

  if (loading) return <SkeletonList />;
  if (events.length === 0) {
    return <EmptyState icon={<History className="h-5 w-5" />} title="No audit events yet" description="Privileged actions will be recorded here." />;
  }

  return (
    <Card>
      <ul className="divide-y divide-line">
        {events.map((event) => (
          <li key={event.id} className="px-5 py-3.5 text-sm">
            <div className="flex items-center justify-between gap-3">
              <p className="text-ink font-medium">{event.action.replace(/_/g, " ")}</p>
              <p className="text-xs text-ink-soft">{new Date(event.created_at).toLocaleString()}</p>
            </div>
            <p className="text-xs text-ink-soft mt-0.5">
              {event.actor ? `by ${event.actor.name}` : "system"}
              {event.entity_type && ` - ${event.entity_type}${event.entity_id ? ` ${event.entity_id.slice(0, 8)}` : ""}`}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
