import clsx from "clsx";
import { PortfolioSnapshot } from "@/lib/mock-data";

type RiskMonitorProps = {
  snapshot: PortfolioSnapshot;
};

const toneMap = {
  success: {
    bar: "from-emerald-500 to-emerald-300",
    badge: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  },
  warning: {
    bar: "from-amber-500 to-orange-300",
    badge: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  },
  danger: {
    bar: "from-rose-600 to-red-400",
    badge: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  },
} as const;

export function RiskMonitor({ snapshot }: RiskMonitorProps) {
  const exposureRatio = Math.min(snapshot.futuresPosition / snapshot.hardLimit, 1);
  const exposureWidth = `${Math.round(exposureRatio * 100)}%`;
  const styles = toneMap[snapshot.riskTone];

  return (
    <aside className="rounded-3xl border border-border bg-surface p-6 shadow-glow">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted">Risk Monitor</p>
          <h2 className="mt-2 text-xl font-semibold text-copy">NDQ Futures Exposure</h2>
        </div>
        <span className={clsx("rounded-full border px-3 py-1 text-xs font-medium", styles.badge)}>
          {snapshot.riskLabel}
        </span>
      </div>

      <div className="mt-8 space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-4xl font-semibold text-copy">{snapshot.futuresPosition}</p>
            <p className="text-sm text-muted">Current Long Contracts</p>
          </div>
          <div className="text-right">
            <p className="text-lg font-medium text-copy">{snapshot.hardLimit}</p>
            <p className="text-sm text-muted">Hard Limit</p>
          </div>
        </div>

        <div className="h-4 overflow-hidden rounded-full bg-slate-900">
          <div className={clsx("h-full rounded-full bg-gradient-to-r", styles.bar)} style={{ width: exposureWidth }} />
        </div>

        <div className="grid gap-3 rounded-2xl border border-border bg-panel/70 p-4 text-sm text-muted">
          <div className="flex items-center justify-between">
            <span>Utilization</span>
            <span className="font-medium text-copy">{(exposureRatio * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Remaining Capacity</span>
            <span className="font-medium text-copy">{snapshot.hardLimit - snapshot.futuresPosition} contracts</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Tradable Universe</span>
            <span className="font-medium text-copy">E-mini NDQ + NDQ Listed Options</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Bond Inventory</span>
            <span className="font-medium text-copy">Collateral Only</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
