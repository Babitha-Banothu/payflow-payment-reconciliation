
import { useCallback, useEffect, useState } from "react";
import {
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  X,
  CreditCard,
  CheckCircle2,
  XCircle,
  Clock,
  Activity,
  ArrowUpRight,
  Receipt,
} from "lucide-react";

import {
  getAllTransactions,
  getTransactionDetails,
} from "./api";

import "./Transactions.css";

const PAGE_SIZE = 20;

function formatAmount(amountMinor, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format((amountMinor || 0) / 100);
}

function formatDate(value) {
  if (!value) return "—";

  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function statusClass(status) {
  return (status || "unknown").toLowerCase().replaceAll("_", "-");
}

function Transactions() {
  const [data, setData] = useState([]);
  const [statistics, setStatistics] = useState({
    total: 0,
    successful: 0,
    failed: 0,
    pending: 0,
  });

  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [currency, setCurrency] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  const loadTransactions = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const result = await getAllTransactions({
        search,
        status,
        currency,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });

      setData(result.items || []);
      setTotal(result.total || 0);
      setStatistics(
        result.statistics || {
          total: 0,
          successful: 0,
          failed: 0,
          pending: 0,
        }
      );
    } catch (err) {
      console.error("Failed to load transactions:", err);
      setError(err.message || "Unable to load transactions.");
    } finally {
      setLoading(false);
    }
  }, [search, status, currency, page]);

  useEffect(() => {
    loadTransactions();
  }, [loadTransactions]);

  async function openTransaction(paymentId) {
    try {
      setSelectedTransaction(null);
      setDetailLoading(true);
      setDetailError("");

      const result = await getTransactionDetails(paymentId);
      setSelectedTransaction(result);
    } catch (err) {
      console.error("Failed to load transaction details:", err);
      setDetailError(err.message || "Unable to load transaction details.");
    } finally {
      setDetailLoading(false);
    }
  }

  function updateFilter(setter, value) {
    setter(value);
    setPage(0);
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const payment = selectedTransaction?.payment;
  const attempts = selectedTransaction?.attempts || [];
  const events = selectedTransaction?.processor_events || [];
  const refunds = selectedTransaction?.refunds || [];

  return (
    <div className="page-content transactions-page">
      <section className="page-heading">
        <div>
          <div className="eyebrow">PAYMENT OPERATIONS</div>
          <h1>Transactions</h1>
          <p>View and monitor payment transactions from your database.</p>
        </div>

        <button
          className="date-button"
          onClick={loadTransactions}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh data
        </button>
      </section>

      {error && <div className="error-message">{error}</div>}

      <section className="transaction-metrics">
        <article className="transaction-metric">
          <div className="transaction-metric-icon total">
            <CreditCard size={20} />
          </div>
          <span>Total transactions</span>
          <strong>
            {loading ? "..." : statistics.total.toLocaleString("en-IN")}
          </strong>
          <small>All payment orders</small>
        </article>

        <article className="transaction-metric">
          <div className="transaction-metric-icon success">
            <CheckCircle2 size={20} />
          </div>
          <span>Successful</span>
          <strong>
            {loading ? "..." : statistics.successful.toLocaleString("en-IN")}
          </strong>
          <small>Successfully paid</small>
        </article>

        <article className="transaction-metric">
          <div className="transaction-metric-icon failed">
            <XCircle size={20} />
          </div>
          <span>Failed</span>
          <strong>
            {loading ? "..." : statistics.failed.toLocaleString("en-IN")}
          </strong>
          <small>Failed payments</small>
        </article>

        <article className="transaction-metric">
          <div className="transaction-metric-icon pending">
            <Clock size={20} />
          </div>
          <span>Pending</span>
          <strong>
            {loading ? "..." : statistics.pending.toLocaleString("en-IN")}
          </strong>
          <small>Awaiting completion</small>
        </article>
      </section>

      <section className="panel transactions-panel">
        <div className="transactions-toolbar">
          <div>
            <h3>All transactions</h3>
            <p>Payment orders and their current status</p>
          </div>

          <div className="transaction-filters">
            <div className="transaction-search">
              <Search size={17} />
              <input
                type="search"
                placeholder="Search payment or merchant..."
                value={search}
                onChange={(event) =>
                  updateFilter(setSearch, event.target.value)
                }
              />
            </div>

            <select
              value={status}
              onChange={(event) =>
                updateFilter(setStatus, event.target.value)
              }
              aria-label="Filter by payment status"
            >
              <option value="">All statuses</option>
              <option value="PAID">Paid</option>
              <option value="FAILED">Failed</option>
            </select>

            <select
              value={currency}
              onChange={(event) =>
                updateFilter(setCurrency, event.target.value)
              }
              aria-label="Filter by currency"
            >
              <option value="">All currencies</option>
              <option value="INR">INR</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
        </div>

        <div className="transaction-table-scroll">
          <table className="transaction-table">
            <thead>
              <tr>
                <th>PAYMENT ID</th>
                <th>MERCHANT</th>
                <th>AMOUNT</th>
                <th>STATUS</th>
                <th>ATTEMPTS</th>
                <th>CREATED AT</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" className="transaction-empty">
                    Loading transactions...
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan="7" className="transaction-empty">
                    No transactions found.
                  </td>
                </tr>
              ) : (
                data.map((item) => (
                  <tr key={item.payment_id}>
                    <td className="transaction-id">
                      {item.payment_id}
                    </td>
                    <td>
                      <strong>{item.merchant_name || "—"}</strong>
                      <small>{item.merchant_id}</small>
                    </td>
                    <td className="transaction-amount">
                      {formatAmount(item.amount_minor, item.currency)}
                    </td>
                    <td>
                      <span
                        className={`transaction-status ${statusClass(item.status)}`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td>{item.attempt_count}</td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>
                      <button
                        className="transaction-view-button"
                        onClick={() => openTransaction(item.payment_id)}
                        aria-label={`View ${item.payment_id}`}
                      >
                        <ArrowUpRight size={17} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="transaction-pagination">
          <span>
            Showing {total === 0 ? 0 : page * PAGE_SIZE + 1}–
            {Math.min((page + 1) * PAGE_SIZE, total)} of {total} transactions
          </span>

          <div>
            <button
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              disabled={page === 0 || loading}
              aria-label="Previous page"
            >
              <ChevronLeft size={18} />
            </button>

            <span>
              Page {page + 1} of {totalPages}
            </span>

            <button
              onClick={() =>
                setPage((current) => Math.min(totalPages - 1, current + 1))
              }
              disabled={page >= totalPages - 1 || loading}
              aria-label="Next page"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </section>

      {(selectedTransaction || detailLoading || detailError) && (
        <div
          className="transaction-modal-backdrop"
          onClick={() => {
            setSelectedTransaction(null);
            setDetailError("");
          }}
        >
          <section
            className="transaction-detail-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="transaction-detail-heading">
              <div>
                <span className="eyebrow">PAYMENT DETAILS</span>
                <h2>Transaction overview</h2>
              </div>

              <button
                onClick={() => {
                  setSelectedTransaction(null);
                  setDetailError("");
                }}
                aria-label="Close transaction details"
              >
                <X size={21} />
              </button>
            </div>

            {detailLoading ? (
              <div className="transaction-detail-message">
                Loading transaction details...
              </div>
            ) : detailError ? (
              <div className="error-message">{detailError}</div>
            ) : payment ? (
              <>
                <div className="transaction-detail-summary">
                  <span>Payment amount</span>
                  <strong>
                    {formatAmount(payment.amount_minor, payment.currency)}
                  </strong>
                  <span
                    className={`transaction-status ${statusClass(payment.status)}`}
                  >
                    {payment.status}
                  </span>
                </div>

                <div className="transaction-detail-section">
                  <h3>Payment information</h3>
                  <div className="transaction-detail-grid">
                    <div>
                      <small>Payment ID</small>
                      <strong>{payment.payment_id}</strong>
                    </div>
                    <div>
                      <small>Customer reference</small>
                      <strong>{payment.customer_reference || "—"}</strong>
                    </div>
                    <div>
                      <small>Merchant</small>
                      <strong>{payment.merchant_name}</strong>
                    </div>
                    <div>
                      <small>Merchant email</small>
                      <strong>{payment.merchant_email || "—"}</strong>
                    </div>
                    <div>
                      <small>Country</small>
                      <strong>{payment.merchant_country || "—"}</strong>
                    </div>
                    <div>
                      <small>Created at</small>
                      <strong>{formatDate(payment.created_at)}</strong>
                    </div>
                  </div>
                </div>

                <div className="transaction-detail-section">
                  <h3>
                    <Activity size={17} /> Payment attempts ({attempts.length})
                  </h3>

                  {attempts.length === 0 ? (
                    <p className="transaction-muted">No attempts recorded.</p>
                  ) : (
                    attempts.map((attempt) => (
                      <div className="transaction-evidence-card" key={attempt.attempt_id}>
                        <div className="transaction-evidence-top">
                          <strong>Attempt #{attempt.attempt_number}</strong>
                          <span className={`transaction-status ${statusClass(attempt.status)}`}>
                            {attempt.status}
                          </span>
                        </div>
                        <p>Processor: {attempt.processor_name}</p>
                        <p>Reference: {attempt.processor_reference || "—"}</p>
                        <p>Attempted: {formatDate(attempt.attempted_at)}</p>
                        <p>Captured: {formatDate(attempt.captured_at)}</p>
                      </div>
                    ))
                  )}
                </div>

                <div className="transaction-detail-section">
                  <h3>
                    <Activity size={17} /> Processor event timeline ({events.length})
                  </h3>

                  {events.length === 0 ? (
                    <p className="transaction-muted">No processor events recorded.</p>
                  ) : (
                    <div className="transaction-event-list">
                      {events.map((event, index) => (
                        <div
                          className="transaction-event"
                          key={`${event.event_id}-${event.delivery_id || index}`}
                        >
                          <div className="transaction-event-marker" />
                          <div>
                            <strong>{event.event_type}</strong>
                            <span className="transaction-event-status">
                              {event.event_status}
                            </span>
                            <p>{event.processor_name}</p>
                            <p>Event time: {formatDate(event.event_timestamp)}</p>
                            <p>Received: {formatDate(event.delivery_received_at || event.received_at)}</p>
                            <p>
                              Delivery: {event.delivery_id || "—"}
                              {event.is_duplicate ? " · Duplicate" : ""}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="transaction-detail-section">
                  <h3>
                    <Receipt size={17} /> Refunds ({refunds.length})
                  </h3>

                  {refunds.length === 0 ? (
                    <p className="transaction-muted">No refunds recorded.</p>
                  ) : (
                    refunds.map((refund) => (
                      <div className="transaction-evidence-card" key={refund.refund_id}>
                        <strong>{refund.refund_id}</strong>
                        <p>
                          Amount: {formatAmount(refund.amount_minor, refund.currency)}
                        </p>
                        <p>Status: {refund.status}</p>
                        <p>Date: {formatDate(refund.refund_timestamp)}</p>
                      </div>
                    ))
                  )}
                </div>
              </>
            ) : null}
          </section>
        </div>
      )}
    </div>
  );
}

export default Transactions;
