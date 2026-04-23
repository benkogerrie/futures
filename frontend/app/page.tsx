import { PriceChart } from "@/components/price-chart";
import { RiskMonitor } from "@/components/risk-monitor";
import { TopBar } from "@/components/top-bar";
import { getDashboardData } from "@/lib/dashboard-api";

/** Elke request opnieuw data ophalen (nodig voor Vercel + runtime DASHBOARD_API_URL). */
export const dynamic = "force-dynamic";

export default async function Home() {
  const dashboardData = await getDashboardData();
  const isApiSource = dashboardData.source === "api";

  return (
    <main className="min-h-screen bg-background px-6 py-8 text-copy lg:px-8">
      <div className="mx-auto max-w-[1600px] space-y-6">
        <header className="flex flex-col gap-3 border-b border-border pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.32em] text-accent">NDQ ALN Vibe</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Quant Trading Dashboard</h1>
          </div>
          <div className="rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-muted shadow-glow">
            Bonds are treated strictly as collateral and excluded from tradable exposure.
          </div>
        </header>

        <div
          className={`rounded-2xl border px-4 py-3 text-sm shadow-glow ${
            isApiSource ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" : "border-amber-500/40 bg-amber-500/10 text-amber-200"
          }`}
        >
          <p>{dashboardData.statusMessage}</p>
          {isApiSource && dashboardData.diagnostics ? (
            <p className="mt-2 border-t border-emerald-500/20 pt-2 font-mono text-xs text-emerald-100/90">
              Backend: {dashboardData.diagnostics.backendHost} · {dashboardData.diagnostics.overviewMetricCount} velden
              in de grid · valuta {dashboardData.diagnostics.currency} · voorbeeld cash saldo{" "}
              {dashboardData.diagnostics.cashBalanceSample.toLocaleString("nl-NL", {
                maximumFractionDigits: 2,
              })}
            </p>
          ) : null}
        </div>

        <TopBar snapshot={dashboardData.snapshot} />

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
          <PriceChart snapshot={dashboardData.snapshot} />
          <RiskMonitor snapshot={dashboardData.snapshot} />
        </section>
      </div>
    </main>
  );
}
