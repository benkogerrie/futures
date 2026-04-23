import {
  FuturesBreakdownRow,
  portfolioSnapshot,
  PortfolioSnapshot,
  PositionSampleRow,
  OverviewMetric,
} from "@/lib/mock-data";

type DashboardApiResponse = {
  meta?: { environment?: string; saxoOpenApi?: boolean };
  accountOverview: Record<string, unknown> & {
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
    marginUtilizationPct?: number;
    marginAndCollateralUtilizationPct?: number;
    openPositionsCount?: number;
    netPositionsCount?: number;
    ordersCount?: number;
    triggerOrdersCount?: number;
    unrealizedMarginProfitLoss?: number;
    unrealizedPositionsValue?: number;
    marginNetExposure?: number;
    futuresBreakdown?: FuturesBreakdownRow[];
  };
  chart: Record<string, unknown> & {
    symbol: string;
    overlays: string[];
  };
  positionsSample?: PositionSampleRow[];
};

export type DashboardDataResult = {
  snapshot: PortfolioSnapshot;
  source: "api" | "mock";
  statusMessage: string;
  /** Alleen bij source=api: bewijs dat de server Railway heeft aangesproken. */
  diagnostics?: {
    backendHost: string;
    overviewMetricCount: number;
    currency: string;
    cashBalanceSample: number;
  };
};

/** Server-side (runtime op Vercel); niet in client-bundle. Fallback: NEXT_PUBLIC_* (build-time). */
function getBackendBaseUrl(): string | undefined {
  const a = process.env.DASHBOARD_API_URL?.trim();
  const b = process.env.NEXT_PUBLIC_API_URL?.trim();
  return a || b || undefined;
}

function safeHost(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return "onbekend";
  }
}

function pickNum(ao: Record<string, unknown>, key: string): number | undefined {
  const v = ao[key];
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  return undefined;
}

function buildOverviewMetrics(ao: Record<string, unknown>): OverviewMetric[] {
  const rows: { label: string; key: string; tone?: OverviewMetric["tone"]; kind?: "count" | "pct" }[] = [
    { label: "Cash saldo", key: "cashBalance" },
    { label: "Cash beschikbaar (trading)", key: "cashAvailableForTrading" },
    { label: "Marge beschikbaar (Saxo)", key: "marginAvailableForTradingRaw", tone: "success" },
    { label: "Totaal marge beschikbaar", key: "totalMarginAvailable", tone: "success" },
    { label: "Collateral / overige zekerheid", key: "bondCollateralLtv90", tone: "success" },
    { label: "Open options waarde (schatting)", key: "openOptionsValue" },
    { label: "Onverwachte marge P/L", key: "unrealizedMarginProfitLoss" },
    { label: "Waarde onverwachte posities", key: "unrealizedPositionsValue" },
    { label: "Netto marge-exposure", key: "marginNetExposure" },
    { label: "Totaal rekeningwaarde", key: "totalAccountValue" },
    { label: "Open posities (Saxo)", key: "openPositionsCount", kind: "count" },
    { label: "Netto posities (Saxo)", key: "netPositionsCount", kind: "count" },
    { label: "Orders open", key: "ordersCount", kind: "count" },
    { label: "Trigger orders", key: "triggerOrdersCount", kind: "count" },
    { label: "Marge-utilisatie %", key: "marginUtilizationPct", kind: "pct" },
    { label: "Marge + collateral util. %", key: "marginAndCollateralUtilizationPct", kind: "pct" },
    { label: "Net equity marge", key: "netEquityForMargin" },
    { label: "Collateral beschikbaar", key: "collateralAvailable", tone: "success" },
    { label: "Transacties nog niet geboekt", key: "transactionsNotBooked" },
    { label: "Posities in feed (sample)", key: "positionsListedCount", kind: "count" },
    { label: "Marktwaarde posities (sample)", key: "positionsTotalMarketValue" },
  ];

  const metrics: OverviewMetric[] = [];
  for (const row of rows) {
    const v = pickNum(ao, row.key);
    if (v === undefined) continue;
    if (row.kind === "count") {
      metrics.push({ label: row.label, value: v, display: String(Math.round(v)), tone: row.tone });
    } else if (row.kind === "pct") {
      metrics.push({ label: row.label, value: v, display: `${v.toFixed(2)}%`, tone: row.tone });
    } else {
      metrics.push({ label: row.label, value: v, tone: row.tone });
    }
  }
  return metrics;
}

function buildRiskDetailRows(risk: DashboardApiResponse["risk"]): { label: string; value: string }[] {
  const rows: { label: string; v: unknown }[] = [
    { label: "Marge-utilisatie", v: risk.marginUtilizationPct },
    { label: "Marge + collateral util.", v: risk.marginAndCollateralUtilizationPct },
    { label: "Open posities", v: risk.openPositionsCount },
    { label: "Netto posities", v: risk.netPositionsCount },
    { label: "Orders open", v: risk.ordersCount },
    { label: "Trigger orders", v: risk.triggerOrdersCount },
    { label: "Onverwachte marge P/L", v: risk.unrealizedMarginProfitLoss },
    { label: "Waarde onverwachte posities", v: risk.unrealizedPositionsValue },
    { label: "Netto marge-exposure", v: risk.marginNetExposure },
  ];
  return rows
    .filter((r) => typeof r.v === "number" && !Number.isNaN(r.v as number))
    .map((r) => {
      const n = r.v as number;
      if (r.label.includes("util")) {
        return { label: r.label, value: `${n.toFixed(2)}%` };
      }
      if (r.label.includes("posities") || r.label.includes("Orders")) {
        return { label: r.label, value: String(Math.round(n)) };
      }
      return { label: r.label, value: n.toLocaleString("nl-NL", { maximumFractionDigits: 2 }) };
    });
}

