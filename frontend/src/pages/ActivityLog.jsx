// VISIBLE OUTCOME: every action is recorded, newest first, in plain English.
import { useMemo, useState } from "react";
import { useApp } from "../context.js";
import { api } from "../services/api.js";
import { useLoad } from "../utils/useLoad.js";
import { ACTIONS, describeLog } from "../utils/activity.js";
import { toDate } from "../utils/format.js";
import { EmptyState, ErrorBox, Icon, Loading, PageHeader } from "../components/ui.jsx";
import ActivityList from "../components/ActivityList.jsx";

export default function ActivityLog() {
  const { refreshKey } = useApp();
  const [actionType, setActionType] = useState("");
  const [productId, setProductId] = useState("");

  const { data, error, loading, reload } = useLoad(
    () =>
      Promise.all([
        api.products(),
        api.auditLogs({ action_type: actionType || undefined, product_id: productId || undefined }),
      ]),
    [refreshKey, actionType, productId]
  );

  const products = data?.[0] || [];
  const names = useMemo(() => Object.fromEntries(products.map((p) => [p.id, p.name])), [products]);
  const logs = useMemo(() => [...(data?.[1] || [])].reverse(), [data]);

  const exportCsv = () => {
    const quote = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const rows = [
      ["Time (UTC)", "Who", "Action", "Product", "What happened"],
      ...logs.map((l) => [
        toDate(l.timestamp)?.toISOString() ?? l.timestamp,
        l.actor,
        ACTIONS[l.action_type]?.label ?? l.action_type,
        names[l.product_id] ?? "",
        describeLog(l, names[l.product_id]),
      ]),
    ];
    const blob = new Blob([rows.map((r) => r.map(quote).join(",")).join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "activity-log.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageHeader
        title="Activity log"
        subtitle="A permanent record of who did what and when. Entries cannot be edited or deleted from the app."
      >
        <button className="btn" onClick={exportCsv} disabled={!logs.length}>
          <Icon name="download" /> Export CSV
        </button>
      </PageHeader>

      <div className="toolbar">
        <select className="input" value={actionType} onChange={(e) => setActionType(e.target.value)} aria-label="Filter by action">
          <option value="">All actions</option>
          {Object.entries(ACTIONS).map(([key, a]) => (
            <option key={key} value={key}>
              {a.label}
            </option>
          ))}
        </select>
        <select className="input" value={productId} onChange={(e) => setProductId(e.target.value)} aria-label="Filter by product">
          <option value="">All products</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <span className="muted small">{logs.length} entries</span>
      </div>

      <ErrorBox error={error} onRetry={reload} />

      {loading && !data ? (
        <Loading />
      ) : logs.length === 0 ? (
        <EmptyState title="No entries match these filters" />
      ) : (
        <section className="card">
          <ActivityList logs={logs} productNames={names} />
        </section>
      )}
    </>
  );
}
