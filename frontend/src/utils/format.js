import { AUTO_FIX_MAX_RM, AUTO_FIX_MAX_UNITS } from "../config.js";

// Money arrives from the backend as strings like "49.80".
export function rm(value) {
  const number = Number(value ?? 0);
  return `RM ${number.toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function signed(n) {
  return n > 0 ? `+${n}` : `${n}`;
}

// SQLite returns times without a timezone; they are UTC.
export function toDate(iso) {
  if (!iso) return null;
  let text = String(iso).replace(/(\.\d{3})\d+/, "$1");
  if (!/[zZ]|[+-]\d\d:?\d\d$/.test(text)) text += "Z";
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function dateTime(iso) {
  const date = toDate(iso);
  if (!date) return "—";
  return date.toLocaleString("en-MY", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function timeAgo(iso) {
  const date = toDate(iso);
  if (!date) return "";
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return dateTime(iso);
}

export function stockStatus(product) {
  if (product.system_quantity === 0) return "out";
  if (product.system_quantity <= product.low_stock_threshold) return "low";
  return "ok";
}

// Explains, in plain words, what the backend rule will decide (or did decide).
export function explainDecision({ systemQty, countedQty, unitPrice }) {
  const delta = countedQty - systemQty;
  const cents = Math.round(Number(unitPrice) * 100) * Math.abs(delta);
  const impact = cents / 100;
  const reasons = [];
  if (countedQty < 0) reasons.push("the count is below zero, which is not possible on a real shelf");
  if (Math.abs(delta) > AUTO_FIX_MAX_UNITS) {
    reasons.push(`the difference is ${Math.abs(delta)} units (more than ${AUTO_FIX_MAX_UNITS})`);
  }
  if (impact >= AUTO_FIX_MAX_RM) reasons.push(`the value is ${rm(impact)} (RM${AUTO_FIX_MAX_RM} or more)`);
  return { delta, impact, autoFix: reasons.length === 0, reasons };
}

export function joinReasons(reasons) {
  if (reasons.length <= 1) return reasons.join("");
  return `${reasons.slice(0, -1).join(", ")} and ${reasons[reasons.length - 1]}`;
}
