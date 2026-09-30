import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { tokenStorage } from "../utils/tokenStorage";
import type { ApiErrorBody, TokenPair } from "../types/auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000/api/v1";

// Mutable holder for the in-memory access token. AuthContext calls
// `setAccessToken` whenever it changes (login, refresh, logout).
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// A queue of callers waiting on an in-flight refresh, so concurrent 401s
// don't each trigger their own refresh call.
let isRefreshing = false;
let pendingQueue: Array<(token: string | null) => void> = [];

function resolvePendingQueue(token: string | null) {
  pendingQueue.forEach((resolve) => resolve(token));
  pendingQueue = [];
}

// Called by AuthContext to perform the actual refresh + propagate the new
// session; kept outside this module to avoid a circular import (AuthContext
// needs the api client, and refreshing needs to update AuthContext's state).
let onRefreshed: ((tokens: TokenPair) => void) | null = null;
let onRefreshFailed: (() => void) | null = null;

export function registerRefreshHandlers(handlers: {
  onRefreshed: (tokens: TokenPair) => void;
  onRefreshFailed: () => void;
}) {
  onRefreshed = handlers.onRefreshed;
  onRefreshFailed = handlers.onRefreshFailed;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const status = error.response?.status;
    const isAuthEndpoint = originalRequest?.url?.includes("/auth/login") || originalRequest?.url?.includes("/auth/refresh");

    if (status !== 401 || !originalRequest || originalRequest._retry || isAuthEndpoint) {
      return Promise.reject(error);
    }

    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) {
      onRefreshFailed?.();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (isRefreshing) {
      // Wait for the in-flight refresh to finish, then retry with whatever
      // token it produced (or fail if it produced none).
      return new Promise((resolve, reject) => {
        pendingQueue.push((newToken) => {
          if (!newToken) {
            reject(error);
            return;
          }
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          resolve(apiClient(originalRequest));
        });
      });
    }

    isRefreshing = true;
    try {
      const response = await axios.post<{ data: TokenPair }>(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const tokens = response.data.data;
      onRefreshed?.(tokens);
      resolvePendingQueue(tokens.access_token);
      originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      resolvePendingQueue(null);
      onRefreshFailed?.();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export function extractApiErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (body?.error?.message) return body.error.message;
  }
  return fallback;
}
