
import { useEffect, useMemo, useState } from "react";
import {
  RefreshCw,
  Download,
  CreditCard,
  CheckCircle2,
  GitCompareArrows,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
} from "recharts";

import { getReportsOverview } from "./api";
import "./Reports.css";

const COLORS = [
  "#d87542",
  "#54856b",
  "#b18a43",
  "#7764a0",
  "#b65c4e",
];

const CURRENCY_COLORS = {
  EUR: "#d87542",
  GBP: "#54856b",
  INR: "#b18a43",
  USD: "#7764a0",
};

function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-IN");
}

function formatLabel(value = "") {
  return value.replaceAll("_", " ");
}

function downloadCSV(filename, rows) {
  if (!rows.length) return;

  const headers = Object.keys(rows[0]);

  const escapeCSV = (value) => {
    const text = String(value ?? "");
    return `"${text.replaceAll('"', '""')}"`;
  };

  const csv = [
    headers.map(escapeCSV).join(","),
    ...rows.map((row) =>
      headers.map((header) => escapeCSV(row[header])).join(",")
    ),
  ].join("\n");

  const blob = new Blob(
    ["\uFEFF" + csv],
    { type: "text/csv;charset=utf-8;" }
  );

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

function Reports() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadReports(showRefresh = false) {
    try {
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const result = await getReportsOverview();
      setReport(result);
    } catch (err) {
      console.error("Reports loading error:", err);
      setError(err.message || "Unable to load reports.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  const transactionTotals = useMemo(() => {
    const rows = report?.transaction_summary || [];

    return {
      total: rows.reduce(
        (sum, item) => sum + Number(item.total_transactions || 0),
        0
      ),
      successful: rows.reduce(
        (sum, item) => sum + Number(item.successful || 0),
        0
      ),
      failed: rows.reduce(
        (sum, item) => sum + Number(item.failed || 0),
        0
      ),
    };
  }, [report]);

  const reconciliationTotals = useMemo(() => {
    const rows = report?.reconciliation_summary || [];

    return rows.reduce(
      (result, item) => {
        result.total += Number(item.count || 0);

        if (item.status === "MATCHED") {
          result.matched += Number(item.count || 0);
        }

        if (item.status === "UNMATCHED") {
          result.unmatched += Number(item.count || 0);
        }

        return result;
      },
      { total: 0, matched: 0, unmatched: 0 }
    );
  }, [report]);

  const exceptionTotals = useMemo(() => {
    const rows = report?.exception_summary || [];

    return rows.reduce(
      (result, item) => {
        result.total += Number(item.count || 0);

        if (item.status === "OPEN") {
          result.open += Number(item.count || 0);
        }

        if (item.status === "RESOLVED") {
          result.resolved += Number(item.count || 0);
        }

        return result;
      },
      { total: 0, open: 0, resolved: 0 }
    );
  }, [report]);

  const statusChartData = useMemo(
    () =>
      (report?.transaction_status || []).map((item) => ({
        name: formatLabel(item.status),
        count: Number(item.count || 0),
      })),
    [report]
  );

  const reconciliationChartData = useMemo(
    () =>
      (report?.reconciliation_summary || []).map((item) => ({
        name: formatLabel(item.status),
        count: Number(item.count || 0),
      })),
    [report]
  );

  const currencyChartData = useMemo(
    () =>
      (report?.transaction_summary || []).map((item) => ({
        currency: item.currency,
        total: Number(item.total_transactions || 0),
        successful: Number(item.successful || 0),
        failed: Number(item.failed || 0),
      })),
    [report]
  );

  const dailyChartData = useMemo(() => {
    const rows = report?.daily_transactions || [];
    const dates = {};

    rows.forEach((item) => {
      if (!dates[item.transaction_date]) {
        dates[item.transaction_date] = {
          date: item.transaction_date,
          EUR: 0,
          GBP: 0,
          INR: 0,
          USD: 0,
        };
      }

      dates[item.transaction_date][item.currency] =
        Number(item.transaction_count || 0);
    });

    return Object.values(dates).sort(
      (a, b) => a.date.localeCompare(b.date)
    );
  }, [report]);

  const exceptionChartData = useMemo(() => {
    const rows = report?.exception_summary || [];
    const grouped = {};

    rows.forEach((item) => {
      if (!grouped[item.severity]) {
        grouped[item.severity] = {
          severity: item.severity,
          open: 0,
          resolved: 0,
          other: 0,
        };
      }

      if (item.status === "OPEN") {
        grouped[item.severity].open += Number(item.count || 0);
      } else if (item.status === "RESOLVED") {
        grouped[item.severity].resolved += Number(item.count || 0);
      } else {
        grouped[item.severity].other += Number(item.count || 0);
      }
    });

    return Object.values(grouped);
  }, [report]);

  function exportReports() {
    if (!report) return;

    const rows = [];

    (report.transaction_summary || []).forEach((item) => {
      rows.push({
        report_type: "Transaction Summary",
        currency: item.currency,
        status: "ALL",
        count: item.total_transactions,
        successful: item.successful,
        failed: item.failed,
        amount_minor: item.total_amount_minor,
      });
    });

    (report.reconciliation_summary || []).forEach((item) => {
      rows.push({
        report_type: "Reconciliation",
        currency: "",
        status: item.status,
        count: item.count,
        successful: "",
        failed: "",
        amount_minor: item.absolute_variance_minor,
      });
    });

    (report.exception_summary || []).forEach((item) => {
      rows.push({
        report_type: "Exceptions",
        currency: "",
        status: `${item.status} - ${item.severity}`,
        count: item.count,
        successful: "",
        failed: "",
        amount_minor: "",
      });
    });

    downloadCSV("payflow-reports.csv", rows);
  }

  return (
    <div className="page-content reports-page">

      {/* HEADER */}
      <section className="page-heading reports-heading">
        <div>
          <div className="eyebrow">PAYMENT OPERATIONS</div>
          <h1>Reports & Analytics</h1>
          <p>
            Analyze payment performance, reconciliation
            results and exception activity.
          </p>
        </div>

        <div className="reports-header-actions">
          <button
            className="reports-refresh-button"
            onClick={() => loadReports(true)}
            disabled={refreshing}
          >
            <RefreshCw
              size={16}
              className={refreshing ? "reports-spinning" : ""}
            />
            Refresh
          </button>

          <button
            className="reports-export-button"
            onClick={exportReports}
            disabled={!report || loading}
          >
            <Download size={16} />
            Export CSV
          </button>
        </div>
      </section>

      {error && (
        <div className="reports-error">
          {error}
          <button onClick={() => loadReports(true)}>
            Retry
          </button>
        </div>
      )}

      {/* KPI CARDS */}
      <section className="reports-kpi-grid">

        <article className="reports-kpi-card">
          <div className="reports-kpi-top">
            <span>Total Transactions</span>
            <CreditCard size={20} />
          </div>
          <strong>
            {loading ? "..." : formatNumber(transactionTotals.total)}
          </strong>
          <small>Across all currencies</small>
        </article>

        <article className="reports-kpi-card">
          <div className="reports-kpi-top">
            <span>Successful Payments</span>
            <CheckCircle2 size={20} />
          </div>
          <strong>
            {loading ? "..." : formatNumber(transactionTotals.successful)}
          </strong>
          <small>
            {transactionTotals.total
              ? `${(
                  (transactionTotals.successful /
                    transactionTotals.total) *
                  100
                ).toFixed(1)}% of transactions`
              : "No transaction data"}
          </small>
        </article>

        <article className="reports-kpi-card">
          <div className="reports-kpi-top">
            <span>Matched Reconciliations</span>
            <GitCompareArrows size={20} />
          </div>
          <strong>
            {loading ? "..." : formatNumber(reconciliationTotals.matched)}
          </strong>
          <small>
            {formatNumber(reconciliationTotals.total)} total matches
          </small>
        </article>

        <article className="reports-kpi-card">
          <div className="reports-kpi-top">
            <span>Open Exceptions</span>
            <AlertTriangle size={20} />
          </div>
          <strong>
            {loading ? "..." : formatNumber(exceptionTotals.open)}
          </strong>
          <small>
            {formatNumber(exceptionTotals.resolved)} resolved
          </small>
        </article>

      </section>

      {loading && !report ? (
        <section className="panel reports-loading">
          <RefreshCw size={22} className="reports-spinning" />
          Loading analytics from database...
        </section>
      ) : report && (
        <>
          {/* TRANSACTION CHARTS */}
          <section className="reports-chart-grid">

            <article className="panel reports-chart-panel">
              <div className="panel-heading">
                <div>
                  <h3>Transaction Status</h3>
                  <p>Payment orders grouped by status</p>
                </div>
              </div>

              <div className="reports-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusChartData}
                      dataKey="count"
                      nameKey="name"
                      cx="50%"
                      cy="48%"
                      innerRadius={55}
                      outerRadius={95}
                      paddingAngle={3}
                    >
                      {statusChartData.map((item, index) => (
                        <Cell
                          key={item.name}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="panel reports-chart-panel">
              <div className="panel-heading">
                <div>
                  <h3>Currency-wise Transactions</h3>
                  <p>Successful and failed payment orders</p>
                </div>
              </div>

              <div className="reports-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={currencyChartData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis dataKey="currency" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Legend />
                    <Bar
                      dataKey="successful"
                      name="Successful"
                      fill="#54856b"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="failed"
                      name="Failed"
                      fill="#d87542"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

          </section>

          {/* DAILY TRANSACTION TREND */}
          <section className="panel reports-trend-panel">
            <div className="panel-heading">
              <div>
                <h3>Daily Transaction Volume</h3>
                <p>
                  Transaction counts by currency over the last 30 days
                </p>
              </div>
              <TrendingUp size={20} />
            </div>

            <div className="reports-trend-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailyChartData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) =>
                      value.slice(5)
                    }
                    minTickGap={25}
                  />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  {["EUR", "GBP", "INR", "USD"].map((currency) => (
                    <Line
                      key={currency}
                      type="monotone"
                      dataKey={currency}
                      stroke={CURRENCY_COLORS[currency]}
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* RECONCILIATION AND EXCEPTIONS */}
          <section className="reports-chart-grid">

            <article className="panel reports-chart-panel">
              <div className="panel-heading">
                <div>
                  <h3>Reconciliation Performance</h3>
                  <p>Matching results by status</p>
                </div>
              </div>

              <div className="reports-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={reconciliationChartData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis dataKey="name" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar
                      dataKey="count"
                      name="Records"
                      fill="#d87542"
                      radius={[5, 5, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="panel reports-chart-panel">
              <div className="panel-heading">
                <div>
                  <h3>Exception Breakdown</h3>
                  <p>Open and resolved exceptions by severity</p>
                </div>
              </div>

              <div className="reports-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={exceptionChartData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis dataKey="severity" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Legend />
                    <Bar
                      dataKey="open"
                      name="Open"
                      stackId="exceptions"
                      fill="#d87542"
                    />
                    <Bar
                      dataKey="resolved"
                      name="Resolved"
                      stackId="exceptions"
                      fill="#54856b"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

          </section>

          {/* CURRENCY SUMMARY TABLE */}
          <section className="panel reports-table-panel">
            <div className="panel-heading">
              <div>
                <h3>Currency Summary</h3>
                <p>
                  Transaction amounts remain separated by currency.
                </p>
              </div>
            </div>

            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>CURRENCY</th>
                    <th>TRANSACTIONS</th>
                    <th>SUCCESSFUL</th>
                    <th>FAILED</th>
                    <th>TOTAL AMOUNT</th>
                  </tr>
                </thead>

                <tbody>
                  {report.transaction_summary.map((item) => (
                    <tr key={item.currency}>
                      <td>
                        <strong>{item.currency}</strong>
                      </td>
                      <td>{formatNumber(item.total_transactions)}</td>
                      <td>{formatNumber(item.successful)}</td>
                      <td>{formatNumber(item.failed)}</td>
                      <td>
                        {(Number(item.total_amount_minor || 0) / 100)
                          .toLocaleString("en-IN", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}{" "}
                        {item.currency}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <footer className="page-footer">
            <span>PayFlow Reconciliation Platform</span>
            <span>Live database reports</span>
          </footer>
        </>
      )}
    </div>
  );
}

export default Reports;
