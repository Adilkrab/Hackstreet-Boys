// One place to change the product name, demo shop and demo users.

export const APP_NAME = "Stock Manager";
export const APP_TAGLINE = "Stock counts you can trust";
export const SHOP_NAME = "Kedai Ah Lee (demo shop)";

// These mirror the rule in backend/services/automation.py.
// The backend makes the real decision; the frontend only uses these
// to explain the decision to the user before and after they submit.
export const AUTO_FIX_MAX_UNITS = 2;
export const AUTO_FIX_MAX_RM = 50;

// Simulated login (allowed by the Domain 2 brief).
// "name" is what gets written into the activity log.
export const ROLES = {
  owner: {
    key: "owner",
    label: "Owner",
    name: "Puan Aisyah (Owner)",
    greeting: "Puan Aisyah",
    canApprove: true,
    canManageProducts: true,
  },
  clerk: {
    key: "clerk",
    label: "Stock clerk",
    name: "Ravi (Stock clerk)",
    greeting: "Ravi",
    canApprove: false,
    canManageProducts: false,
  },
};
