
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Search,
  RefreshCw,
  Eye,
  X,
  AlertCircle,
  Clock,
  CheckCircle2,
  FileText,
  History,
} from "lucide-react";

import {
  getAllExceptions,
  getExceptionDetails,
  getExceptionHistory,
  investigateException,
} from "./api";

import "./Exceptions.css";

const PAGE_SIZE = 10;

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function formatAmount(value, currency = "INR") {
  if (value == null) return "—";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
  }).format(value / 100);
}

function Exceptions({ onBack }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);

  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [issueType, setIssueType] = useState("");
  const [search, setSearch] = useState("");

  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState(null);

  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  const [actor, setActor] = useState("analyst_01");
  const [notes, setNotes] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function loadExceptions() {
    try {
      setLoading(true);
      setError("");

      const result = await getAllExceptions({
        status,
        severity,
        issueType,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });

      setItems(result.items || []);
      setTotal(result.total || 0);
    } catch (err) {
      setError(err.message || "Could not load exceptions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadExceptions();
  }, [status, severity, issueType, page]);

  async function openException(exceptionId) {
    try {
      setDetailLoading(true);
      setError("");
      setMessage("");
      setNotes("");

      const [detail, audit] = await Promise.all([
        getExceptionDetails(exceptionId),
        getExceptionHistory(exceptionId),
      ]);

      setSelected(detail);
      setHistory(audit);
    } catch (err) {
      setError(err.message || "Could not load exception details.");
    } finally {
      setDetailLoading(false);
    }
  }

  async function startInvestigation(event) {
    event.preventDefault();

    if (!selected?.exception) return;

    try {
      setActionLoading(true);
      setMessage("");

      const result = await investigateException(
        selected.exception.exception_id,
        { actor, notes }
      );

      setMessage(result.message || "Investigation started successfully.");

      await loadExceptions();
      await openException(selected.exception.exception_id);
    } catch (err) {
      setMessage(err.message || "Investigation failed.");
    } finally {
      setActionLoading(false);
    }
  }

  const filteredItems = items.filter((item) =>
    [
      item.exception_id,
      item.merchant_name,
      item.issue_type,
      item.description,
    ]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(search.toLowerCase()))
  );

  const exception = selected?.exception;
  const evidence = selected?.evidence || [];

  return (
    <div className="exception-workspace">
      <div className="exception-header">
        <div>
          <button className="back-button" onClick={onBack}>
            <ArrowLeft size={16} /> Back to Dashboard
          </button>

          <div className="eyebrow">PAYMENT OPERATIONS</div>
          <h1>Exception Management</h1>
          <p>Review, investigate and manage payment discrepancies.</p>
        </div>

        <button className="refresh-exceptions" onClick={loadExceptions}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {error && <div className="exception-error">{error}</div>}

      <section className="exception-list-panel">
        <div className="exception-toolbar">
          <div>
            <h3>All Exceptions</h3>
            <p>{total} records found</p>
          </div>

          <div className="exception-search">
            <Search size={16} />
            <input
              placeholder="Search ID, merchant or issue..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        <div className="exception-filters">
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(0);
            }}
          >
            <option value="">All statuses</option>
            <option value="OPEN">Open</option>
            <option value="INVESTIGATING">Investigating</option>
            <option value="RESOLVED">Resolved</option>
            <option value="REJECTED">Rejected</option>
          </select>

          <select
            value={severity}
            onChange={(event) => {
              setSeverity(event.target.value);
              setPage(0);
            }}
          >
            <option value="">All severities</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={issueType}
            onChange={(event) => {
              setIssueType(event.target.value);
              setPage(0);
            }}
          >
            <option value="">All issue types</option>
            <option value="AMOUNT_MISMATCH">Amount mismatch</option>
            <option value="CURRENCY_MISMATCH">Currency mismatch</option>
            <option value="UNMATCHED_BANK">Unmatched bank</option>
            <option value="UNMATCHED_SETTLEMENT">Unmatched settlement</option>
            <option value="DELAYED_SETTLEMENT">Delayed settlement</option>
          </select>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>EXCEPTION ID</th>
                <th>MERCHANT</th>
                <th>ISSUE TYPE</th>
                <th>STATUS</th>
                <th>SEVERITY</th>
                <th>DETECTED</th>
                <th>ACTION</th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" className="exception-empty">
                    Loading exceptions...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan="7" className="exception-empty">
                    No exceptions found.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr key={item.exception_id}>
                    <td className="exception-id">
                      {item.exception_id}
                    </td>
                    <td>{item.merchant_name}</td>
                    <td>{item.issue_type.replaceAll("_", " ")}</td>
                    <td>
                      <span className={`status-pill ${item.status.toLowerCase()}`}>
                        {item.status}
                      </span>
                    </td>
                    <td>
                      <span className={`severity-pill ${item.severity.toLowerCase()}`}>
                        {item.severity}
                      </span>
                    </td>
                    <td>{formatDate(item.detected_at)}</td>
                    <td>
                      <button
                        className="inspect-button"
                        onClick={() => openException(item.exception_id)}
                      >
                        <Eye size={14} /> Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="exception-pagination">
          <span>
            Showing {total === 0 ? 0 : page * PAGE_SIZE + 1}–
            {Math.min((page + 1) * PAGE_SIZE, total)} of {total}
          </span>

          <div>
            <button
              disabled={page === 0}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </button>
            <button
              disabled={(page + 1) * PAGE_SIZE >= total}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {selected && (
        <div className="exception-modal-backdrop">
          <section className="exception-detail-modal">
            <div className="detail-header">
              <div>
                <span className="eyebrow">EXCEPTION DETAILS</span>
                <h2>{exception?.exception_id}</h2>
              </div>
              <button
                className="detail-close"
                onClick={() => {
                  setSelected(null);
                  setHistory(null);
                  setMessage("");
                }}
              >
                <X size={20} />
              </button>
            </div>

            {detailLoading ? (
              <p>Loading details...</p>
            ) : (
              <>
                <div className="detail-summary">
                  <span className={`status-pill ${exception?.status?.toLowerCase()}`}>
                    {exception?.status}
                  </span>
                  <span className={`severity-pill ${exception?.severity?.toLowerCase()}`}>
                    {exception?.severity} SEVERITY
                  </span>
                  <h3>{exception?.issue_type?.replaceAll("_", " ")}</h3>
                  <p>{exception?.description}</p>
                </div>

                <div className="detail-grid">
                  <div>
                    <span>Merchant</span>
                    <strong>{exception?.merchant_name}</strong>
                  </div>
                  <div>
                    <span>Merchant ID</span>
                    <strong>{exception?.merchant_id}</strong>
                  </div>
                  <div>
                    <span>Settlement batch</span>
                    <strong>{exception?.batch_id || "—"}</strong>
                  </div>
                  <div>
                    <span>Bank line</span>
                    <strong>{exception?.bank_line_id || "—"}</strong>
                  </div>
                  <div>
                    <span>Detected at</span>
                    <strong>{formatDate(exception?.detected_at)}</strong>
                  </div>
                  <div>
                    <span>Resolved at</span>
                    <strong>{formatDate(exception?.resolved_at)}</strong>
                  </div>
                </div>

                <div className="detail-section">
                  <h3><FileText size={17} /> Evidence</h3>

                  {evidence.length === 0 ? (
                    <p>No evidence records available.</p>
                  ) : (
                    evidence.map((item) => (
                      <div className="evidence-card" key={item.exception_item_id}>
                        <strong>{item.source_type}</strong>
                        <div className="detail-grid">
                          <div>
                            <span>Settlement currency</span>
                            <strong>{item.settlement_currency || "—"}</strong>
                          </div>
                          <div>
                            <span>Bank currency</span>
                            <strong>{item.bank_currency || "—"}</strong>
                          </div>
                          <div>
                            <span>Settlement amount</span>
                            <strong>
                              {formatAmount(item.signed_amount_minor, item.settlement_currency)}
                            </strong>
                          </div>
                          <div>
                            <span>Settlement fee</span>
                            <strong>
                              {formatAmount(item.fee_amount_minor, item.settlement_currency)}
                            </strong>
                          </div>
                          <div>
                            <span>Net settlement</span>
                            <strong>
                              {formatAmount(item.net_amount_minor, item.settlement_currency)}
                            </strong>
                          </div>
                          <div>
                            <span>Bank amount</span>
                            <strong>
                              {formatAmount(item.bank_amount_minor, item.bank_currency)}
                            </strong>
                          </div>
                          <div>
                            <span>Bank reference</span>
                            <strong>{item.bank_reference || "—"}</strong>
                          </div>
                          <div>
                            <span>Transaction date</span>
                            <strong>{item.transaction_date || "—"}</strong>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {["OPEN", "INVESTIGATING"].includes(exception?.status) && (
                  <form className="investigation-form" onSubmit={startInvestigation}>
                    <h3><AlertCircle size={17} /> Investigation</h3>

                    <label>Analyst</label>
                    <input
                      value={actor}
                      onChange={(event) => setActor(event.target.value)}
                      required
                    />

                    <label>Investigation notes</label>
                    <textarea
                      value={notes}
                      onChange={(event) => setNotes(event.target.value)}
                      placeholder="Describe the investigation..."
                      required
                      rows={3}
                    />

                    <button
                      type="submit"
                      disabled={actionLoading || exception?.status !== "OPEN"}
                    >
                      <Clock size={16} />
                      {actionLoading
                        ? "Submitting..."
                        : exception?.status === "OPEN"
                          ? "Start Investigation"
                          : "Investigation Started"}
                    </button>

                    {message && <p className="action-message">{message}</p>}
                  </form>
                )}

                <div className="detail-section">
                  <h3><History size={17} /> Audit History</h3>

                  {!history ? (
                    <p>Loading audit history...</p>
                  ) : (
                    <>
                      {[
                        ...(history.audit_events || []),
                        ...(history.resolutions || []),
                      ].length === 0 ? (
                        <p>No audit events recorded yet.</p>
                      ) : (
                        <div className="history-list">
                          {[
                            ...(history.audit_events || []),
                            ...(history.resolutions || []),
                          ].map((event, index) => (
                            <div className="history-item" key={event.id || index}>
                              <CheckCircle2 size={17} />
                              <div>
                                <strong>
                                  {event.action || event.resolution_type || "Activity"}
                                </strong>
                                <span>
                                  {event.actor || "System"} ·{" "}
                                  {formatDate(event.created_at)}
                                </span>
                                {event.notes && <p>{event.notes}</p>}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export default Exceptions;
