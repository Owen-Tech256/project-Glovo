# Delivery Marketplace — Frontend (Phase 1)

React + TypeScript authentication interface for the delivery marketplace:
landing page, portal pages, login/registration/password-reset flows, and
four role-based dashboard shells. No product, cart, or order UI yet — that's
Phase 2.

## Stack

- React 19 + TypeScript
- Vite
- Tailwind CSS v4
- React Router v7
- Lucide React (icons — no emojis anywhere in the UI)
- Axios

## 1. Setup

### Prerequisites
- Node.js 20+
- The backend running locally (see `../backend/README.md`)

### Install & run

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The app runs at `http://localhost:5173`.

### Build for production

```bash
npm run build     # type-checks with tsc, then builds to dist/
npm run preview   # serve the production build locally
```

## 2. Environment variables

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Base URL of the Flask API, no trailing slash (default `http://localhost:5000/api/v1`) |

## 3. Project structure

```text
src/
├── components/       Shared UI: primitives (ui/), Logo, illustrations, ComingSoonCard
├── context/          AuthContext (session state), ToastContext (notifications)
├── hooks/            useAdminStats, etc.
├── layouts/          AuthLayout (split-screen), DashboardLayout (sidebar)
├── pages/
│   ├── auth/         Login, Register (x3 role variants), Forgot/Reset password
│   ├── dashboards/   One dashboard per role + shared Account/FutureFeature pages
│   ├── LandingPage, VendorPortalPage, RiderPortalPage, AdminPortalPage, NotFoundPage
├── routes/           ProtectedRoute / RoleRoute / GuestOnlyRoute guards
├── services/         apiClient (axios + refresh interceptor), authService
├── types/            Shared TypeScript types
└── utils/            Client-side validation, token storage helpers
```

## 4. Routing map

| Path | Access | Notes |
|---|---|---|
| `/` | public | Landing page |
| `/vendor`, `/rider`, `/admin` | public | Portal intro pages (admin has no register CTA) |
| `/login` | guest only | Universal login for all four roles |
| `/register`, `/vendor/register`, `/rider/register` | guest only | Role-fixed registration |
| `/forgot-password`, `/reset-password` | guest only | `reset-password` reads `?token=` |
| `/customer/dashboard`, `/vendor/dashboard`, `/rider/dashboard`, `/admin/dashboard` | role-gated | Redirects to `/login` if unauthenticated, or to the caller's own dashboard if the role doesn't match |

Guests are redirected away from auth pages if already logged in; authenticated
users are redirected to `/login` from any dashboard route; a logged-in
customer hitting a vendor route is redirected to their own dashboard, not
shown a 403 page — the backend is what actually enforces access (frontend
guards are UX only, per the project's security requirements).

## 5. Authentication design

- **Access token**: kept in memory only (a module-level variable in
  `services/apiClient.ts`), never written to `localStorage`/`sessionStorage`.
  This keeps it out of reach of an XSS payload reading browser storage.
- **Refresh token**: persisted in `localStorage` so a session survives a
  page reload. On app start, `AuthContext` uses it to silently obtain a new
  access token and restore `user`.
- **Automatic refresh**: an axios response interceptor catches `401`s,
  refreshes once (queuing concurrent requests behind the same refresh call),
  retries the original request, and logs the user out if the refresh itself
  fails.
- **Known Phase 1 trade-off**: storing the refresh token in `localStorage`
  is simpler than the alternative, but a real production deployment should
  move to an httpOnly, Secure, SameSite cookie set directly by the API, so
  client JavaScript never has a readable copy of it at all. That change is
  backend + frontend together and was left out of Phase 1 to keep the token
  contract (JSON body) simple while the rest of the auth system is being
  built and tested.

## 6. Design notes

The visual identity ("Routeley") is built around delivery routes rather
than a generic SaaS template: a route/node illustration anchors the
landing page and the auth split-panel, Space Grotesk carries headlines
and Inter carries body/UI text, and the palette is a deep pine green
primary with a coral accent rather than a default blue/purple or the
common cream-and-terracotta AI-generated look. Marketing sections use
hairline dividers instead of shadowed card grids; dashboards use
conventional sidebar + card patterns, since that's expected, legible
structure for functional software.
