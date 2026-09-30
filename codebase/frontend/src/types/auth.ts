export type UserRole = "CUSTOMER" | "VENDOR" | "RIDER" | "ADMIN";

export type UserStatus = "ACTIVE" | "SUSPENDED" | "DISABLED";

export interface User {
  id: string; // public_id (UUID)
  full_name: string;
  email: string;
  phone: string | null;
  role: UserRole;
  status: UserStatus;
  is_email_verified: boolean;
  is_phone_verified: boolean;
  created_at: string;
  last_login_at: string | null;
  admin_role?: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
}

export interface ApiSuccess<T> {
  success: true;
  message: string;
  data: T;
}

export interface ApiErrorBody {
  success: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  phone: string;
  password: string;
  password_confirmation: string;
  role: Exclude<UserRole, "ADMIN">;
}

export interface LoginPayload {
  identifier: string;
  password: string;
  remember_me?: boolean;
}
