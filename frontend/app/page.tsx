import { PriceChart } from "@/components/price-chart";
import { RiskMonitor } from "@/components/risk-monitor";
import { TopBar } from "@/components/top-bar";
import { portfolioSnapshot } from "@/lib/mock-data";

export default function Home() {
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

        <TopBar snapshot={portfolioSnapshot} />

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
          <PriceChart snapshot={portfolioSnapshot} />
          <RiskMonitor snapshot={portfolioSnapshot} />
        </section>
      </div>
    </main>
  );
}
