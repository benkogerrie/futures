"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PortfolioSnapshot } from "@/lib/mock-data";

type PriceChartProps = {
  snapshot: PortfolioSnapshot;
};

const formatNumber = (value: number) => value.toLocaleString("en-US");

export function PriceChart({ snapshot }: PriceChartProps) {
  return (
    <section className="rounded-3xl border border-border bg-surface p-6 shadow-glow">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted">Main View</p>
          <h2 className="mt-2 text-xl font-semibold text-copy">{snapshot.symbol} Price Action</h2>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs text-muted md:grid-cols-4">
          <div className="rounded-xl border border-border bg-panel px-3 py-2">ALN Asia</div>
          <div className="rounded-xl border border-border bg-panel px-3 py-2">ALN London</div>
          <div className="rounded-xl border border-border bg-panel px-3 py-2">ALN New York</div>
          <div className="rounded-xl border border-border bg-panel px-3 py-2">VWAP Overlay</div>
        </div>
      </div>

      <div className="mt-6 h-[420px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={snapshot.priceSeries} margin={{ top: 12, right: 18, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="#7f8da3" tickLine={false} axisLine={false} />
            <YAxis
              stroke="#7f8da3"
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => formatNumber(value)}
              domain={["dataMin - 40", "dataMax + 40"]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0b1220",
                border: "1px solid #1e293b",
                borderRadius: 16,
                color: "#d8e1f0",
              }}
              formatter={(value: number) => formatNumber(value)}
            />
            <Legend wrapperStyle={{ color: "#d8e1f0" }} />
            <Line type="monotone" dataKey="price" name="NDQ" stroke="#38bdf8" strokeWidth={3} dot={false} />
            <Line type="monotone" dataKey="vwap" name="VWAP" stroke="#facc15" strokeWidth={2} dot={false} />
            <Line type="stepAfter" dataKey="asiaHigh" name="Asia High" stroke="#22c55e" strokeDasharray="4 4" dot={false} />
            <Line type="stepAfter" dataKey="asiaLow" name="Asia Low" stroke="#22c55e" strokeDasharray="2 6" dot={false} />
            <Line type="stepAfter" dataKey="londonHigh" name="London High" stroke="#fb923c" strokeDasharray="4 4" dot={false} />
            <Line type="stepAfter" dataKey="londonLow" name="London Low" stroke="#fb923c" strokeDasharray="2 6" dot={false} />
            <Line type="stepAfter" dataKey="newYorkHigh" name="New York High" stroke="#f87171" strokeDasharray="4 4" dot={false} />
            <Line type="stepAfter" dataKey="newYorkLow" name="New York Low" stroke="#f87171" strokeDasharray="2 6" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
