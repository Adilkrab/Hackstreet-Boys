import { useMemo, useState } from "react";
import { useApp } from "../context.js";
import { api } from "../services/api.js";
import { useLoad } from "../utils/useLoad.js";
import { dateTime, rm, signed, stockStatus } from "../utils/format.js";
import { Badge, EmptyState, ErrorBox, Icon, Loading, Modal, PageHeader } from "../components/ui.jsx";
import StockBadge from "../components/StockBadge.jsx";

export default function Products() {
  const { role, refreshKey, goTo } = useApp();
  const { data: products, error, loading, reload } = useLoad(() => api.products(), [refreshKey]);
  const [search, setSearch] = useState("");
  const [onlyLow, setOnlyLow] = useState(false);
  const [modal, setModal] = useState(null); // { type, product }

  const shown = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (products || []).filter(
      (p) =>
        (!q || p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)) &&
        (!onlyLow || stockStatus(p) !== "ok")
    );
  }, [products, search, onlyLow]);

  const close = () => setModal(null);

  return (
    <>
      <PageHeader title="Products" subtitle="Everything the shop sells, with live stock levels.">
        {role.canManageProducts ? (
          <>
            <button className="btn" onClick={() => setModal({ type: "import" })}>
              <Icon name="upload" /> Import spreadsheet
            </button>
            <button className="btn btn-primary" onClick={() => setModal({ type: "add" })}>
              <Icon name="plus" /> Add product
            </button>
          </>
        ) : (
          <span className="muted small lock-note">
            <Icon name="lock" size={14} /> Only the owner can add or import products
          </span>
        )}
      </PageHeader>

      <ErrorBox error={error} onRetry={reload} />

      <div className="toolbar">
        <input
          className="input search"
          type="search"
          placeholder="Search by name or SKU"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search products"
        />
        <label className="check">
          <input type="checkbox" checked={onlyLow} onChange={(e) => setOnlyLow(e.target.checked)} />
          Only low / out of stock
        </label>
      </div>

      {loading && !products ? (
        <Loading />
      ) : shown.length === 0 ? (
        <EmptyState title="No products found">
          {products?.length ? "Try a different search." : "Add a product or import a spreadsheet to get started."}
        </EmptyState>
      ) : (
        <div className="table-wrap card">
          <table className="table">
            <thead>
              <tr>
                <th>Product</th>
                <th className="num">In stock</th>
                <th className="num hide-sm">Reorder at</th>
                <th className="num hide-sm">Unit price</th>
                <th>Status</th>
                <th className="actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((p) => (
                <tr key={p.id} className={stockStatus(p) !== "ok" ? "row-warn" : ""}>
                  <td>
                    <strong>{p.name}</strong>
                    <span className="muted small block">{p.sku}</span>
                  </td>
                  <td className="num strong">{p.system_quantity}</td>
                  <td className="num hide-sm">{p.low_stock_threshold}</td>
                  <td className="num hide-sm">{rm(p.unit_price)}</td>
                  <td>
                    <StockBadge product={p} />
                  </td>
                  <td className="actions-col">
                    <div className="row-actions">
                      <button className="btn btn-sm" onClick={() => setModal({ type: "IN", product: p })}>
                        <Icon name="arrowIn" size={15} /> In
                      </button>
                      <button className="btn btn-sm" onClick={() => setModal({ type: "OUT", product: p })}>
                        <Icon name="arrowOut" size={15} /> Out
                      </button>
                      <button className="btn btn-sm" onClick={() => goTo("count", { productId: p.id })}>
                        <Icon name="count" size={15} /> Count
                      </button>
                      <button
                        className="icon-btn"
                        title="Stock history"
                        aria-label={`Stock history for ${p.name}`}
                        onClick={() => setModal({ type: "history", product: p })}
                      >
                        <Icon name="history" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(modal?.type === "IN" || modal?.type === "OUT") && (
        <MovementModal product={modal.product} type={modal.type} onClose={close} />
      )}
      {modal?.type === "history" && <HistoryModal product={modal.product} onClose={close} />}
      {modal?.type === "add" && <AddProductModal onClose={close} />}
      {modal?.type === "import" && <ImportModal onClose={close} />}
    </>
  );
}

