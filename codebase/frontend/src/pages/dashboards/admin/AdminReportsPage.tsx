import { useCallback, useEffect, useState } from "react";
import { FileBarChart, Plus, Download } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody, CardHeader } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { StatusBadge } from "../../../components/ui/Badge";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { reportsService } from "../../../services/reportsService";
import { extractApiErrorMessage } from "../../../services/apiClient";
import type { ReportDefinition, ReportExport, ReportType } from "../../../types/reports";
import { SkeletonList } from "../../../components/ui/Skeleton";

const REPORT_TYPES: ReportType[] = ["ORDERS", "FINANCE", "VENDORS", "RIDERS", "DELIVERY", "CUSTOMERS", "PROMOTIONS_ADS", "SUPPORT_DISPUTES"];

export function AdminReportsPage() {
  const { showSuccess, showError } = useToast();
  const [definitions, setDefinitions] = useState<ReportDefinition[]>([]);
  const [exports, setExports] = useState<ReportExport[]>([]);
  const [loading, setLoading] = useState(true);

  const [defModalOpen, setDefModalOpen] = useState(false);
  const [defName, setDefName] = useState("");
  const [defType, setDefType] = useState<ReportType>("ORDERS");
  const [creatingDef, setCreatingDef] = useState(false);

  const [exportType, setExportType] = useState<ReportType>("ORDERS");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([reportsService.listDefinitions(), reportsService.listExports(1)])
      .then(([defs, exp]) => {
        setDefinitions(defs);
        setExports(exp.exports);
      })
      .catch(() => showError("Could not load reports."))
      .finally(() => setLoading(false));
  }, [showError]);

  useEffect(load, [load]);

  async function createDefinition() {
    setCreatingDef(true);
    try {
      await reportsService.createDefinition(defName, defType);
      showSuccess("Report definition saved.");
      setDefModalOpen(false);
      setDefName("");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not save this report definition."));
    } finally {
      setCreatingDef(false);
    }
  }

  async function requestExport() {
    setRequesting(true);
    try {
      await reportsService.requestExport({ report_type: exportType, date_from: dateFrom || undefined, date_to: dateTo || undefined });
      showSuccess("Export generated.");
      load();
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not generate this export."));
    } finally {
      setRequesting(false);
    }
  }

  async function downloadExport(exp: ReportExport) {
    setDownloadingId(exp.id);
    try {
      const blob = await reportsService.download(exp.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${exp.report_type.toLowerCase()}-${exp.id.slice(0, 8)}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      showError(extractApiErrorMessage(error, "Could not download this export."));
    } finally {
      setDownloadingId(null);
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <SkeletonList />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink flex items-center gap-2">
            <FileBarChart className="h-6 w-6" /> Reports
          </h1>
          <p className="text-ink-soft mt-1">Generate and download CSV exports, or save a reusable report definition.</p>
        </div>

        <Card>
          <CardHeader className="font-medium text-ink">New export</CardHeader>
          <CardBody className="flex flex-wrap items-end gap-3">
            <div className="w-48">
              <Select label="Report type" value={exportType} onChange={(e) => setExportType(e.target.value as ReportType)}>
                {REPORT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </Select>
            </div>
            <Input label="From" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            <Input label="To" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            <Button size="sm" isLoading={requesting} onClick={requestExport}>Generate</Button>
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="font-medium text-ink">Recent exports</CardHeader>
          {exports.length === 0 ? (
            <CardBody className="text-sm text-ink-soft">No exports yet.</CardBody>
          ) : (
            <ul className="divide-y divide-line">
              {exports.map((exp) => (
                <li key={exp.id} className="flex items-center justify-between gap-3 px-5 py-3.5 text-sm">
                  <div>
                    <p className="text-ink">{exp.report_type.replace(/_/g, " ")} {exp.row_count !== null && `- ${exp.row_count} rows`}</p>
                    <p className="text-xs text-ink-soft mt-0.5">{new Date(exp.created_at).toLocaleString()}</p>
                    {exp.error_message && <p className="text-xs text-danger mt-0.5">{exp.error_message}</p>}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge status={exp.status} />
                    {exp.downloadable && (
                      <Button size="sm" variant="secondary" isLoading={downloadingId === exp.id} onClick={() => downloadExport(exp)}>
                        <Download className="h-3.5 w-3.5" /> Download
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-ink">Saved definitions</h2>
          <Button size="sm" variant="secondary" onClick={() => setDefModalOpen(true)}>
            <Plus className="h-3.5 w-3.5" /> New definition
          </Button>
        </div>

        {definitions.length === 0 ? (
          <EmptyState icon={<FileBarChart className="h-5 w-5" />} title="No saved definitions" description="Save a report definition to reuse its configuration later." />
        ) : (
          <Card>
            <ul className="divide-y divide-line">
              {definitions.map((def) => (
                <li key={def.id} className="px-5 py-3.5 text-sm">
                  <p className="text-ink">{def.name}</p>
                  <p className="text-xs text-ink-soft mt-0.5">{def.report_type.replace(/_/g, " ")} - requires {def.access_level}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}

        <Modal open={defModalOpen} onClose={() => setDefModalOpen(false)} title="New report definition">
          <div className="space-y-4">
            <Input label="Name" value={defName} onChange={(e) => setDefName(e.target.value)} placeholder="Weekly delivery health" />
            <Select label="Report type" value={defType} onChange={(e) => setDefType(e.target.value as ReportType)}>
              {REPORT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </Select>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDefModalOpen(false)}>Cancel</Button>
              <Button isLoading={creatingDef} disabled={!defName.trim()} onClick={createDefinition}>Save</Button>
            </div>
          </div>
        </Modal>
      </div>
    </DashboardLayout>
  );
}
