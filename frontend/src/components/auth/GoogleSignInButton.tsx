"use client";

import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

import { useAuth } from "./AuthProvider";

interface GoogleSignInButtonProps {
  compact?: boolean;
}

export default function GoogleSignInButton({ compact = false }: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();
  const { loading, signInWithGoogle } = useAuth();
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId || !containerRef.current) {
      return;
    }

    let cancelled = false;

    const renderButton = () => {
      if (cancelled || !containerRef.current || !window.google?.accounts?.id) {
        return false;
      }

      containerRef.current.innerHTML = "";
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          if (response.credential) {
            const success = await signInWithGoogle(response.credential);
            if (success) {
              router.push("/dashboard");
            }
          }
        },
      });
      window.google.accounts.id.renderButton(containerRef.current, {
        theme: "outline",
        size: compact ? "medium" : "large",
        shape: "pill",
        text: "continue_with",
        width: compact ? 220 : 280,
      });

      return true;
    };

    if (renderButton()) {
      return () => {
        cancelled = true;
      };
    }

    const intervalId = window.setInterval(() => {
      if (renderButton()) {
        window.clearInterval(intervalId);
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [clientId, compact, router, signInWithGoogle]);

  if (!clientId) {
    return (
      <div className="rounded-xl border border-sigma-800/60 bg-sigma-900/40 px-4 py-3 text-sm text-sigma-400">
        Add <span className="font-mono text-sigma-200">NEXT_PUBLIC_GOOGLE_CLIENT_ID</span> to enable Google sign-in.
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <div ref={containerRef} className="min-h-[40px]" />
      {loading && (
        <div className="flex items-center gap-2 text-sm text-sigma-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          Signing you in...
        </div>
      )}
    </div>
  );
}
