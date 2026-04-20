import { MetricCard } from "@/components/metric-card";
import { PortfolioSnapshot } from "@/lib/mock-data";

type TopBarProps = {
  snapshot: PortfolioSnapshot;
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

export function TopBar({ snapshot }: TopBarProps) {
  return (
    <section className="grid gap-4 xl:grid-cols-5">
      {snapshot.overviewMetrics.map((metric) => (
        <MetricCard
          key={metric.label}
          label={metric.label}
          value={formatCurrency(metric.value)}
          tone={metric.tone}
        />
      ))}
    </section>
  );
}
