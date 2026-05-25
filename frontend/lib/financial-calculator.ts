export type FinancialMode = "simple_interest" | "compound_interest" | "present_value" | "future_value";

export type FinancialCalculation = {
  formula: string;
  value: number;
  result: string;
  description: string;
};

export function calculateFinancialValue({
  financialMode,
  principal,
  ratePercent,
  time,
  frequency
}: {
  financialMode: FinancialMode;
  principal: number;
  ratePercent: number;
  time: number;
  frequency: number;
}): FinancialCalculation {
  const safePrincipal = Number.isFinite(principal) ? principal : 0;
  const safeRate = Number.isFinite(ratePercent) ? ratePercent / 100 : 0;
  const safeTime = Number.isFinite(time) ? time : 0;
  const safeFrequency = Number.isFinite(frequency) && frequency > 0 ? frequency : 1;

  if (financialMode === "compound_interest") {
    const amount = safePrincipal * (1 + safeRate / safeFrequency) ** (safeFrequency * safeTime);
    return {
      formula: "A = P(1 + r/n)^(nt)",
      value: amount,
      result: formatMoney(amount),
      description: "Compound interest adds interest repeatedly during the time period."
    };
  }

  if (financialMode === "present_value") {
    const value = safePrincipal / (1 + safeRate) ** safeTime;
    return {
      formula: "PV = FV / (1 + r)^t",
      value,
      result: formatMoney(value),
      description: "Present value estimates what a future amount is worth today."
    };
  }

  if (financialMode === "future_value") {
    const value = safePrincipal * (1 + safeRate) ** safeTime;
    return {
      formula: "FV = PV(1 + r)^t",
      value,
      result: formatMoney(value),
      description: "Future value estimates what today's amount grows into later."
    };
  }

  const amount = safePrincipal * (1 + safeRate * safeTime);
  return {
    formula: "A = P(1 + rt)",
    value: amount,
    result: formatMoney(amount),
    description: "Simple interest applies the same yearly interest rate to the original principal."
  };
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(Number.isFinite(value) ? value : 0);
}
