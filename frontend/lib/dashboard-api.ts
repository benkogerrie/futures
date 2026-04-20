import { portfolioSnapshot, PortfolioSnapshot } from "@/lib/mock-data";

type DashboardApiResponse = {
  accountOverview: {
    cashBalance: number;
    openOptionsValue: number;
    bondCollateralLtv90: number;
    totalMarginAvailable: number;
    totalAccountValue: number;
  };
  risk: {
    instrument: string;
    currentLongFutures: number;
    hardLimit: number;
  };
};

export type DashboardDataResult = {
  snapshot: PortfolioSnapshot;
  source: "api" | "mock";
  statusMessage: string;
};

function mapToPortfolioSnapshot(payload: DashboardApiResponse): PortfolioSnapshot {
  const utilization = payload.risk.currentLongFutures / payload.risk.hardLimit;

  let riskTone: PortfolioSnapshot["riskTone"] = "success";
  let riskLabel = "Controlled Risk";

  if (utilization >= 0.9) {
    riskTone = "danger";
    riskLabel = "Limit Risk";
  } else if (utilization >= 0.65) {
    riskTone = "warning";
    riskLabel = "Elevated Risk";
  }

  return {
    symbol: payload.risk.instrument,
    futuresPosition: payload.risk.currentLongFutures,
    hardLimit: payload.risk.hardLimit,
    totalAccountValue: payload.accountOverview.totalAccountValue,
    marginAvailable: payload.accountOverview.totalMarginAvailable,
    riskLabel,
    riskTone,
    overviewMetrics: [
      { label: "Cash Balance", value: payload.accountOverview.cashBalance },
      { label: "Open Options Value", value: payload.accountOverview.openOptionsValue },
      { label: "Bond Collateral @ 90% LTV", value: payload.accountOverview.bondCollateralLtv90, tone: "success" },
      { label: "Total Margin Available", value: payload.accountOverview.totalMarginAvailable, tone: "success" },
      { label: "Total Account Value", value: payload.accountOverview.totalAccountValue },
    ],
    // Sprint 1 keeps chart overlays mocked until market data integration.
    priceSeries: portfolioSnapshot.priceSeries,
  };
}

export async function getDashboardData(): Promise<DashboardDataResult> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;

  if (!baseUrl) {
    return {
      snapshot: portfolioSnapshot,
      source: "mock",
      statusMessage: "NEXT_PUBLIC_API_URL ontbreekt, dashboard draait op mock-data.",
    };
  }

  try {
    const response = await fetch(`${baseUrl}/api/dashboard`, {
      method: "GET",
      next: { revalidate: 15 },
    });

    if (!response.ok) {
      throw new Error(`API status ${response.status}`);
    }

    const payload = (await response.json()) as DashboardApiResponse;

    return {
      snapshot: mapToPortfolioSnapshot(payload),
      source: "api",
      statusMessage: "Live accountgegevens geladen via Railway API.",
    };
  } catch (error) {
    return {
      snapshot: portfolioSnapshot,
      source: "mock",
      statusMessage: `API fallback actief (${error instanceof Error ? error.message : "onbekende fout"}).`,
    };
  }
}
