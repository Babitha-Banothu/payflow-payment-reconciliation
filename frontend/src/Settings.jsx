
import { useEffect, useState } from "react";
import {
  UserRound,
  Bell,
  Palette,
  ShieldCheck,
  Monitor,
  Save,
  RotateCcw,
} from "lucide-react";
import "./Settings.css";

const DEFAULT_SETTINGS = {
  profile: {
    name: "Analyst User",
    email: "analyst@payflow.local",
    role: "Administrator",
  },
  preferences: {
    dateFormat: "DD/MM/YYYY",
    defaultCurrency: "INR",
    compactView: false,
  },
  notifications: {
    payments: true,
    reconciliation: true,
    exceptions: true,
    audit: false,
  },
};

const SETTINGS_SECTIONS = [
  { id: "profile-settings", label: "Profile", icon: UserRound },
  { id: "preferences-settings", label: "Preferences", icon: Palette },
  { id: "notification-settings", label: "Notifications", icon: Bell },
  { id: "security-settings", label: "Security", icon: ShieldCheck },
  { id: "system-settings", label: "System information", icon: Monitor },
];

function loadSettings() {
  try {
    const stored = localStorage.getItem("payflow-settings");

    if (!stored) return DEFAULT_SETTINGS;

    const parsed = JSON.parse(stored);

    return {
      profile: { ...DEFAULT_SETTINGS.profile, ...parsed.profile },
      preferences: {
        ...DEFAULT_SETTINGS.preferences,
        ...parsed.preferences,
      },
      notifications: {
        ...DEFAULT_SETTINGS.notifications,
        ...parsed.notifications,
      },
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function Settings() {
  const [settings, setSettings] = useState(loadSettings);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const { profile, preferences, notifications } = settings;

  useEffect(() => {
    function handleStorageChange(event) {
      if (event.key === "payflow-settings") {
        setSettings(loadSettings());
      }
    }

    window.addEventListener("storage", handleStorageChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
    };
  }, []);

  function updateSetting(section, field, value) {
    setSettings((previous) => ({
      ...previous,
      [section]: {
        ...previous[section],
        [field]: value,
      },
    }));

    setSaved(false);
    setError("");
  }

  function navigateToSection(sectionId) {
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  function saveSettings() {
    if (!profile.name.trim()) {
      setError("Please enter your full name.");
      return;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailPattern.test(profile.email.trim())) {
      setError("Please enter a valid email address.");
      return;
    }

    try {
      localStorage.setItem(
        "payflow-settings",
        JSON.stringify(settings)
      );

      setSaved(true);
      setError("");
    } catch {
      setError("Unable to save settings in this browser.");
    }
  }

  function resetSettings() {
    const confirmed = window.confirm(
      "Are you sure you want to restore all default settings?"
    );

    if (!confirmed) return;

    setSettings(DEFAULT_SETTINGS);
    localStorage.removeItem("payflow-settings");
    setSaved(false);
    setError("");
  }

  return (
    <div className="page-content settings-page">
      <section className="page-heading">
        <div>
          <div className="eyebrow">APPLICATION CONFIGURATION</div>
          <h1>Settings</h1>
          <p>
            Manage your profile, preferences and application notifications.
          </p>
        </div>

        <div className="settings-actions">
          <button className="settings-reset" onClick={resetSettings}>
            <RotateCcw size={16} />
            Reset
          </button>

          <button className="settings-save" onClick={saveSettings}>
            <Save size={16} />
            Save changes
          </button>
        </div>
      </section>

      {saved && (
        <div className="settings-success">
          Your settings have been saved successfully.
        </div>
      )}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <section className="settings-layout">
        <div className="settings-sidebar">
          {SETTINGS_SECTIONS.map(({ id, label, icon: Icon }) => (
            <button
              type="button"
              key={id}
              className="settings-nav-item"
              onClick={() => navigateToSection(id)}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </div>

        <div className="settings-content">
          <section
            className="settings-card"
            id="profile-settings"
          >
            <div className="settings-card-heading">
              <div className="settings-card-icon orange">
                <UserRound size={20} />
              </div>
              <div>
                <h2>Profile Settings</h2>
                <p>Manage your analyst profile information.</p>
              </div>
            </div>

            <div className="settings-form-grid">
              <label>
                Full name
                <input
                  value={profile.name}
                  onChange={(event) =>
                    updateSetting("profile", "name", event.target.value)
                  }
                  placeholder="Enter your name"
                />
              </label>

              <label>
                Email address
                <input
                  type="email"
                  value={profile.email}
                  onChange={(event) =>
                    updateSetting("profile", "email", event.target.value)
                  }
                  placeholder="Enter email address"
                />
              </label>

              <label>
                Role
                <input value={profile.role} disabled />
              </label>
            </div>
          </section>

          <section
            className="settings-card"
            id="preferences-settings"
          >
            <div className="settings-card-heading">
              <div className="settings-card-icon purple">
                <Palette size={20} />
              </div>
              <div>
                <h2>Application Preferences</h2>
                <p>Configure how information is displayed.</p>
              </div>
            </div>

            <div className="settings-form-grid">
              <label>
                Date format
                <select
                  value={preferences.dateFormat}
                  onChange={(event) =>
                    updateSetting(
                      "preferences",
                      "dateFormat",
                      event.target.value
                    )
                  }
                >
                  <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                  <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                  <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                </select>
              </label>

              <label>
                Default currency
                <select
                  value={preferences.defaultCurrency}
                  onChange={(event) =>
                    updateSetting(
                      "preferences",
                      "defaultCurrency",
                      event.target.value
                    )
                  }
                >
                  <option value="INR">INR - Indian Rupee</option>
                  <option value="USD">USD - US Dollar</option>
                  <option value="EUR">EUR - Euro</option>
                  <option value="GBP">GBP - British Pound</option>
                </select>
              </label>
            </div>

            <div className="settings-toggle-row">
              <div>
                <strong>Compact view</strong>
                <p>Use a more compact display for data tables.</p>
              </div>

              <input
                type="checkbox"
                checked={preferences.compactView}
                onChange={(event) =>
                  updateSetting(
                    "preferences",
                    "compactView",
                    event.target.checked
                  )
                }
              />
            </div>
          </section>

          <section
            className="settings-card"
            id="notification-settings"
          >
            <div className="settings-card-heading">
              <div className="settings-card-icon green">
                <Bell size={20} />
              </div>
              <div>
                <h2>Notification Preferences</h2>
                <p>Choose which application events you want to receive.</p>
              </div>
            </div>

            {[
              ["payments", "Payment notifications", "Updates about payment activity."],
              ["reconciliation", "Reconciliation alerts", "Updates about settlement matching."],
              ["exceptions", "Exception alerts", "Updates about newly detected exceptions."],
              ["audit", "Audit activity", "Updates about recorded analyst actions."],
            ].map(([key, title, description]) => (
              <div className="settings-toggle-row" key={key}>
                <div>
                  <strong>{title}</strong>
                  <p>{description}</p>
                </div>

                <input
                  type="checkbox"
                  checked={notifications[key]}
                  onChange={(event) =>
                    updateSetting(
                      "notifications",
                      key,
                      event.target.checked
                    )
                  }
                />
              </div>
            ))}
          </section>

          <section
            className="settings-card"
            id="security-settings"
          >
            <div className="settings-card-heading">
              <div className="settings-card-icon red">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h2>Security</h2>
                <p>Application access information.</p>
              </div>
            </div>

            <div className="settings-info-row">
              <span>Current role</span>
              <strong>{profile.role}</strong>
            </div>

            <div className="settings-info-row">
              <span>Authentication</span>
              <strong>Demo application</strong>
            </div>

            <p className="settings-note">
              Password management and account security require a configured
              authentication service.
            </p>
          </section>

          <section
            className="settings-card"
            id="system-settings"
          >
            <div className="settings-card-heading">
              <div className="settings-card-icon orange">
                <Monitor size={20} />
              </div>
              <div>
                <h2>System Information</h2>
                <p>PayFlow application environment.</p>
              </div>
            </div>

            <div className="settings-info-row">
              <span>Application</span>
              <strong>PayFlow Reconciliation Platform</strong>
            </div>

            <div className="settings-info-row">
              <span>Version</span>
              <strong>1.0.0</strong>
            </div>

            <div className="settings-info-row">
              <span>Environment</span>
              <strong>Development</strong>
            </div>
          </section>
        </div>
      </section>

      <footer className="page-footer">
        <span>PayFlow Reconciliation Platform</span>
        <span>Application Settings</span>
      </footer>
    </div>
  );
}

export default Settings;
