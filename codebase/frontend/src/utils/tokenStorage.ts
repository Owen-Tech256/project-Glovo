/**
 * The access token is kept in memory only (see AuthContext) so it never
 * touches localStorage/sessionStorage - that keeps it out of reach of a
 * JS-injection (XSS) attack reading browser storage. The refresh token is
 * long-lived and needed to restore a session across page reloads, so it is
 * persisted here. In a browser-only production deployment this would
 * instead be an httpOnly, Secure, SameSite cookie set by the API so client
 * JavaScript never sees it at all - see the frontend README for this
 * trade-off.
 */
const REFRESH_TOKEN_KEY = "delivery_marketplace_refresh_token";

export const tokenStorage = {
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setRefreshToken(token: string): void {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },
  clearRefreshToken(): void {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
