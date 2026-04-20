export type OverviewMetric = {
  label: string;
  value: number;
  tone?: "neutral" | "success" | "warning";
};

export type PricePoint = {
  time: string;
  price: number;
  asiaHigh: number;
  asiaLow: number;
  londonHigh: number;
  londonLow: number;
  newYorkHigh: number;
  newYorkLow: number;
  vwap: number;
};

export type PortfolioSnapshot = {
  symbol: string;
  futuresPosition: number;
  hardLimit: number;
  totalAccountValue: number;
  marginAvailable: number;
  riskLabel: string;
  riskTone: "success" | "warning" | "danger";
  overviewMetrics: OverviewMetric[];
  priceSeries: PricePoint[];
};

const basePrice = 21340;

const offsets = [
  -58, -42, -24, -18, -30, -12, 4, 22, 18, 35, 28, 41, 56, 48, 66, 61, 78, 92,
];

export const portfolioSnapshot: PortfolioSnapshot = {
  symbol: "NDQ",
  futuresPosition: 34,
  hardLimit: 50,
  totalAccountValue: 24_100_000,
  marginAvailable: 17_380_000,
  riskLabel: "Controlled Risk",
  riskTone: "warning",
  overviewMetrics: [
    { label: "Cash Balance", value: 5_100_000 },
    { label: "Open Options Value", value: 6_720_000 },
    { label: "Bond Collateral @ 90% LTV", value: 12_280_000, tone: "success" },
    { label: "Total Margin Available", value: 17_380_000, tone: "success" },
    { label: "Total Account Value", value: 24_100_000 },
  ],
  priceSeries: offsets.map((offset, index) => {
    const price = basePrice + offset;

    return {
      time: `${String(7 + index).padStart(2, "0")}:00`,
      price,
      asiaHigh: 21365,
      asiaLow: 21270,
      londonHigh: 21425,
      londonLow: 21310,
      newYorkHigh: 21485,
      newYorkLow: 21355,
      vwap: 21372 + Math.round(offset * 0.15),
    };
  }),
};
