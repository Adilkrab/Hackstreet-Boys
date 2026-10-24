// The TRIGGER of the automated journey: a clerk records what is really on the shelf.
import { useEffect, useState } from "react";
import { useApp } from "../context.js";
import { api } from "../services/api.js";
import { useLoad } from "../utils/useLoad.js";
import { explainDecision, joinReasons, rm, signed } from "../utils/format.js";
import { AUTO_FIX_MAX_RM, AUTO_FIX_MAX_UNITS } from "../config.js";
import { ErrorBox, Icon, Loading, PageHeader } from "../components/ui.jsx";

const COUNT_REASONS = ["Routine shelf count", "Damaged stock found", "Items missing", "Extra stock found in storeroom"];

export default function StockCount({ initialProductId }) {
  const { role, notify, refresh, refreshKey, goTo } = useApp();
  const { data: products, error: loadError, loading } = useLoad(() => api.products(), [refreshKey]);

  const [productId, setProductId] = useState(initialProductId ? String(initialProductId) : "");
  const [counted, setCounted] = useState("");
  const [reason, setReason] = useState(COUNT_REASONS[0]);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null); // { request, product }

  useEffect(() => {
    if (initialProductId) setProductId(String(initialProductId));
  }, [initialProductId]);

  if (loading && !products) return <Loading />;

  const product = products?.find((p) => String(p.id) === productId);
  const countedNumber = counted === "" ? null : Number(counted);
  const countValid = countedNumber !== null && Number.isInteger(countedNumber);
  const preview =
    product && countValid
      ? explainDecision({ systemQty: product.system_quantity, countedQty: countedNumber, unitPrice: product.unit_price })
      : null;

  const submit = async (e) => {
    e.preventDefault();
    if (!product || !countValid || !reason.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const request = await api.submitCount({
        product_id: product.id,
        physical_counted_qty: countedNumber,
        submitted_by: role.name,
        reason: reason.trim(),
      });
      setResult({ request, product });
      notify(
        request.status === "AUTO_APPROVED" ? "Count saved and stock updated." : "Mismatch sent to the owner for approval.",
        request.status === "AUTO_APPROVED" ? "good" : "info"
      );
      refresh();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  };

  const reset = () => {
    setResult(null);
    setCounted("");
    setProductId("");
    setReason(COUNT_REASONS[0]);
  };

  if (result) return <CountResult {...result} onAgain={reset} goTo={goTo} canApprove={role.canApprove} />;

  return (
    <>
      <PageHeader
        title="Stock count"
        subtitle="Count what is physically on the shelf. The app checks it against the system for you."
      />
      <ErrorBox error={loadError} />

      <div className="count-layout">
        <form className="card form" onSubmit={submit}>
          <label className="field">
            <span>
              <span className="step-num">1</span> Which product did you count?
            </span>
            <select className="input" value={productId} onChange={(e) => setProductId(e.target.value)} required>
              <option value="">Choose a product…</option>
              {products?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.sku})
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>
              <span className="step-num">2</span> How many are on the shelf?
            </span>
            <input
              className="input input-big"
              type="number"
              step="1"
              inputMode="numeric"
              value={counted}
              onChange={(e) => setCounted(e.target.value)}
              placeholder="0"
              required
            />
            <span className="muted small">Type the full amount you counted, not the difference.</span>
          </label>

          <div className="field">
            <span>
              <span className="step-num">3</span> Reason
            </span>
            <div className="chips">
              {COUNT_REASONS.map((r) => (
                <button type="button" key={r} className={`chip ${reason === r ? "on" : ""}`} onClick={() => setReason(r)}>
                  {r}
                </button>
              ))}
            </div>
            <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={2000} required />
          </div>

          <ErrorBox error={error} />

          <button className="btn btn-primary btn-block" disabled={!product || !countValid || !reason.trim() || saving}>
            {saving ? "Submitting…" : "Submit count"}
          </button>
        </form>

        <aside className="card preview">
          <h2 className="card-title">What will happen</h2>
          {!product ? (
            <p className="muted">Choose a product to see its system stock.</p>
          ) : (
            <>
              <div className="compare">
                <div>
                  <span className="muted small">System says</span>
                  <strong>{product.system_quantity}</strong>
                </div>
                <div>
                  <span className="muted small">You counted</span>
                  <strong>{countValid ? countedNumber : "–"}</strong>
                </div>
                <div>
                  <span className="muted small">Difference</span>
                  <strong className={preview?.delta < 0 ? "text-bad" : preview?.delta > 0 ? "text-info" : ""}>
                    {preview ? signed(preview.delta) : "–"}
                  </strong>
                </div>
              </div>
              {preview && (
                <>
                  <p className="muted small">
                    Value of the difference: <strong>{rm(preview.impact)}</strong> at {rm(product.unit_price)} each
                  </p>
                  {preview.delta === 0 ? (
                    <div className="callout callout-good">
                      <Icon name="check" /> Matches the system. It will be logged and nothing changes.
                    </div>
                  ) : preview.autoFix ? (
                    <div className="callout callout-good">
                      <Icon name="check" />
                      <div>
                        <strong>Small difference: fixed automatically.</strong> Stock will be set to {countedNumber}.
                      </div>
                    </div>
                  ) : (
                    <div className="callout callout-warn">
                      <Icon name="approvals" />
                      <div>
                        <strong>Needs owner approval</strong> because {joinReasons(preview.reasons)}. Stock stays at{" "}
                        {product.system_quantity} until the owner decides.
                      </div>
                    </div>
                  )}
                </>
              )}
              <p className="muted small rule">
                Rule: differences of up to {AUTO_FIX_MAX_UNITS} units <em>and</em> under RM{AUTO_FIX_MAX_RM} are fixed
                automatically. Anything bigger goes to the owner.
              </p>
            </>
          )}
        </aside>
      </div>
    </>
  );
}

