import { useState } from "react";
import { useApp } from "../context.js";
import { api } from "../services/api.js";
import { useLoad } from "../utils/useLoad.js";
import { rm, signed, timeAgo } from "../utils/format.js";
import { AUTO_FIX_MAX_RM, AUTO_FIX_MAX_UNITS } from "../config.js";
import { Badge, EmptyState, ErrorBox, Icon, Loading, PageHeader, StatCard } from "../components/ui.jsx";
import ActivityList from "../components/ActivityList.jsx";

const JOURNEY = [
  { title: "Count", text: "Clerk counts what is really on the shelf." },
  { title: "Compare", text: "App compares the count with the system stock." },
  { title: "Decide", text: `Small gaps (≤${AUTO_FIX_MAX_UNITS} units, under RM${AUTO_FIX_MAX_RM}) are fixed automatically.` },
  { title: "Approve", text: "Bigger gaps wait for the owner to approve or reject." },
  { title: "Record", text: "Every step is saved in the activity log." },
];

export default function Dashboard() {
  const { role, refreshKey, goTo, notify, refresh } = useApp();
  const { data, error, loading, reload } = useLoad(
    () => Promise.all([api.products(), api.alerts(), api.pending(), api.auditLogs()]),
    [refreshKey]
  );
  const [sync, setSync] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [showPayload, setShowPayload] = useState(false);

  if (loading && !data) return <Loading />;
  if (!data) return <ErrorBox error={error} onRetry={reload} />;

  const [products, alerts, pending, logs] = data;
  const names = Object.fromEntries(products.map((p) => [p.id, p.name]));
  const stockValue = products.reduce((sum, p) => sum + p.system_quantity * Number(p.unit_price), 0);
  const pendingValue = pending.reduce((sum, r) => sum + Number(r.financial_impact), 0);
  const recent = [...logs].reverse().filter((l) => l.action_type !== "ORBYTE_SYNC").slice(0, 6);

  const runSync = async () => {
    setSyncing(true);
    try {
      const result = await api.orbyteSync(role.name);
      setSync(result);
      notify("Orbyte payload prepared and logged.", "good");
      refresh();
    } catch (e) {
      notify(e.message, "bad");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <>
      <PageHeader
        title={`Selamat datang, ${role.greeting}`}
        subtitle="Here is what needs your attention in the shop today."
      >
        <button className="btn btn-primary" onClick={() => goTo("count")}>
          <Icon name="count" /> Start a stock count
        </button>
      </PageHeader>

      <ErrorBox error={error} onRetry={reload} />

      <section className="stats">
        <StatCard
          label="Waiting for approval"
          value={pending.length}
          hint={pending.length ? `${rm(pendingValue)} of stock in question` : "Nothing waiting"}
          tone={pending.length ? "attention" : "neutral"}
          onClick={() => goTo("approvals")}
        />
        <StatCard
          label="Low or out of stock"
          value={alerts.length}
          hint={alerts.length ? "Reorder soon" : "All stocked"}
          tone={alerts.length ? "warn" : "neutral"}
          onClick={() => goTo("products")}
        />
        <StatCard label="Products tracked" value={products.length} hint="Across the shop" />
        <StatCard label="Stock value" value={rm(stockValue)} hint="At current prices" />
      </section>

      <section className="card journey">
        <h2 className="card-title">How a stock count works</h2>
        <ol className="journey-steps">
          {JOURNEY.map((step, i) => (
            <li key={step.title}>
              <span className="step-num">{i + 1}</span>
              <strong>{step.title}</strong>
              <span className="muted small">{step.text}</span>
            </li>
          ))}
        </ol>
      </section>

      <div className="grid-2">
        <section className="card">
          <div className="card-head">
            <h2 className="card-title">Waiting for approval</h2>
            <button className="link-btn" onClick={() => goTo("approvals")}>
              Open approvals
            </button>
          </div>
          {pending.length === 0 ? (
            <EmptyState title="All clear">No stock mismatches are waiting for a decision.</EmptyState>
          ) : (
            <ul className="mini-list">
              {pending.slice(0, 4).map((r) => (
                <li key={r.id}>
                  <div>
                    <strong>{r.product_name}</strong>
                    <span className="muted small">
                      System {r.recorded_system_qty} → counted {r.physical_counted_qty} · {timeAgo(r.created_at)}
                    </span>
                  </div>
                  <div className="mini-right">
                    <Badge tone={r.discrepancy_delta < 0 ? "bad" : "info"}>{signed(r.discrepancy_delta)}</Badge>
                    <span className="small">{rm(r.financial_impact)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <div className="card-head">
            <h2 className="card-title">Low-stock warnings</h2>
            <button className="link-btn" onClick={() => goTo("products")}>
              See products
            </button>
          </div>
          {alerts.length === 0 ? (
            <EmptyState title="Everything is stocked">No product is at or below its low-stock level.</EmptyState>
          ) : (
            <ul className="mini-list">
              {alerts.map((a) => (
                <li key={a.product_id}>
                  <div>
                    <strong>{a.product_name}</strong>
                    <span className="muted small">
                      {a.sku} · reorder at {a.low_stock_threshold}
                    </span>
                  </div>
                  <div className="mini-right">
                    <Badge tone={a.system_quantity === 0 ? "bad" : "warn"}>
                      {a.system_quantity === 0 ? "Out" : `${a.system_quantity} left`}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <div className="card-head">
            <h2 className="card-title">Recent activity</h2>
            <button className="link-btn" onClick={() => goTo("activity")}>
              Full log
            </button>
          </div>
          {recent.length === 0 ? (
            <EmptyState title="No activity yet" />
          ) : (
            <ActivityList logs={recent} productNames={names} compact />
          )}
        </section>

        <section className="card orbyte">
          <div className="card-head">
            <h2 className="card-title">Share with Orbyte</h2>
            <Badge tone="info">Simulated</Badge>
          </div>
          <p className="muted">
            Send approved stock changes and low-stock alerts to the Orbyte business hub, so purchasing, accounts
            and other Orbyte apps see the same numbers. For this demo the payload is prepared and logged, but not
            sent anywhere.
          </p>
          <button className="btn" onClick={runSync} disabled={syncing}>
            <Icon name="sync" /> {syncing ? "Preparing…" : "Sync to Orbyte now"}
          </button>
          {sync && (
            <div className="sync-result">
              <p>
                <strong>{sync.payload.inventory_changes.length}</strong> stock changes and{" "}
                <strong>{sync.payload.low_stock_alerts.length}</strong> low-stock alerts from the last 24 hours are
                ready for Orbyte (log #{sync.sync_log_id}).
              </p>
              <button className="link-btn" onClick={() => setShowPayload((s) => !s)}>
                {showPayload ? "Hide" : "Show"} data sent to Orbyte
              </button>
              {showPayload && <pre className="payload">{JSON.stringify(sync.payload, null, 2)}</pre>}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
