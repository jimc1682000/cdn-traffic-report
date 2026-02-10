/**
 * Deterministic mock data for integration tests.
 * Values are fixed so test assertions can match exactly.
 */
window.MOCK_DATA = {
  kpiCards: [
    { title: "Edge", value: "12.34", unit: "Terabytes" },
    { title: "Origin", value: "4.56", unit: "Terabytes" },
    { title: "Midgress", value: "7.89", unit: "Gigabytes" },
    { title: "Edge vs. Origin", value: "56.78", unit: "%" }
  ],
  geographyRows: [
    { country: "ID", bytes: "9,870,000,000,000" },
    { country: "TW", bytes: "21,000,000,000" },
    { country: "SG", bytes: "3,400,000,000" }
  ],
  cpCodes: ["100001", "100002", "100003", "100004"],
  initialMonth: { year: 2026, month: 0 }  // January (0-indexed)
};
