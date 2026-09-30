import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { LoginPayload, RegisterPayload, User } from "../types/auth";
import { authService } from "../services/authService";
import { setAccessToken as setApiAccessToken, registerRefreshHandlers } from "../services/apiClient";
import { tokenStorage } from "../utils/tokenStorage";
import { extractApiErrorMessage } from "../services/apiClient";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  updateProfile: (payload: { full_name?: string }) => Promise<User>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    setApiAccessToken(null);
    tokenStorage.clearRefreshToken();
    setUser(null);
  }, []);

  const applySession = useCallback((accessToken: string, refreshToken: string, sessionUser?: User) => {
    setApiAccessToken(accessToken);
    tokenStorage.setRefreshToken(refreshToken);
    if (sessionUser) setUser(sessionUser);
  }, []);

  // Restore a session on first load using a persisted refresh token, if any.
  useEffect(() => {
    registerRefreshHandlers({
      onRefreshed: (tokens) => {
        setApiAccessToken(tokens.access_token);
        tokenStorage.setRefreshToken(tokens.refresh_token);
      },
      onRefreshFailed: () => {
        clearSession();
      },
    });

    const bootstrap = async () => {
      const existingRefreshToken = tokenStorage.getRefreshToken();
      if (!existingRefreshToken) {
        setIsLoading(false);
        return;
      }
      try {
        const tokens = await authService.refresh(existingRefreshToken);
        applySession(tokens.access_token, tokens.refresh_token);
        const me = await authService.me();
        setUser(me);
      } catch {
        clearSession();
      } finally {
        setIsLoading(false);
      }
    };

    bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (payload: LoginPayload) => {
      const result = await authService.login(payload);
      applySession(result.access_token, result.refresh_token, result.user);
      return result.user;
    },
    [applySession]
  );

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const result = await authService.register(payload);
      applySession(result.access_token, result.refresh_token, result.user);
      return result.user;
    },
    [applySession]
  );

  const logout = useCallback(async () => {
    const refreshToken = tokenStorage.getRefreshToken();
    try {
      if (refreshToken) await authService.logout(refreshToken);
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const refreshSession = useCallback(async () => {
    const existingRefreshToken = tokenStorage.getRefreshToken();
    if (!existingRefreshToken) throw new Error("No active session.");
    const tokens = await authService.refresh(existingRefreshToken);
    applySession(tokens.access_token, tokens.refresh_token);
  }, [applySession]);

  const updateProfile = useCallback(async (payload: { full_name?: string }) => {
    const updated = await authService.updateMe(payload);
    setUser(updated);
    return updated;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
      refreshSession,
      updateProfile,
    }),
    [user, isLoading, login, register, logout, refreshSession, updateProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider.");
  return ctx;
}

export { extractApiErrorMessage };
