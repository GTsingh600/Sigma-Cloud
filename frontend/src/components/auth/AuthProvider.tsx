"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import toast from "react-hot-toast";

import { AUTH_TOKEN_KEY, authAPI, setAuthToken } from "@/lib/api";
import type { User } from "@/types";

const AUTH_REQUEST_TIMEOUT_MS = 10000;

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timeoutId = window.setTimeout(() => reject(new Error(message)), timeoutMs);

    promise
      .then((value) => {
        window.clearTimeout(timeoutId);
        resolve(value);
      })
      .catch((error) => {
        window.clearTimeout(timeoutId);
        reject(error);
      });
  });
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  signInWithGoogle: (credential: string) => Promise<boolean>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    setAuthToken(null);
    setUser(null);
    setToken(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const sessionToken =
      token || (typeof window !== "undefined" ? window.localStorage.getItem(AUTH_TOKEN_KEY) : null);

    if (!sessionToken) {
      clearSession();
      return;
    }

    setAuthToken(sessionToken);
    const response = await withTimeout(
      authAPI.me(),
      AUTH_REQUEST_TIMEOUT_MS,
      "Timed out while restoring your session."
    );
    setUser(response.data);
    setToken(sessionToken);
  }, [clearSession, token]);

  useEffect(() => {
    async function bootstrapAuth() {
      const storedToken =
        typeof window !== "undefined" ? window.localStorage.getItem(AUTH_TOKEN_KEY) : null;

      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        setAuthToken(storedToken);
        const response = await withTimeout(
          authAPI.me(),
          AUTH_REQUEST_TIMEOUT_MS,
          "Timed out while restoring your session."
        );
        setUser(response.data);
        setToken(storedToken);
      } catch {
        clearSession();
      } finally {
        setLoading(false);
      }
    }

    bootstrapAuth();
  }, [clearSession]);

  const signInWithGoogle = useCallback(
    async (credential: string) => {
      setLoading(true);

      try {
        const response = await withTimeout(
          authAPI.googleSignIn(credential),
          AUTH_REQUEST_TIMEOUT_MS,
          "Timed out while contacting the backend."
        );
        setAuthToken(response.data.access_token);
        setToken(response.data.access_token);
        setUser(response.data.user);
        toast.success(`Signed in as ${response.data.user.name}`);
        return true;
      } catch (error: any) {
        const detail = error?.response?.data?.detail || "Google sign-in failed";
        toast.error(detail);
        clearSession();
        return false;
      } finally {
        setLoading(false);
      }
    },
    [clearSession]
  );

  const logout = useCallback(() => {
    clearSession();
    toast.success("Signed out");
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(user && token),
      signInWithGoogle,
      logout,
      refreshUser,
    }),
    [loading, logout, refreshUser, signInWithGoogle, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