function mapToPortfolioSnapshot(payload: DashboardApiResponse): PortfolioSnapshot {
  const ao = payload.accountOverview as Record<string, unknown>;
  const risk = payload.risk;
  const chart = payload.chart;

  const utilization = risk.currentLongFutures / Math.max(risk.hardLimit, 1);

  let riskTone: PortfolioSnapshot["riskTone"] = "success";
  let riskLabel = "Controlled Risk";

  if (utilization >= 0.9) {
    riskTone = "danger";
    riskLabel = "Limit Risk";
  } else if (utilization >= 0.65) {
    riskTone = "warning";
    riskLabel = "Elevated Risk";
  }

  const ccy = typeof ao.currency === "string" && ao.currency.length === 3 ? ao.currency : "USD";
  const decRaw = ao.currencyDecimals;
  const currencyDecimals = typeof decRaw === "number" && decRaw >= 0 && decRaw <= 8 ? decRaw : 2;

  const overviewMetrics = buildOverviewMetrics(ao);
  if (overviewMetrics.length === 0) {
    overviewMetrics.push(
      { label: "Cash saldo", value: payload.accountOverview.cashBalance },
      { label: "Open options waarde", value: payload.accountOverview.openOptionsValue },
      { label: "Collateral", value: payload.accountOverview.bondCollateralLtv90, tone: "success" },
      { label: "Totaal marge beschikbaar", value: payload.accountOverview.totalMarginAvailable, tone: "success" },
      { label: "Totaal rekeningwaarde", value: payload.accountOverview.totalAccountValue },
    );
  }

  const riskDetailRows = buildRiskDetailRows(risk);
  const futuresBreakdown = Array.isArray(risk.futuresBreakdown) ? risk.futuresBreakdown : undefined;
  const positionsSample = Array.isArray(payload.positionsSample) ? payload.positionsSample : undefined;

  const chartMeta = {
    anchorPrice: typeof chart.anchorPrice === "number" ? chart.anchorPrice : undefined,
    environment: typeof chart.environment === "string" ? chart.environment : undefined,
    netPositionsReturned: typeof chart.netPositionsReturned === "number" ? chart.netPositionsReturned : undefined,
    calculationReliability:
      typeof chart.calculationReliability === "string" ? chart.calculationReliability : undefined,
  };

  return {
    symbol: risk.instrument,
    futuresPosition: risk.currentLongFutures,
    hardLimit: risk.hardLimit,
    totalAccountValue: payload.accountOverview.totalAccountValue,
    marginAvailable: payload.accountOverview.totalMarginAvailable,
    riskLabel,
    riskTone,
    overviewMetrics,
    priceSeries: portfolioSnapshot.priceSeries,
    displayCurrency: ccy,
    currencyDecimals,
    riskDetailRows: riskDetailRows.length ? riskDetailRows : undefined,
    futuresBreakdown: futuresBreakdown?.length ? futuresBreakdown : undefined,
    positionsSample: positionsSample?.length ? positionsSample : undefined,
    chartMeta,
  };
}

export async function getDashboardData(): Promise<DashboardDataResult> {
  const baseUrl = getBackendBaseUrl();

  if (!baseUrl) {
    return {
      snapshot: portfolioSnapshot,
      source: "mock",
      statusMessage:
        "Geen backend-URL: zet op Vercel **DASHBOARD_API_URL** (aanrader, runtime) of **NEXT_PUBLIC_API_URL** (build-time) naar je Railway-API en deploy opnieuw.",
    };
  }

  try {
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/dashboard`, {
      method: "GET",
      cache: "no-store",
    });

    const rawBody = await response.text();
    if (!response.ok) {
      let detail = "";
      try {
        const j = JSON.parse(rawBody) as { detail?: unknown };
        if (typeof j.detail === "string") detail = j.detail;
        else if (Array.isArray(j.detail))
          detail = j.detail.map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: unknown }).msg) : String(x))).join("; ");
      } catch {
        if (rawBody) detail = rawBody;
      }
      const oneLine = detail.replace(/\s+/g, " ").trim().slice(0, 420);
      throw new Error(`API status ${response.status}${oneLine ? ` — ${oneLine}` : ""}`);
    }

    const payload = JSON.parse(rawBody) as DashboardApiResponse;

    const sim = payload.meta?.environment === "saxo-sim";
    const statusMessage = sim
      ? "SIM: accountdata via Saxo OpenAPI (Railway) — onderstaande cijfers komen uit de API-response."
      : "Live accountgegevens geladen via Railway API.";

    const snapshot = mapToPortfolioSnapshot(payload);
    const ao = payload.accountOverview as Record<string, unknown>;
    const cash = typeof ao.cashBalance === "number" ? ao.cashBalance : snapshot.overviewMetrics[0]?.value ?? 0;

    return {
      snapshot,
      source: "api",
      statusMessage,
      diagnostics: {
        backendHost: safeHost(baseUrl),
        overviewMetricCount: snapshot.overviewMetrics.length,
        currency: snapshot.displayCurrency,
        cashBalanceSample: cash,
      },
    };
  } catch (error) {
    return {
      snapshot: portfolioSnapshot,
      source: "mock",
      statusMessage: `API fallback actief (${error instanceof Error ? error.message : "onbekende fout"}) — host: ${safeHost(baseUrl)}.`,
    };
  }
}
