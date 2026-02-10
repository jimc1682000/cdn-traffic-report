/**
 * Deterministic mock data for integration tests.
 * Values are fixed so test assertions can match exactly.
 */
window.MOCK_DATA = {
  kpiCards: [
    { title: "Edge", value: "170.82", unit: "Terabytes" },
    { title: "Origin", value: "61.25", unit: "Terabytes" },
    { title: "Midgress", value: "43.89", unit: "Gigabytes" },
    { title: "Edge vs. Origin", value: "64.14", unit: "%" }
  ],
  geographyRows: [
    { country: "ID", bytes: "168,776,644,787,204" },
    { country: "TW", bytes: "31,398,058,511" },
    { country: "SG", bytes: "5,234,567,890" }
  ],
  cpCodes: ["960172", "578716", "1415558", "1421896"],
  initialMonth: { year: 2026, month: 0 }  // January (0-indexed)
};
