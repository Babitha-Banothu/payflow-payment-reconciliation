
import { useEffect, useMemo, useState } from "react";

import {
  LayoutDashboard,
  ArrowLeftRight,
  GitCompareArrows,
  AlertCircle,
  History,
  ChartNoAxesCombined,
  Settings as SettingsIcon,
  Search,
  Bell,
  Menu,
  X,
  ChevronDown,
  CircleHelp,
  RefreshCw,
  Construction,
} from "lucide-react";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

import Exceptions from "./Exceptions";
import Transactions from "./Transactions";

import Reconciliation from "./Reconciliation";
import Audit from "./Audit";
import Reports from "./Reports";
import HelpSupport from "./HelpSupport";
import Settings from "./Settings";

import { getAllExceptions } from "./api";
import "./App.css";

const navigation = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Transactions", icon: ArrowLeftRight },
  { label: "Reconciliation", icon: GitCompareArrows },
  { label: "Exceptions", icon: AlertCircle },
  { label: "Audit History", icon: History },
  { label: "Reports", icon: ChartNoAxesCombined },
];

const secondaryNavigation = [
  { label: "Help & Support", icon: CircleHelp },
  { label: "Settings", icon: SettingsIcon },
];

const chartColors = [
  "#d87542",
  "#54856b",
  "#b18a43",
  "#7764a0",
  "#b65c4e",
];

