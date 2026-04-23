import { MetricCard } from "@/components/metric-card";
import { PortfolioSnapshot } from "@/lib/mock-data";

type TopBarProps = {
  snapshot: PortfolioSnapshot;
};

function formatMoney(value: number, currency: string, maxFractionDigits: number) {
  return new Intl.NumberFormat("nl-NL", {
    style: "currency",
    currency,
    maximumFractionDigits: maxFractionDigits,
    minimumFractionDigits: Math.min(2, maxFractionDigits),
  }).format(value);
}

export function TopBar({ snapshot }: TopBarProps) {
  const ccy = snapshot.displayCurrency ?? "USD";
  const dec = snapshot.currencyDecimals ?? 0;

  return (
    <section className="grid gap-4 xl:grid-cols-[repeat(auto-fit,minmax(160px,1fr))]">
      {snapshot.overviewMetrics.map((metric) => (
        <MetricCard
          key={metric.label}
          label={metric.label}
          value={metric.display ?? formatMoney(metric.value, ccy, dec)}
          tone={metric.tone}
        />
      ))}
    </section>
  );
}
