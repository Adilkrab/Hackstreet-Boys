import { Badge } from "./ui.jsx";
import { stockStatus } from "../utils/format.js";

export default function StockBadge({ product }) {
  const status = stockStatus(product);
  if (status === "out") return <Badge tone="bad">Out of stock</Badge>;
  if (status === "low") return <Badge tone="warn">Low stock</Badge>;
  return <Badge tone="good">OK</Badge>;
}
