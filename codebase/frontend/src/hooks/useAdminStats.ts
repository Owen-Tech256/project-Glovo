import { useEffect, useState } from "react";
import { apiClient, extractApiErrorMessage } from "../services/apiClient";
import type { ApiSuccess } from "../types/auth";

interface AdminStats {
  total_users: number;
  users_by_role: Record<string, number>;
  users_by_status: Record<string, number>;
}

export function useAdminStats() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await apiClient.get<ApiSuccess<AdminStats>>("/admin/stats");
        if (!cancelled) setStats(data.data);
      } catch (err) {
        if (!cancelled) setError(extractApiErrorMessage(err, "Couldn't load platform stats."));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { stats, isLoading, error };
}
