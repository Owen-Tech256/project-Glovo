import { apiClient } from "./apiClient";
import type {
  ApiSuccess,
  AuthResponse,
  LoginPayload,
  RegisterPayload,
  User,
} from "../types/auth";

export const authService = {
  async register(payload: RegisterPayload) {
    const { data } = await apiClient.post<ApiSuccess<AuthResponse>>("/auth/register", payload);
    return data.data;
  },

  async login(payload: LoginPayload) {
    const { data } = await apiClient.post<ApiSuccess<AuthResponse>>("/auth/login", payload);
    return data.data;
  },

  async logout(refreshToken: string) {
    await apiClient.post("/auth/logout", { refresh_token: refreshToken });
  },

  async me() {
    const { data } = await apiClient.get<ApiSuccess<{ user: User }>>("/auth/me");
    return data.data.user;
  },

  async refresh(refreshToken: string) {
    const { data } = await apiClient.post<ApiSuccess<AuthResponse>>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return data.data;
  },

  async forgotPassword(email: string) {
    const { data } = await apiClient.post<ApiSuccess<{ debug_reset_token?: string }>>(
      "/auth/forgot-password",
      { email }
    );
    return data.data;
  },

  async resetPassword(token: string, password: string, password_confirmation: string) {
    const { data } = await apiClient.post<ApiSuccess<Record<string, never>>>("/auth/reset-password", {
      token,
      password,
      password_confirmation,
    });
    return data;
  },

  async updateMe(payload: { full_name?: string }) {
    const { data } = await apiClient.patch<ApiSuccess<{ user: User }>>("/users/me", payload);
    return data.data.user;
  },
};
