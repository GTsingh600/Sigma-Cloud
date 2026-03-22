"use client";

import Link from "next/link";
import { Loader2, LockKeyhole } from "lucide-react";

import { useAuth } from "./AuthProvider";
import GoogleSignInButton from "./GoogleSignInButton";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#161d23] px-6 text-[#f8f4ef]">
        <div className="sigma-card w-full max-w-md text-center">
          <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-sigma-400" />
          <h1 className="font-display text-2xl font-semibold text-white">Checking your session</h1>
          <p className="mt-2 text-sm text-sigma-500">Hold on while SigmaCloud validates your Google login.</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#161d23] px-6 text-[#f8f4ef]">
        <div className="sigma-card w-full max-w-lg">
          <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-sigma-500/12">
            <LockKeyhole className="h-6 w-6 text-sigma-400" />
          </div>
          <h1 className="font-display text-3xl font-bold text-white">Sign in to open the dashboard</h1>
          <p className="mt-3 max-w-md text-sm leading-6 text-sigma-500">
            Google authentication now protects datasets, training jobs, deployed models, and predictions per user.
          </p>
          <div className="mt-6">
            <GoogleSignInButton />
          </div>
          <div className="mt-5 text-sm text-sigma-500">
            Need the public landing page instead?{" "}
            <Link href="/" className="text-sigma-300 underline underline-offset-4">
              Go back home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
