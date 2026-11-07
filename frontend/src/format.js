// Small helpers for showing numbers and dates the same way everywhere.

export const fmtNumber = (n) => Number(n).toLocaleString("en-US");

export const fmtMoney = (n) =>
  "₪" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });

// "2026-11-07T14:51:00" -> "2026-11-07 14:51"
export const fmtDateTime = (iso) => iso.replace("T", " ").slice(0, 16);