const MOVEMENT_REASONS = {
  IN: ["Supplier delivery", "Customer return", "Found in storeroom"],
  OUT: ["Customer sale", "Damaged / expired", "Used in shop"],
};

function MovementModal({ product, type, onClose }) {
  const { role, notify, refresh } = useApp();
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState(MOVEMENT_REASONS[type][0]);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const qty = Number(quantity);
  const valid = Number.isInteger(qty) && qty > 0 && reason.trim();
  const after = product.system_quantity + (type === "IN" ? qty : -qty);

  const submit = async (e) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await api.recordMovement({
        product_id: product.id,
        movement_type: type,
        quantity: qty,
        actor: role.name,
        reason: reason.trim(),
      });
      notify(`${type === "IN" ? "Added" : "Removed"} ${qty} × ${product.name}.`);
      refresh();
      onClose();
    } catch (err) {
      setError(err.status === 409 ? new Error(`Not enough stock: only ${product.system_quantity} left.`) : err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={`${type === "IN" ? "Stock in" : "Stock out"}: ${product.name}`} onClose={onClose}>
      <form onSubmit={submit} className="form">
        <p className="muted">Currently in stock: {product.system_quantity}</p>
        <label className="field">
          <span>Quantity</span>
          <input
            className="input"
            type="number"
            min="1"
            step="1"
            inputMode="numeric"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            autoFocus
            required
          />
        </label>
        <div className="field">
          <span>Reason</span>
          <div className="chips">
            {MOVEMENT_REASONS[type].map((r) => (
              <button type="button" key={r} className={`chip ${reason === r ? "on" : ""}`} onClick={() => setReason(r)}>
                {r}
              </button>
            ))}
          </div>
          <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={2000} />
        </div>
        {valid && (
          <p className={after < 0 ? "callout callout-bad" : "callout callout-info"}>
            Stock will go from {product.system_quantity} to {after}.
            {after < 0 && " That is below zero, so it will be refused."}
          </p>
        )}
        <ErrorBox error={error} />
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={!valid || saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

const MOVEMENT_LABELS = { OPENING: "Opening stock", IN: "Stock in", OUT: "Stock out", ADJUSTMENT: "Count correction" };

function HistoryModal({ product, onClose }) {
  const { data, error, loading } = useLoad(() => api.movements(product.id), [product.id]);
  return (
    <Modal title={`Stock history: ${product.name}`} onClose={onClose} wide>
      <ErrorBox error={error} />
      {loading ? (
        <Loading />
      ) : !data?.length ? (
        <EmptyState title="No stock changes yet" />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>When</th>
                <th>Type</th>
                <th className="num">Change</th>
                <th className="num">Stock</th>
                <th>By / reason</th>
              </tr>
            </thead>
            <tbody>
              {[...data].reverse().map((m) => (
                <tr key={m.id}>
                  <td className="nowrap">{dateTime(m.created_at)}</td>
                  <td>
                    <Badge tone={m.movement_type === "ADJUSTMENT" ? "info" : m.delta > 0 ? "good" : "neutral"}>
                      {MOVEMENT_LABELS[m.movement_type] || m.movement_type}
                    </Badge>
                  </td>
                  <td className="num strong">{signed(m.delta)}</td>
                  <td className="num nowrap">
                    {m.before_quantity} → {m.after_quantity}
                  </td>
                  <td>
                    {m.actor}
                    <span className="muted small block">{m.reason}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}

function AddProductModal({ onClose }) {
  const { role, notify, refresh } = useApp();
  const [form, setForm] = useState({ sku: "", name: "", system_quantity: "0", unit_price: "", low_stock_threshold: "5" });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const product = await api.createProduct(
        {
          sku: form.sku.trim(),
          name: form.name.trim(),
          system_quantity: Number(form.system_quantity),
          unit_price: form.unit_price,
          low_stock_threshold: Number(form.low_stock_threshold),
        },
        role.name
      );
      notify(`Added ${product.name}.`);
      refresh();
      onClose();
    } catch (err) {
      setError(err.status === 409 ? new Error("That SKU already exists. Use a different SKU.") : err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Add product" onClose={onClose}>
      <form onSubmit={submit} className="form">
        <label className="field">
          <span>Product name</span>
          <input className="input" value={form.name} onChange={set("name")} placeholder="e.g. Gardenia Bread 400g" required autoFocus />
        </label>
        <label className="field">
          <span>SKU (product code)</span>
          <input className="input" value={form.sku} onChange={set("sku")} placeholder="e.g. MY-BREAD-400G" required />
        </label>
        <div className="field-row">
          <label className="field">
            <span>Opening stock</span>
            <input className="input" type="number" min="0" step="1" value={form.system_quantity} onChange={set("system_quantity")} required />
          </label>
          <label className="field">
            <span>Unit price (RM)</span>
            <input className="input" type="number" min="0" step="0.01" value={form.unit_price} onChange={set("unit_price")} placeholder="0.00" required />
          </label>
          <label className="field">
            <span>Reorder at</span>
            <input className="input" type="number" min="0" step="1" value={form.low_stock_threshold} onChange={set("low_stock_threshold")} required />
          </label>
        </div>
        <ErrorBox error={error} />
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Add product"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ImportModal({ onClose }) {
  const { role, notify, refresh } = useApp();
  const [file, setFile] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const check = async () => {
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      setReport(await api.importFile(file, role.name, true));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const commit = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.importFile(file, role.name, false);
      notify(`Imported ${result.created_count} products.`);
      refresh();
      onClose();
    } catch (err) {
      if (err.data?.detail?.errors) setReport(err.data.detail);
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Import products from a spreadsheet" onClose={onClose} wide>
      <div className="form">
        <p className="muted">
          Upload a <strong>.csv</strong> or <strong>.xlsx</strong> file with these columns:{" "}
          <code>sku, name, system_quantity, unit_price, low_stock_threshold</code>. We check the file first and
          nothing is saved until you confirm.
        </p>
        <input
          className="input"
          type="file"
          accept=".csv,.xlsx"
          onChange={(e) => {
            setFile(e.target.files[0] || null);
            setReport(null);
            setError(null);
          }}
        />
        <ErrorBox error={error} />
        {report && (
          <div className={`callout ${report.valid ? "callout-good" : "callout-bad"}`}>
            <div>
              {report.valid ? (
                <strong>
                  File looks good: {report.total_rows} product{report.total_rows === 1 ? "" : "s"} ready to import.
                </strong>
              ) : (
                <>
                  <strong>Fix these rows and upload again:</strong>
                  <ul>
                    {report.errors.map((e, i) => (
                      <li key={i}>
                        Row {e.row}: {e.message}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>
        )}
        {report?.preview?.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Name</th>
                  <th className="num">Stock</th>
                  <th className="num">Price</th>
                  <th className="num">Reorder at</th>
                </tr>
              </thead>
              <tbody>
                {report.preview.map((p) => (
                  <tr key={p.sku}>
                    <td>{p.sku}</td>
                    <td>{p.name}</td>
                    <td className="num">{p.system_quantity}</td>
                    <td className="num">{rm(p.unit_price)}</td>
                    <td className="num">{p.low_stock_threshold}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="form-actions">
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          {report?.valid ? (
            <button className="btn btn-primary" onClick={commit} disabled={busy}>
              {busy ? "Importing…" : `Import ${report.total_rows} products`}
            </button>
          ) : (
            <button className="btn btn-primary" onClick={check} disabled={!file || busy}>
              {busy ? "Checking…" : "Check file"}
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
