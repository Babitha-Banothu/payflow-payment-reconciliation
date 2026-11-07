
import { useEffect, useMemo, useState } from "react";
import {
  Search,
  RefreshCw,
  History,
  Activity,
  UserRound,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  X,
  Eye,
  FileClock,
  ArrowRight,
  AlertCircle,
} from "lucide-react";

import { getAuditHistory } from "./api";
import "./Audit.css";

const PAGE_SIZE = 10;

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

function formatAction(value = "") {
  return value.replaceAll("_", " ");
}

function formatJson(value) {
  if (value === null || value === undefined) {
    return "No state recorded";
  }

  return JSON.stringify(value, null, 2);
}

function Audit() {
  const [auditData, setAuditData] = useState({
    total: 0,
    items: [],
    entity_summary: [],
    action_summary: [],
  });

  const [search, setSearch] = useState("");
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [selectedEvent, setSelectedEvent] = useState(null);

  async function loadAudit(showRefresh = false) {
    try {
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const result = await getAuditHistory({
        search,
        entityType,
        action,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });

      setAuditData({
        total: result.total || 0,
        items: result.items || [],
        entity_summary: result.entity_summary || [],
        action_summary: result.action_summary || [],
      });
    } catch (err) {
      console.error("Failed to load audit history:", err);
      setError(
        err.message || "Unable to load audit history."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      loadAudit();
    }, 300);

    return () => clearTimeout(timer);
  }, [search, entityType, action, page]);

  const totalPages = Math.max(
    1,
    Math.ceil(auditData.total / PAGE_SIZE)
  );

  const entityCount = useMemo(
    () =>
      auditData.entity_summary.reduce(
        (sum, item) => sum + Number(item.count || 0),
        0
      ),
    [auditData.entity_summary]
  );

  const actionCount = useMemo(
    () => auditData.action_summary.length,
    [auditData.action_summary]
  );

  function changeSearch(value) {
    setSearch(value);
    setPage(0);
  }

  function changeEntity(value) {
    setEntityType(value);
    setPage(0);
  }

  function changeAction(value) {
    setAction(value);
    setPage(0);
  }

  function clearFilters() {
    setSearch("");
    setEntityType("");
    setAction("");
    setPage(0);
  }

  const hasFilters = search || entityType || action;

  return (
    <div className="page-content audit-page">

      {/* PAGE HEADING */}
      <section className="page-heading audit-heading">
        <div>
          <div className="eyebrow">PAYMENT OPERATIONS</div>
          <h1>Audit History</h1>
          <p>
            Monitor system activity, investigation events
            and analyst actions.
          </p>
        </div>

        <button
          className="audit-refresh-button"
          onClick={() => loadAudit(true)}
          disabled={refreshing}
        >
          <RefreshCw
            size={16}
            className={refreshing ? "audit-spinning" : ""}
          />
          Refresh data
        </button>
      </section>

      {/* ERROR MESSAGE */}
      {error && (
        <div className="audit-error">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button onClick={() => loadAudit(true)}>
            Retry
          </button>
        </div>
      )}

      {/* STATISTICS */}
      <section className="audit-stats-grid">

        <article className="audit-stat-card">
          <div className="audit-stat-top">
            <span>Total Audit Events</span>
            <div className="audit-stat-icon orange">
              <History size={20} />
            </div>
          </div>

          <strong>
            {loading ? "..." : auditData.total.toLocaleString("en-IN")}
          </strong>
          <small>Matching database records</small>
        </article>

        <article className="audit-stat-card">
          <div className="audit-stat-top">
            <span>Entity Types</span>
            <div className="audit-stat-icon green">
              <Activity size={20} />
            </div>
          </div>

          <strong>
            {loading ? "..." : entityCount}
          </strong>
          <small>Recorded entity events</small>
        </article>

        <article className="audit-stat-card">
          <div className="audit-stat-top">
            <span>Action Types</span>
            <div className="audit-stat-icon gold">
              <FileClock size={20} />
            </div>
          </div>

          <strong>
            {loading ? "..." : actionCount}
          </strong>
          <small>Distinct recorded actions</small>
        </article>

        <article className="audit-stat-card">
          <div className="audit-stat-top">
            <span>Records on Page</span>
            <div className="audit-stat-icon purple">
              <CalendarDays size={20} />
            </div>
          </div>

          <strong>
            {loading ? "..." : auditData.items.length}
          </strong>
          <small>Currently displayed</small>
        </article>

      </section>

      {/* ACTION DISTRIBUTION */}
      <section className="audit-distribution-grid">

        <article className="panel audit-distribution-panel">
          <div className="panel-heading">
            <div>
              <h3>Activity by Entity</h3>
              <p>Events grouped by entity type</p>
            </div>
          </div>

          {auditData.entity_summary.length === 0 ? (
            <div className="audit-empty-small">
              No entity activity recorded.
            </div>
          ) : (
            <div className="audit-summary-list">
              {auditData.entity_summary.map((item) => (
                <div
                  className="audit-summary-row"
                  key={item.entity_type}
                >
                  <span>{item.entity_type}</span>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel audit-distribution-panel">
          <div className="panel-heading">
            <div>
              <h3>Activity by Action</h3>
              <p>Recorded system operations</p>
            </div>
          </div>

          {auditData.action_summary.length === 0 ? (
            <div className="audit-empty-small">
              No actions recorded.
            </div>
          ) : (
            <div className="audit-summary-list">
              {auditData.action_summary.map((item) => (
                <div
                  className="audit-summary-row"
                  key={item.action}
                >
                  <span>{formatAction(item.action)}</span>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          )}
        </article>

      </section>

      {/* AUDIT TABLE */}
      <section className="panel audit-table-panel">

        <div className="panel-heading audit-table-heading">
          <div>
            <h3>Audit Events</h3>
            <p>
              Search and inspect recorded system activity.
            </p>
          </div>

          <span className="audit-live-label">
            <span />
            Database records
          </span>
        </div>

        {/* FILTERS */}
        <div className="audit-filters">

          <div className="audit-search">
            <Search size={17} />
            <input
              type="text"
              placeholder="Search audit ID, entity, actor..."
              value={search}
              onChange={(event) =>
                changeSearch(event.target.value)
              }
            />
          </div>

          <select
            value={entityType}
            onChange={(event) =>
              changeEntity(event.target.value)
            }
          >
            <option value="">All entity types</option>
            {auditData.entity_summary.map((item) => (
              <option
                key={item.entity_type}
                value={item.entity_type}
              >
                {item.entity_type}
              </option>
            ))}
          </select>

          <select
            value={action}
            onChange={(event) =>
              changeAction(event.target.value)
            }
          >
            <option value="">All actions</option>
            {auditData.action_summary.map((item) => (
              <option
                key={item.action}
                value={item.action}
              >
                {formatAction(item.action)}
              </option>
            ))}
          </select>

          {hasFilters && (
            <button
              className="audit-clear-button"
              onClick={clearFilters}
            >
              Clear filters
            </button>
          )}

        </div>

        {/* TABLE */}
        <div className="table-scroll audit-table-scroll">
          <table className="audit-table">
            <thead>
              <tr>
                <th>AUDIT ID</th>
                <th>ENTITY</th>
                <th>ENTITY ID</th>
                <th>ACTION</th>
                <th>ACTOR</th>
                <th>TIMESTAMP</th>
                <th>DETAILS</th>
              </tr>
            </thead>

            <tbody>

              {loading ? (
                <tr>
                  <td colSpan="7" className="empty-table">
                    Loading audit records...
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan="7" className="empty-table">
                    Unable to retrieve audit records.
                  </td>
                </tr>
              ) : auditData.items.length === 0 ? (
                <tr>
                  <td colSpan="7" className="empty-table">
                    No audit events found.
                  </td>
                </tr>
              ) : (
                auditData.items.map((item) => (
                  <tr key={item.audit_id}>

                    <td className="audit-id-cell">
                      #{item.audit_id}
                    </td>

                    <td>
                      <span className="audit-entity-pill">
                        {item.entity_type}
                      </span>
                    </td>

                    <td className="audit-entity-id">
                      {item.entity_id}
                    </td>

                    <td>
                      <span
                        className={`audit-action-pill ${
                          item.action?.toLowerCase()
                        }`}
                      >
                        {formatAction(item.action)}
                      </span>
                    </td>

                    <td>
                      <span className="audit-actor">
                        <UserRound size={15} />
                        {item.actor}
                      </span>
                    </td>

                    <td className="audit-date">
                      {formatDate(item.created_at)}
                    </td>

                    <td>
                      <button
                        className="audit-view-button"
                        onClick={() => setSelectedEvent(item)}
                      >
                        <Eye size={15} />
                        View
                      </button>
                    </td>

                  </tr>
                ))
              )}

            </tbody>
          </table>
        </div>

        {/* PAGINATION */}
        <div className="audit-pagination">

          <span>
            Showing{" "}
            {auditData.total === 0
              ? 0
              : page * PAGE_SIZE + 1}
            {" "}to{" "}
            {Math.min(
              (page + 1) * PAGE_SIZE,
              auditData.total
            )}
            {" "}of {auditData.total} records
          </span>

          <div className="audit-pagination-controls">
            <button
              disabled={page === 0 || loading}
              onClick={() => setPage((current) => current - 1)}
              aria-label="Previous page"
            >
              <ChevronLeft size={17} />
            </button>

            <span>
              Page {page + 1} of {totalPages}
            </span>

            <button
              disabled={
                page + 1 >= totalPages || loading
              }
              onClick={() => setPage((current) => current + 1)}
              aria-label="Next page"
            >
              <ChevronRight size={17} />
            </button>
          </div>

        </div>

      </section>

      {/* EVENT DETAIL MODAL */}
      {selectedEvent && (
        <div
          className="audit-modal-overlay"
          onClick={() => setSelectedEvent(null)}
        >
          <section
            className="audit-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="audit-modal-title"
            onClick={(event) => event.stopPropagation()}
          >

            <div className="audit-modal-header">
              <div>
                <span className="eyebrow">
                  AUDIT EVENT #{selectedEvent.audit_id}
                </span>
                <h2 id="audit-modal-title">
                  {formatAction(selectedEvent.action)}
                </h2>
              </div>

              <button
                className="audit-modal-close"
                onClick={() => setSelectedEvent(null)}
                aria-label="Close details"
              >
                <X size={21} />
              </button>
            </div>

            <div className="audit-detail-meta">

              <div>
                <span>Entity type</span>
                <strong>{selectedEvent.entity_type}</strong>
              </div>

              <div>
                <span>Entity ID</span>
                <strong>{selectedEvent.entity_id}</strong>
              </div>

              <div>
                <span>Performed by</span>
                <strong>{selectedEvent.actor}</strong>
              </div>

              <div>
                <span>Timestamp</span>
                <strong>
                  {formatDate(selectedEvent.created_at)}
                </strong>
              </div>

            </div>

            <div className="audit-state-heading">
              <h3>State transition</h3>
              <p>
                Changes recorded during this event.
              </p>
            </div>

            <div className="audit-state-grid">

              <div className="audit-json-panel old">
                <div className="audit-json-heading">
                  <span>Previous State</span>
                  <span>BEFORE</span>
                </div>

                <pre>
                  {formatJson(selectedEvent.old_state)}
                </pre>
              </div>

              <div className="audit-state-arrow">
                <ArrowRight size={21} />
              </div>

              <div className="audit-json-panel new">
                <div className="audit-json-heading">
                  <span>New State</span>
                  <span>AFTER</span>
                </div>

                <pre>
                  {formatJson(selectedEvent.new_state)}
                </pre>
              </div>

            </div>

            <div className="audit-modal-footer">
              <button
                onClick={() => setSelectedEvent(null)}
              >
                Close details
              </button>
            </div>

          </section>
        </div>
      )}

      <footer className="page-footer">
        <span>PayFlow Reconciliation Platform</span>
        <span>
          {loading ? "Connecting..." : "Live database data"}
        </span>
      </footer>

    </div>
  );
}

export default Audit;
