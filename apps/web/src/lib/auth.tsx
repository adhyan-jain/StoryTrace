"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { User } from "./types";
import { getMe, login as apiLogin, signup as apiSignup } from "./api";

const TOKEN_KEY = "storytrace_token";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Token lives in localStorage, not an httpOnly cookie -- the pragmatic
// choice for a same-origin-free local dev setup (the API and frontend run
// on different ports/origins, and a cross-origin httpOnly cookie needs
// SameSite=None; Secure, which needs HTTPS). This trades some XSS
// resistance for setup simplicity; note it if hardening this later.
export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

function storeToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

// Called by api.ts's request() when an authenticated call comes back 401 --
// the token expired (24h TTL) or was revoked server-side. Clears storage and
// bounces to /login directly (rather than through the AuthProvider's React
// state, which this module-level function can't reach) so a request fired
// from anywhere -- not just inside a component with access to useAuth() --
// still ends the stuck session instead of looping on retries.
export function handleSessionExpired() {
  storeToken(null);
  if (typeof window === "undefined") return;
  if (window.location.pathname !== "/login") {
    // A hard navigation, not useRouter().push(): this runs from api.ts,
    // called from arbitrary non-component code with no router instance in
    // scope, and it also forces a full reload that clears any in-memory
    // AuthProvider state left over from the expired session.
    window.location.assign("/login");
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const stored = getStoredToken();
    if (!stored) {
      setLoading(false);
      return;
    }
    setToken(stored);
    getMe()
      .then(setUser)
      .catch(() => {
        storeToken(null);
        setToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const res = await apiLogin(email, password);
    storeToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
  }

  async function signup(email: string, password: string) {
    const res = await apiSignup(email, password);
    storeToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
  }

  function logout() {
    storeToken(null);
    setToken(null);
    setUser(null);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
