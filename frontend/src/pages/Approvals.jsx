// HUMAN APPROVAL step: the owner approves or rejects bigger stock mismatches.
import { useState } from "react";
import { useApp } from "../context.js";
import { api } from "../services/api.js";
import { useLoad } from "../utils/useLoad.js";
import { dateTime, explainDecision, joinReasons, rm, signed } from "../utils/format.js";
import { Badge, EmptyState, ErrorBox, Icon, Loading, PageHeader } from "../components/ui.jsx";

export default function Approvals() {
  const { role, refreshKey } = useApp();
  const { data: pending, error, loading, reload } = useLoad(() => api.pending(), [refreshKey]);

  return (
    <>
      <PageHeader
        title="Approvals"
        subtitle="Stock mismatches that are too big to fix automatically. Nothing changes until someone decides."
      />

      {!role.canApprove && (
        <div className="callout callout-info">
          <Icon name="lock" />
          <div>
            You are signed in as <strong>{role.name}</strong>. You can see these requests, but only the owner can
            approve or reject them. Switch to <strong>Owner</strong> at the top to decide.
          </div>
        </div>
      )}

      <ErrorBox error={error} onRetry={reload} />

      {loading && !pending ? (
        <Loading />
      ) : !pending?.length ? (
        <EmptyState title="All clear">No stock mismatches are waiting for approval.</EmptyState>
      ) : (
        <div className="approval-list">
          {pending.map((request) => (
            <ApprovalCard key={request.id} request={request} />
          ))}
        </div>
      )}
    </>
  );
}

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

function ApprovalCard({ request }) {
  const { role, notify, refresh } = useApp();
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(null); // "APPROVE" | "REJECT"
  const [error, setError] = useState(null);

  const { reasons } = explainDecision({
    systemQty: request.recorded_system_qty,
    countedQty: request.physical_counted_qty,
    unitPrice: request.unit_price_snapshot,
  });
  const negative = request.physical_counted_qty < 0;
  const blockApprove = negative || request.is_stale;

  const decide = async (action) => {
    setBusy(action);
    setError(null);
    try {
      await api.review(request.id, { action, manager_name: role.name, notes: notes.trim() });
      notify(
        action === "APPROVE"
          ? `Approved. ${request.product_name} is now ${request.physical_counted_qty}.`
          : `Rejected. ${request.product_name} stays at ${request.current_system_quantity}.`,
        action === "APPROVE" ? "good" : "info"
      );
      refresh();
    } catch (err) {
      setError(err);
      if (err.status === 409 || err.status === 400) refresh();
    } finally {
      setBusy(null);
    }
  };

  return (
    <article className="card approval">
      <header className="approval-head">
        <div>
          <h2>{request.product_name}</h2>
          <span className="muted small">
            {request.sku} · request #{request.id} · {dateTime(request.created_at)}
          </span>
        </div>
        <Badge tone="attention">Waiting</Badge>
      </header>

      <div className="compare">
        <div>
          <span className="muted small">System had</span>
          <strong>{request.recorded_system_qty}</strong>
        </div>
        <div>
          <span className="muted small">Counted</span>
          <strong>{request.physical_counted_qty}</strong>
        </div>
        <div>
          <span className="muted small">Difference</span>
          <strong className={request.discrepancy_delta < 0 ? "text-bad" : "text-info"}>
            {signed(request.discrepancy_delta)}
          </strong>
        </div>
        <div>
          <span className="muted small">Value</span>
          <strong>{rm(request.financial_impact)}</strong>
        </div>
      </div>

      <dl className="facts">
        <div>
          <dt>Counted by</dt>
          <dd>{request.submitted_by}</dd>
        </div>
        <div>
          <dt>Their reason</dt>
          <dd>{request.reason}</dd>
        </div>
        <div>
          <dt>Why it needs you</dt>
          <dd>{reasons.length ? capitalize(`${joinReasons(reasons)}.`) : "Flagged for review."}</dd>
        </div>
      </dl>

      {request.is_stale && (
        <div className="callout callout-warn">
          <Icon name="alert" />
          <div>
            <strong>Stock changed after this count</strong> (now {request.current_system_quantity}). Approving would
            overwrite newer changes, so reject it and ask for a fresh count.
          </div>
        </div>
      )}
      {negative && (
        <div className="callout callout-warn">
          <Icon name="alert" />
          <div>
            <strong>The count is below zero.</strong> It cannot be approved. Reject it and ask for a corrected count.
          </div>
        </div>
      )}

      <ErrorBox error={error} />

      {role.canApprove ? (
        <div className="decision">
          <input
            className="input"
            placeholder="Note for the log (optional), e.g. checked damaged-goods bin"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={2000}
            aria-label="Review note"
          />
          <div className="decision-buttons">
            <button className="btn btn-danger" onClick={() => decide("REJECT")} disabled={!!busy}>
              <Icon name="x" /> {busy === "REJECT" ? "Rejecting…" : "Reject"}
            </button>
            <button
              className="btn btn-success"
              onClick={() => decide("APPROVE")}
              disabled={!!busy || blockApprove}
              title={blockApprove ? "This request cannot be approved" : undefined}
            >
              <Icon name="check" /> {busy === "APPROVE" ? "Approving…" : `Approve: set stock to ${request.physical_counted_qty}`}
            </button>
          </div>
        </div>
      ) : (
        <p className="muted small lock-note">
          <Icon name="lock" size={14} /> Waiting for the owner to decide.
        </p>
      )}
    </article>
  );
}
