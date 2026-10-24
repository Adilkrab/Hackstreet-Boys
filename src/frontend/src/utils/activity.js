import { rm, signed } from "./format.js";

// Friendly names and colours for each audit action type from the backend.
export const ACTIONS = {
  DISCREPANCY_DETECTED: { label: "Mismatch found", tone: "warn" },
  AUTO_ADJUSTED: { label: "Auto-fixed", tone: "info" },
  APPROVAL_GRANTED: { label: "Approved", tone: "good" },
  APPROVAL_REJECTED: { label: "Rejected", tone: "bad" },
  STOCK_IN: { label: "Stock in", tone: "good" },
  STOCK_OUT: { label: "Stock out", tone: "neutral" },
  PRODUCT_CREATED: { label: "Product added", tone: "neutral" },
  PRODUCT_UPDATED: { label: "Product edited", tone: "neutral" },
  INVENTORY_IMPORTED: { label: "Spreadsheet import", tone: "neutral" },
  ORBYTE_SYNC: { label: "Orbyte sync", tone: "info" },
};

const FIELD_NAMES = {
  sku: "SKU",
  name: "name",
  unit_price: "price",
  low_stock_threshold: "low-stock level",
};

// One plain-English sentence per audit entry.
export function describeLog(log, productName = "a product") {
  const d = log.details || {};
  const notes = d.notes ? ` Note: "${d.notes}"` : "";
  switch (log.action_type) {
    case "PRODUCT_CREATED":
      return `Added ${productName} (${d.sku}) with ${d.opening_quantity} in stock.`;
    case "PRODUCT_UPDATED":
      return `Edited ${productName}: ${Object.keys(d.after || {})
        .map((key) => `${FIELD_NAMES[key] || key} ${d.before?.[key]} → ${d.after[key]}`)
        .join(", ")}.`;
    case "STOCK_IN":
      return `Received ${d.discrepancy_delta} × ${productName} (${d.before_quantity} → ${d.after_quantity}). Reason: ${d.reason}.`;
    case "STOCK_OUT":
      return `Removed ${Math.abs(d.discrepancy_delta)} × ${productName} (${d.before_quantity} → ${d.after_quantity}). Reason: ${d.reason}.`;
    case "INVENTORY_IMPORTED":
      return `Imported ${d.created_count} product${d.created_count === 1 ? "" : "s"} from a spreadsheet.`;
    case "DISCREPANCY_DETECTED":
      return `Shelf count for ${productName} was ${d.physical_counted_qty} but the system had ${d.before_quantity} (${signed(d.discrepancy_delta)}, ${rm(d.financial_impact)}). Sent to the owner for approval.`;
    case "AUTO_ADJUSTED":
      return d.discrepancy_delta === 0
        ? `Shelf count for ${productName} matched the system (${d.physical_counted_qty}). Nothing to fix.`
        : `Small difference on ${productName} (${signed(d.discrepancy_delta)}, ${rm(d.financial_impact)}) fixed automatically: ${d.before_quantity} → ${d.after_quantity}.`;
    case "APPROVAL_GRANTED":
      return `Approved request #${d.request_id}: ${productName} corrected ${d.before_quantity} → ${d.after_quantity}.${notes}`;
    case "APPROVAL_REJECTED":
      return `Rejected request #${d.request_id} for ${productName}. Stock stays at ${d.before_quantity}.${notes}`;
    case "ORBYTE_SYNC":
      return `Prepared ${d.inventory_change_count} stock change${d.inventory_change_count === 1 ? "" : "s"} and ${d.low_stock_alert_count} low-stock alert${d.low_stock_alert_count === 1 ? "" : "s"} for Orbyte (simulated, nothing sent).`;
    default:
      return log.action_type;
  }
}
