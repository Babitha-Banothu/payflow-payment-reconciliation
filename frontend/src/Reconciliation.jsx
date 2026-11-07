
import { useEffect, useState } from "react";
import {
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  X,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Clock3,
  GitCompareArrows,
  Building2,
  Landmark,
  Layers3,
  Eye,
} from "lucide-react";

import {
  getAllReconciliation,
  getReconciliationDetails,
} from "./api";

import "./Reconciliation.css";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = [
  "MATCHED",
  "PARTIAL",
  "UNMATCHED",
  "REJECTED",
];

function formatMoney(amountMinor, currency = "INR") {
  const amount = Number(amountMinor ?? 0) / 100;

  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currency || "INR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

function formatDate(value) {
  if (!value) return "—";

  return new Date(value).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDateOnly(value) {
  if (!value) return "—";

  return new Date(`${value}T00:00:00`).toLocaleDateString(
    "en-IN",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }
  );
}

function StatusBadge({ status }) {
  const config = {
    MATCHED: {
      icon: CheckCircle2,
      label: "Matched",
    },
    PARTIAL: {
      icon: AlertCircle,
      label: "Partial",
    },
    UNMATCHED: {
      icon: Clock3,
      label: "Unmatched",
    },
    REJECTED: {
      icon: XCircle,
      label: "Rejected",
    },
  };

  const item = config[status] || {
    icon: AlertCircle,
    label: status || "Unknown",
  };

  const Icon = item.icon;

  return (
    <span className={`recon-status recon-status-${status?.toLowerCase()}`}>
      <Icon size={14} />
      {item.label}
    </span>
  );
}

function SummaryCard({ label, value, helper, icon: Icon }) {
  return (
    <div className="recon-summary-card">
      <div className="recon-summary-top">
        <span>{label}</span>
        <span className="recon-summary-icon">
          <Icon size={19} />
        </span>
      </div>

      <div className="recon-summary-value">{value}</div>

      {helper && (
        <div className="recon-summary-helper">{helper}</div>
      )}
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="recon-detail-row">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

function ReconciliationDetails({ matchId, onClose }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDetails() {
      try {
        setLoading(true);
        setError("");

        const result = await getReconciliationDetails(matchId);

        if (active) {
          setDetails(result);
        }
      } catch (err) {
        if (active) {
          setError(err.message || "Unable to load match details.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadDetails();

    return () => {
      active = false;
    };
  }, [matchId]);

  if (!matchId) return null;

  const match = details?.match;
  const batch = details?.batch;
  const bank = details?.bank_line;
  const settlementLines = details?.settlement_lines || [];

  return (
    <div
      className="recon-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="recon-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="recon-detail-title"
      >
        <div className="recon-modal-header">
          <div>
            <span className="recon-eyebrow">MATCH DETAILS</span>
            <h2 id="recon-detail-title">{matchId}</h2>
          </div>

          <button
            className="recon-icon-button"
            onClick={onClose}
            aria-label="Close details"
          >
            <X size={20} />
          </button>
        </div>

        {loading && (
          <div className="recon-modal-state">
            <RefreshCw className="recon-spin" size={24} />
            <p>Loading reconciliation evidence...</p>
          </div>
        )}

        {error && (
          <div className="recon-error recon-modal-error">
            {error}
          </div>
        )}

        {match && !loading && (
          <div className="recon-detail-content">
            <div className="recon-detail-overview">
              <div>
                <span className="recon-detail-label">Match status</span>
                <StatusBadge status={match.status} />
              </div>

              <div>
                <span className="recon-detail-label">Confidence score</span>
                <strong className="recon-confidence-large">
                  {(Number(match.confidence_score || 0) * 100).toFixed(1)}%
                </strong>
              </div>

              <div>
                <span className="recon-detail-label">Merchant</span>
                <strong>{match.merchant_name}</strong>
              </div>
            </div>

            <section className="recon-detail-section">
              <h3>
                <GitCompareArrows size={17} />
                Amount comparison
              </h3>

              <div className="recon-amount-comparison">
                <div>
                  <span>Expected amount</span>
                  <strong>
                    {formatMoney(
                      match.expected_amount_minor,
                      match.currency
                    )}
                  </strong>
                </div>

                <div className="recon-amount-arrow">
                  <GitCompareArrows size={20} />
                </div>

                <div>
                  <span>Actual amount</span>
                  <strong>
                    {formatMoney(
                      match.actual_amount_minor,
                      match.currency
                    )}
                  </strong>
                </div>
              </div>

              <DetailRow
                label="Variance"
                value={formatMoney(match.variance_minor, match.currency)}
              />

              <DetailRow
                label="Matching method"
                value={match.matching_method}
              />

              <DetailRow
                label="Matched at"
                value={formatDate(match.matched_at)}
              />
            </section>

            <section className="recon-detail-section">
              <h3>
                <Layers3 size={17} />
                Settlement batch
              </h3>

              {batch ? (
                <>
                  <DetailRow label="Batch ID" value={batch.batch_id} />
                  <DetailRow
                    label="Processor"
                    value={batch.processor_name}
                  />
                  <DetailRow
                    label="Settlement date"
                    value={formatDateOnly(batch.settlement_date)}
                  />
                  <DetailRow label="Batch status" value={batch.status} />
                  <DetailRow
                    label="Gross amount"
                    value={formatMoney(
                      batch.gross_amount_minor,
                      batch.currency
                    )}
                  />
                  <DetailRow
                    label="Refund amount"
                    value={formatMoney(
                      batch.refund_amount_minor,
                      batch.currency
                    )}
                  />
                  <DetailRow
                    label="Fee amount"
                    value={formatMoney(
                      batch.fee_amount_minor,
                      batch.currency
                    )}
                  />
                  <DetailRow
                    label="Net settlement"
                    value={formatMoney(
                      batch.net_amount_minor,
                      batch.currency
                    )}
                  />
                </>
              ) : (
                <p className="recon-empty-inline">
                  No settlement batch is linked to this match.
                </p>
              )}
            </section>

            <section className="recon-detail-section">
              <h3>
                <Landmark size={17} />
                Bank statement
              </h3>

              {bank ? (
                <>
                  <DetailRow
                    label="Bank line ID"
                    value={bank.bank_line_id}
                  />
                  <DetailRow
                    label="Bank reference"
                    value={bank.bank_reference}
                  />
                  <DetailRow label="Bank" value={bank.bank_name} />
                  <DetailRow
                    label="Transaction type"
                    value={bank.transaction_type}
                  />
                  <DetailRow
                    label="Transaction date"
                    value={formatDateOnly(bank.transaction_date)}
                  />
                  <DetailRow
                    label="Value date"
                    value={formatDateOnly(bank.value_date)}
                  />
                  <DetailRow
                    label="Bank amount"
                    value={formatMoney(bank.amount_minor, bank.currency)}
                  />
                  <DetailRow
                    label="Description"
                    value={bank.description}
                  />
                </>
              ) : (
                <p className="recon-empty-inline">
                  No bank statement line is linked to this match.
                </p>
              )}
            </section>

            <section className="recon-detail-section">
              <h3>
                <Layers3 size={17} />
                Settlement line items ({settlementLines.length})
              </h3>

              {settlementLines.length > 0 ? (
                <div className="recon-line-list">
                  {settlementLines.map((line) => (
                    <div
                      className="recon-line-card"
                      key={line.match_item_id}
                    >
                      <div className="recon-line-card-top">
                        <strong>{line.settlement_line_id}</strong>
                        <span>{line.line_type}</span>
                      </div>

                      <DetailRow
                        label="Attempt ID"
                        value={line.attempt_id}
                      />
                      <DetailRow
                        label="Signed amount"
                        value={formatMoney(
                          line.signed_amount_minor,
                          line.currency
                        )}
                      />
                      <DetailRow
                        label="Fee"
                        value={formatMoney(
                          line.fee_amount_minor,
                          line.currency
                        )}
                      />
                      <DetailRow
                        label="Net amount"
                        value={formatMoney(
                          line.net_amount_minor,
                          line.currency
                        )}
                      />
                      <DetailRow
                        label="Allocated amount"
                        value={formatMoney(
                          line.allocated_amount_minor,
                          line.currency
                        )}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="recon-empty-inline">
                  No settlement line items were found.
                </p>
              )}
            </section>
          </div>
        )}
      </section>
    </div>
  );
}

export default function Reconciliation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [method, setMethod] = useState("");

  const [offset, setOffset] = useState(0);
  const [selectedMatchId, setSelectedMatchId] = useState(null);

  async function loadReconciliation(isRefresh = false) {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const result = await getAllReconciliation({
        search,
        status,
        method,
        limit: PAGE_SIZE,
        offset,
      });

      setData(result);
    } catch (err) {
      setError(err.message || "Unable to load reconciliation records.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadReconciliation();
  }, [search, status, method, offset]);

  useEffect(() => {
    setOffset(0);
  }, [search, status, method]);

  const statistics = data?.statistics || {};
  const items = data?.items || [];
  const total = data?.total || 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const statusSummary = data?.status_summary || [];
  const methodSummary = data?.method_summary || [];

  const matchedPercent = statistics.total
    ? (statistics.matched / statistics.total) * 100
    : 0;

  return (
    <main className="recon-page">
      <div className="recon-page-header">
        <div>
          <span className="recon-eyebrow">PAYMENT OPERATIONS</span>
          <h1>Reconciliation</h1>
          <p>
            Compare processor settlements with bank statement records
            and investigate discrepancies.
          </p>
        </div>

        <button
          className="recon-refresh-button"
          onClick={() => loadReconciliation(true)}
          disabled={refreshing || loading}
        >
          <RefreshCw
            size={16}
            className={refreshing ? "recon-spin" : ""}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div className="recon-error">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button onClick={() => loadReconciliation(true)}>
            Retry
          </button>
        </div>
      )}

      <section className="recon-summary-grid">
        <SummaryCard
          label="Total matches"
          value={statistics.total?.toLocaleString("en-IN") ?? "—"}
          helper="All reconciliation records"
          icon={GitCompareArrows}
        />

        <SummaryCard
          label="Matched"
          value={statistics.matched?.toLocaleString("en-IN") ?? "—"}
          helper={`${matchedPercent.toFixed(1)}% of all matches`}
          icon={CheckCircle2}
        />

        <SummaryCard
          label="Unmatched"
          value={statistics.unmatched?.toLocaleString("en-IN") ?? "—"}
          helper="No matching bank record"
          icon={Clock3}
        />

        <SummaryCard
          label="Partial / Rejected"
          value={
            (
              Number(statistics.partial || 0) +
              Number(statistics.rejected || 0)
            ).toLocaleString("en-IN")
          }
          helper={`${statistics.partial || 0} partial · ${statistics.rejected || 0} rejected`}
          icon={AlertCircle}
        />
      </section>

      <section className="recon-analytics-grid">
        <div className="recon-panel recon-status-panel">
          <div className="recon-panel-heading">
            <div>
              <h2>Match status overview</h2>
              <p>Distribution across all reconciliation records</p>
            </div>
          </div>

          <div className="recon-status-bars">
            {STATUS_OPTIONS.map((item) => {
              const count =
                statusSummary.find((entry) => entry.status === item)?.count || 0;

              const percentage = statistics.total
                ? (count / statistics.total) * 100
                : 0;

              return (
                <div className="recon-status-bar-row" key={item}>
                  <div className="recon-status-bar-label">
                    <StatusBadge status={item} />
                    <strong>{count.toLocaleString("en-IN")}</strong>
                  </div>

                  <div className="recon-progress-track">
                    <div
                      className={`recon-progress-fill recon-progress-${item.toLowerCase()}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="recon-progress-percent">
                    {percentage.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="recon-panel recon-method-panel">
          <div className="recon-panel-heading">
            <div>
              <h2>Matching methods</h2>
              <p>How reconciliation records were linked</p>
            </div>
          </div>

          <div className="recon-method-list">
            {methodSummary.map((item) => {
              const percentage = statistics.total
                ? (item.count / statistics.total) * 100
                : 0;

              return (
                <div className="recon-method-item" key={item.matching_method}>
                  <div className="recon-method-icon">
                    <GitCompareArrows size={18} />
                  </div>

                  <div className="recon-method-info">
                    <strong>{item.matching_method}</strong>
                    <span>{percentage.toFixed(1)}% of records</span>
                  </div>

                  <strong className="recon-method-count">
                    {item.count.toLocaleString("en-IN")}
                  </strong>
                </div>
              );
            })}

            {methodSummary.length === 0 && (
              <p className="recon-empty-inline">No method data available.</p>
            )}
          </div>

          <div className="recon-average-confidence">
            <span>Average confidence</span>
            <strong>
              {statistics.average_confidence != null
                ? `${(
                    Number(statistics.average_confidence) * 100
                  ).toFixed(1)}%`
                : "—"}
            </strong>
          </div>
        </div>
      </section>

      <section className="recon-panel recon-records-panel">
        <div className="recon-records-heading">
          <div>
            <h2>Reconciliation records</h2>
            <p>
              Review matched, partial, unmatched and rejected settlements.
            </p>
          </div>

          <span className="recon-record-count">
            {total.toLocaleString("en-IN")} records
          </span>
        </div>

        <div className="recon-filters">
          <div className="recon-search-box">
            <Search size={18} />
            <input
              type="search"
              placeholder="Search match, batch, bank reference or merchant..."
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setOffset(0);
              }}
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                aria-label="Clear search"
              >
                <X size={16} />
              </button>
            )}
          </div>

          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setOffset(0);
            }}
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((item) => (
              <option value={item} key={item}>
                {item}
              </option>
            ))}
          </select>

          <select
            value={method}
            onChange={(event) => {
              setMethod(event.target.value);
              setOffset(0);
            }}
            aria-label="Filter by matching method"
          >
            <option value="">All methods</option>
            {methodSummary.map((item) => (
              <option
                value={item.matching_method}
                key={item.matching_method}
              >
                {item.matching_method}
              </option>
            ))}
          </select>
        </div>

        <div className="recon-table-wrap">
          <table className="recon-table">
            <thead>
              <tr>
                <th>Match ID</th>
                <th>Merchant</th>
                <th>Settlement batch</th>
                <th>Expected</th>
                <th>Actual</th>
                <th>Variance</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="9" className="recon-table-state">
                    <RefreshCw className="recon-spin" size={22} />
                    <span>Loading reconciliation records...</span>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan="9" className="recon-table-state">
                    <Search size={22} />
                    <span>No reconciliation records found.</span>
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.match_id}>
                    <td>
                      <strong className="recon-match-id">
                        {item.match_id}
                      </strong>
                      <span className="recon-cell-subtext">
                        {formatDate(item.matched_at)}
                      </span>
                    </td>

                    <td>
                      <div className="recon-merchant-cell">
                        <span className="recon-merchant-icon">
                          <Building2 size={15} />
                        </span>
                        <span>{item.merchant_name}</span>
                      </div>
                    </td>

                    <td>
                      <strong>{item.batch_id || "—"}</strong>
                      <span className="recon-cell-subtext">
                        {item.processor_name || "No processor"}
                      </span>
                    </td>

                    <td className="recon-money">
                      {formatMoney(
                        item.expected_amount_minor,
                        item.currency
                      )}
                    </td>

                    <td className="recon-money">
                      {formatMoney(
                        item.actual_amount_minor,
                        item.currency
                      )}
                    </td>

                    <td>
                      <span
                        className={
                          Number(item.variance_minor) === 0
                            ? "recon-variance-zero"
                            : "recon-variance-nonzero"
                        }
                      >
                        {formatMoney(
                          item.variance_minor,
                          item.currency
                        )}
                      </span>
                    </td>

                    <td>
                      <StatusBadge status={item.status} />
                    </td>

                    <td>
                      <div className="recon-confidence-cell">
                        <div className="recon-confidence-track">
                          <div
                            style={{
                              width: `${
                                Number(item.confidence_score || 0) * 100
                              }%`,
                            }}
                          />
                        </div>
                        <span>
                          {(
                            Number(item.confidence_score || 0) * 100
                          ).toFixed(0)}%
                        </span>
                      </div>
                    </td>

                    <td>
                      <button
                        className="recon-view-button"
                        onClick={() => setSelectedMatchId(item.match_id)}
                        aria-label={`View ${item.match_id}`}
                      >
                        <Eye size={16} />
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="recon-pagination">
          <span>
            Showing {total === 0 ? 0 : offset + 1}–
            {Math.min(offset + PAGE_SIZE, total)} of{" "}
            {total.toLocaleString("en-IN")}
          </span>

          <div className="recon-pagination-actions">
            <button
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0 || loading}
              aria-label="Previous page"
            >
              <ChevronLeft size={18} />
              Previous
            </button>

            <span>
              Page {currentPage} of {totalPages}
            </span>

            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total || loading}
              aria-label="Next page"
            >
              Next
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </section>

      {selectedMatchId && (
        <ReconciliationDetails
          matchId={selectedMatchId}
          onClose={() => setSelectedMatchId(null)}
        />
      )}
    </main>
  );
}