function CountResult({ request, product, onAgain, goTo, canApprove }) {
  const auto = request.status === "AUTO_APPROVED";
  const { reasons } = explainDecision({
    systemQty: request.recorded_system_qty,
    countedQty: request.physical_counted_qty,
    unitPrice: request.unit_price_snapshot,
  });

  return (
    <>
      <PageHeader title="Count submitted" subtitle={`${product.name} · request #${request.id}`} />
      <section className={`card result ${auto ? "result-good" : "result-warn"}`}>
        <div className="result-icon">
          <Icon name={auto ? "check" : "approvals"} size={28} />
        </div>
        <div>
          {request.discrepancy_delta === 0 ? (
            <h2>Count matches the system</h2>
          ) : auto ? (
            <h2>Fixed automatically</h2>
          ) : (
            <h2>Sent to the owner for approval</h2>
          )}
          <p>
            System had <strong>{request.recorded_system_qty}</strong>, you counted{" "}
            <strong>{request.physical_counted_qty}</strong> ({signed(request.discrepancy_delta)},{" "}
            {rm(request.financial_impact)}).
          </p>
          <p className="muted">
            {request.discrepancy_delta === 0
              ? "Nothing needed changing. The count is saved in the activity log."
              : auto
                ? `The difference was small (≤${AUTO_FIX_MAX_UNITS} units and under RM${AUTO_FIX_MAX_RM}), so stock was updated to ${request.physical_counted_qty} and logged.`
                : `This needs a decision because ${joinReasons(reasons)}. Stock is unchanged until the owner approves.`}
          </p>
          <div className="form-actions left">
            <button className="btn btn-primary" onClick={onAgain}>
              Count another product
            </button>
            {!auto && canApprove && (
              <button className="btn" onClick={() => goTo("approvals")}>
                Review it now
              </button>
            )}
            <button className="btn" onClick={() => goTo("activity")}>
              See activity log
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
