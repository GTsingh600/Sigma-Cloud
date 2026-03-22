import Sidebar from "@/components/layout/Sidebar";
import AuthGate from "@/components/auth/AuthGate";

export const dynamic = "force-dynamic";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <div className="flex h-screen overflow-hidden bg-[#161d23] text-[#f8f4ef]">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <div className="min-h-full p-8 bg-[radial-gradient(circle_at_top,rgba(129,166,198,0.12),transparent_24%),radial-gradient(circle_at_88%_12%,rgba(170,205,220,0.08),transparent_18%),radial-gradient(circle_at_18%_100%,rgba(243,227,208,0.06),transparent_24%)]">
            {children}
          </div>
        </main>
      </div>
    </AuthGate>
  );
}