const pageDescriptions = {
  Transactions: {
    subtitle: "View and monitor payment transactions.",
    description: "Payment Transactions",
    details:
      "This workspace will contain payment orders, payment attempts, merchant information, transaction statuses and search filters.",
  },
  Reconciliation: {
    subtitle: "Monitor payment matching and settlement results.",
    description: "Reconciliation Management",
    details:
      "This workspace will contain matched, partially matched, unmatched and rejected reconciliation records.",
  },
  "Audit History": {
    subtitle: "Track system activity and analyst actions.",
    description: "Audit History",
    details:
      "This workspace will display investigation events, resolution records, status changes, actors and timestamps.",
  },
  Reports: {
    subtitle: "Analyze reconciliation and exception performance.",
    description: "Reports & Analytics",
    details:
      "This workspace will contain reconciliation summaries, exception reports, operational metrics and CSV exports.",
  },
  "Help & Support": {
    subtitle: "Learn how to use the PayFlow platform.",
    description: "Help & Support",
    details:
      "This workspace will contain application documentation, reconciliation workflow guidance and troubleshooting information.",
  },
  Settings: {
    subtitle: "Manage application preferences.",
    description: "Application Settings",
    details:
      "This workspace will contain configurable application preferences and analyst settings.",
  },
};

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [menuOpen, setMenuOpen] = useState(false);

  const [exceptions, setExceptions] = useState([]);
  const [totalExceptions, setTotalExceptions] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  async function loadExceptions() {
    try {
      setLoading(true);
      setError("");

      const result = await getAllExceptions();

      setExceptions(result.items || []);
      setTotalExceptions(result.total || 0);
    } catch (err) {
      console.error("Failed to load exceptions:", err);
      setError(
        "Unable to load exception data. Please check your backend."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadExceptions();
  }, []);

  const stats = useMemo(() => {
    const count = (status) =>
      exceptions.filter(
        (item) => item.status?.toUpperCase() === status
      ).length;

    return {
      open: count("OPEN"),
      investigating: count("INVESTIGATING"),
      resolved: count("RESOLVED"),
      rejected: count("REJECTED"),
      high: exceptions.filter(
        (item) => item.severity?.toUpperCase() === "HIGH"
      ).length,
    };
  }, [exceptions]);

  const issueData = useMemo(() => {
    const counts = {};

    exceptions.forEach((item) => {
      const type = item.issue_type || "UNKNOWN";
      counts[type] = (counts[type] || 0) + 1;
    });

    return Object.entries(counts).map(([name, value]) => ({
      name: name.replaceAll("_", " "),
      value,
    }));
  }, [exceptions]);

  const statusData = [
    { name: "Open", count: stats.open },
    { name: "Investigating", count: stats.investigating },
    { name: "Resolved", count: stats.resolved },
    { name: "Rejected", count: stats.rejected },
  ];

  const filteredExceptions = useMemo(() => {
    const term = searchTerm.toLowerCase();

    return exceptions.filter((item) =>
      [
        item.exception_id,
        item.merchant_name,
        item.issue_type,
        item.status,
        item.severity,
      ]
        .filter(Boolean)
        .some((value) =>
          value.toLowerCase().includes(term)
        )
    );
  }, [exceptions, searchTerm]);

  const metrics = [
    {
      label: "Total Exceptions",
      value: totalExceptions,
      note: "Records from database",
      icon: AlertCircle,
    },
    {
      label: "Open",
      value: stats.open,
      note: "Awaiting investigation",
      icon: AlertCircle,
    },
    {
      label: "Investigating",
      value: stats.investigating,
      note: "Currently under review",
      icon: History,
    },
    {
      label: "Resolved",
      value: stats.resolved,
      note: "Successfully resolved",
      icon: GitCompareArrows,
    },
    {
      label: "High Severity",
      value: stats.high,
      note: "Require close attention",
      icon: ChartNoAxesCombined,
    },
  ];

  function navigateTo(page) {
    setActivePage(page);
    setMenuOpen(false);
    setSearchTerm("");
  }

  function renderDashboard() {
    return (
      <div className="page-content">
        <section className="page-heading">
          <div>
            <div className="eyebrow">PAYMENT OPERATIONS</div>
            <h1>Dashboard</h1>
            <p>
              Monitor payments, reconciliation activity and exceptions.
            </p>
          </div>

          <button className="date-button" onClick={loadExceptions}>
            <RefreshCw size={16} />
            Refresh data
          </button>
        </section>

        {error && (
          <div className="error-message">{error}</div>
        )}

        <section className="metrics-grid">
          {metrics.map(
            ({ label, value, note, icon: Icon }, index) => (
              <article className="metric-card" key={label}>
                <div className="metric-top">
                  <span>{label}</span>
                  <div className={`metric-icon metric-icon-${index}`}>
                    <Icon size={19} />
                  </div>
                </div>

                <div className="metric-value">
                  {loading
                    ? "..."
                    : value.toLocaleString("en-IN")}
                </div>

                <div className="metric-note">{note}</div>
              </article>
            )
          )}
        </section>

        <section className="dashboard-grid">
          <article className="panel trend-panel">
            <div className="panel-heading">
              <div>
                <h3>Exceptions by Status</h3>
                <p>Current exception lifecycle distribution</p>
              </div>
            </div>

            <div className="chart-container">
              {loading ? (
                <div className="chart-message">
                  Loading chart...
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={statusData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: 10 }}
                    />
                    <Tooltip />
                    <Bar
                      dataKey="count"
                      fill="#d87542"
                      radius={[5, 5, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </article>

          <article className="panel exceptions-panel">
            <div className="panel-heading">
              <div>
                <h3>Exceptions by Type</h3>
                <p>Distribution of reconciliation issues</p>
              </div>
            </div>

            <div className="chart-container">
              {loading ? (
                <div className="chart-message">
                  Loading chart...
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={issueData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={48}
                      outerRadius={85}
                      paddingAngle={3}
                    >
                      {issueData.map((entry, index) => (
                        <Cell
                          key={entry.name}
                          fill={
                            chartColors[
                              index % chartColors.length
                            ]
                          }
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="chart-legend">
              {issueData.map((item, index) => (
                <div key={item.name}>
                  <span
                    className="legend-dot"
                    style={{
                      background:
                        chartColors[
                          index % chartColors.length
                        ],
                    }}
                  />
                  {item.name}
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="panel recent-panel">
          <div className="panel-heading recent-heading">
            <div>
              <h3>Recent Exceptions</h3>
              <p>
                {filteredExceptions.length} records displayed
                from {totalExceptions} total exceptions
              </p>
            </div>

            <button
              className="view-all-button"
              onClick={() => navigateTo("Exceptions")}
            >
              View all exceptions
            </button>
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
                  <th>DETECTED AT</th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="6" className="empty-table">
                      Loading exception records...
                    </td>
                  </tr>
                ) : filteredExceptions.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="empty-table">
                      No matching exceptions found.
                    </td>
                  </tr>
                ) : (
                  filteredExceptions.slice(0, 10).map((item) => (
                    <tr key={item.exception_id}>
                      <td className="exception-id">
                        {item.exception_id}
                      </td>
                      <td>
                        {item.merchant_name || item.merchant_id}
                      </td>
                      <td>
                        {item.issue_type?.replaceAll("_", " ")}
                      </td>
                      <td>
                        <span
                          className={`status-pill ${item.status?.toLowerCase()}`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`severity-pill ${item.severity?.toLowerCase()}`}
                        >
                          {item.severity}
                        </span>
                      </td>
                      <td>
                        {item.detected_at
                          ? new Date(
                              item.detected_at
                            ).toLocaleDateString()
                          : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <footer className="page-footer">
          <span>PayFlow Reconciliation Platform</span>
          <span>
            {loading
              ? "Connecting..."
              : "Live database data"}
          </span>
        </footer>
      </div>
    );
  }

  function renderUpcomingPage(page) {
    const info = pageDescriptions[page];

    return (
      <div className="page-content">
        <section className="page-heading">
          <div>
            <div className="eyebrow">PAYMENT OPERATIONS</div>
            <h1>{page}</h1>
            <p>{info.subtitle}</p>
          </div>
        </section>

        <section className="panel upcoming-panel">
          <div className="upcoming-icon">
            <Construction size={32} />
          </div>

          <h2>{info.description}</h2>

          <p>{info.details}</p>

          <div className="upcoming-status">
            <span className="upcoming-dot" />
            Page implementation pending
          </div>
        </section>
      </div>
    );
  }

      
function renderActivePage() {
  if (activePage === "Dashboard") {
    return renderDashboard();
  }

  if (activePage === "Exceptions") {
    return (
      <Exceptions
        onBack={() => navigateTo("Dashboard")}
      />
    );
  }

  if (activePage === "Transactions") {
    return <Transactions />;
  }

  if (activePage === "Reconciliation") {
    return <Reconciliation />;
  }

  if (activePage === "Audit History") {
    return <Audit />;
  }

  if (activePage === "Reports") {
  return <Reports />;
}

if (activePage === "Help & Support") {
  return <HelpSupport />;
}
if (activePage === "Settings") {
  return <Settings />;
}
  return renderUpcomingPage(activePage);
}


  return (
    <div className="app-shell">
      {menuOpen && (
        <button
          className="mobile-overlay"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">P</div>

          <div>
            <h2>PayFlow</h2>
            <span>RECONCILIATION</span>
          </div>

          <button
            className="close-menu"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <div className="nav-section-label">WORKSPACE</div>

        <nav className="navigation">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`nav-item ${
                activePage === label ? "active" : ""
              }`}
              onClick={() => navigateTo(label)}
            >
              <Icon size={19} strokeWidth={1.8} />
              <span>{label}</span>

              {label === "Exceptions" && (
                <span className="nav-dot" />
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          {secondaryNavigation.map(
            ({ label, icon: Icon }) => (
              <button
                key={label}
                className={`nav-item ${
                  activePage === label ? "active" : ""
                }`}
                onClick={() => navigateTo(label)}
              >
                <Icon size={19} />
                <span>{label}</span>
              </button>
            )
          )}

          <div className="profile">
            <div className="avatar">A</div>

            <div className="profile-info">
              <strong>Analyst User</strong>
              <span>Administrator</span>
            </div>

            <ChevronDown size={17} />
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMenuOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={23} />
          </button>

          <div className="breadcrumb">
            Workspace <span>/</span>
            <strong>{activePage}</strong>
          </div>

          <div className="topbar-actions">
            <div className="search-box">
              <Search size={17} />
              <input
                placeholder="Search exceptions..."
                value={searchTerm}
                onChange={(event) =>
                  setSearchTerm(event.target.value)
                }
              />
            </div>

            <button
              className="icon-button notification-button"
              aria-label="Notifications"
            >
              <Bell size={19} />
            </button>

            <div className="topbar-avatar">A</div>
          </div>
        </header>

        {renderActivePage()}
      </main>
    </div>
  );
}

export default App;
