import clsx from "clsx";

type MetricCardProps = {
  label: string;
  value: string;
  tone?: "neutral" | "success" | "warning";
};

const toneStyles: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  neutral: "border-border bg-surface",
  success: "border-emerald-500/30 bg-emerald-500/5",
  warning: "border-amber-500/30 bg-amber-500/5",
};

export function MetricCard({ label, value, tone = "neutral" }: MetricCardProps) {
  return (
    <div className={clsx("rounded-2xl border p-4 shadow-glow", toneStyles[tone])}>
      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-copy">{value}</p>
    </div>
  );
}
