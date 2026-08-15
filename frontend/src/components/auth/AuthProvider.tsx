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

import { AUTH_TOKEN_KEY, authAPI, describeApiError, setAuthToken } from "@/lib/api";
import type { User } from "@/types";

/**
 * Session bootstrap must tolerate a sleeping backend.
 *
 * The previous 10s ceiling was shorter than a free-tier cold start, so the very
 * first visit after an idle period timed out and cleared a perfectly valid
 * token - users were signed out for no reason. Timeout now exceeds the wake
 * window, and a timeout is retried once before the session is discarded.
 */
const AUTH_REQUEST_TIMEOUT_MS = 75_000;
const AUTH_RETRY_DELAY_MS = 1500;

class RequestTimeoutError extends Error {}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timeoutId = window.setTimeout(() => reject(new RequestTimeoutError(message)), timeoutMs);

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

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

/** Network/timeout failures mean "unreachable", not "unauthenticated". */
function isTransientFailure(error: unknown): boolean {
  if (error instanceof RequestTimeoutError) return true;
  const status = (error as any)?.response?.status;
  if (status === undefined) return true; // no response at all
  return status >= 500;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  /** True while a request is outstanding that may be waiting on a cold start. */
  backendWaking: boolean;
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
  const [backendWaking, setBackendWaking] = useState(false);

  const clearSession = useCallback(() => {
    setAuthToken(null);
    setUser(null);
    setToken(null);
  }, []);

  const fetchMe = useCallback(async () => {
    return withTimeout(
      authAPI.me(),
      AUTH_REQUEST_TIMEOUT_MS,
      "Timed out while restoring your session."
    );
  }, []);

  const refreshUser = useCallback(async () => {
    const sessionToken =
      token || (typeof window !== "undefined" ? window.localStorage.getItem(AUTH_TOKEN_KEY) : null);

    if (!sessionToken) {
      clearSession();
      return;
    }

    setAuthToken(sessionToken);
    const response = await fetchMe();
    setUser(response.data);
    setToken(sessionToken);
  }, [clearSession, fetchMe, token]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrapAuth() {
      const storedToken =
        typeof window !== "undefined" ? window.localStorage.getItem(AUTH_TOKEN_KEY) : null;

      if (!storedToken) {
        setLoading(false);
        return;
      }

      setAuthToken(storedToken);
      setBackendWaking(true);

      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          const response = await fetchMe();
          if (cancelled) return;

          setUser(response.data);
          setToken(storedToken);
          break;
        } catch (error) {
          if (cancelled) return;

          // Only a genuine rejection should end the session. A cold start or a
          // dropped connection gets one more chance first.
          if (!isTransientFailure(error) || attempt === 1) {
            clearSession();
            break;
          }

          await delay(AUTH_RETRY_DELAY_MS);
        }
      }

      if (!cancelled) {
        setBackendWaking(false);
        setLoading(false);
      }
    }

    bootstrapAuth();

    return () => {
      cancelled = true;
    };
  }, [clearSession, fetchMe]);

  const signInWithGoogle = useCallback(
    async (credential: string) => {
      setLoading(true);
      setBackendWaking(true);

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
      } catch (error) {
        toast.error(describeApiError(error, "Google sign-in failed"));
        clearSession();
        return false;
      } finally {
        setBackendWaking(false);
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
      backendWaking,
      isAuthenticated: Boolean(user && token),
      signInWithGoogle,
      logout,
      refreshUser,
    }),
    [backendWaking, loading, logout, refreshUser, signInWithGoogle, token, user]
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
