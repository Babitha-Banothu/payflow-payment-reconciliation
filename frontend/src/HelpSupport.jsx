
import { useState } from "react";
import {
  BookOpen,
  Workflow,
  MessageCircleQuestion,
  LifeBuoy,
  Search,
  ChevronDown,
  ArrowRight,
  ShieldCheck,
  CreditCard,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import "./HelpSupport.css";

const helpCategories = [
  {
    title: "Getting Started",
    description: "Learn how to navigate PayFlow.",
    icon: BookOpen,
    color: "orange",
    articles: 4,
  },
  {
    title: "Reconciliation Guide",
    description: "Understand settlement matching.",
    icon: Workflow,
    color: "green",
    articles: 5,
  },
  {
    title: "Transactions",
    description: "Understand payment statuses and records.",
    icon: CreditCard,
    color: "purple",
    articles: 4,
  },
  {
    title: "Exceptions",
    description: "Investigate and resolve payment issues.",
    icon: AlertCircle,
    color: "red",
    articles: 4,
  },
];

const faqs = [
  {
    question: "What is payment reconciliation?",
    answer:
      "Payment reconciliation compares internal payment and settlement records with processor and bank records to identify matched, unmatched, partial and rejected transactions.",
    category: "Reconciliation",
  },
  {
    question: "What does Matched mean?",
    answer:
      "A matched record indicates that the settlement information and corresponding bank information have been successfully reconciled.",
    category: "Reconciliation",
  },
  {
    question: "What does Unmatched mean?",
    answer:
      "An unmatched record indicates that the expected settlement could not be matched with the available bank information.",
    category: "Reconciliation",
  },
  {
    question: "What is a Partial reconciliation?",
    answer:
      "A partial reconciliation indicates that the records have been linked but a difference remains between the expected and actual amounts.",
    category: "Reconciliation",
  },
  {
    question: "How do I investigate an exception?",
    answer:
      "Open the Exceptions section, select the exception you want to review, inspect its available details and evidence, and start an investigation.",
    category: "Exceptions",
  },
  {
    question: "Can I resolve an exception?",
    answer:
      "Yes. Open an exception, review its details and use the available resolution action. The system records the action in Audit History.",
    category: "Exceptions",
  },
  {
    question: "What information is available in Audit History?",
    answer:
      "Audit History displays recorded entity events, actions, actors, timestamps and available previous and updated states.",
    category: "Audit",
  },
  {
    question: "Can I export reports?",
    answer:
      "Open Reports & Analytics and select Export CSV to download the available report summaries.",
    category: "Reports",
  },
  {
    question: "Why are my reports taking time to load?",
    answer:
      "Reports depend on the backend API and database connection. Check that both services are running and that the Reports API is responding.",
    category: "Troubleshooting",
  },
];

function HelpSupport() {
  const [search, setSearch] = useState("");
  const [openFaq, setOpenFaq] = useState(null);

  const filteredFaqs = faqs.filter((faq) =>
    `${faq.question} ${faq.answer} ${faq.category}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  return (
    <div className="page-content help-page">
      <section className="page-heading help-heading">
        <div>
          <div className="eyebrow">SUPPORT CENTRE</div>
          <h1>Help & Support</h1>
          <p>
            Find guidance, understand workflows and get help using PayFlow.
          </p>
        </div>
      </section>

      <section className="help-hero">
        <div className="help-hero-content">
          <span className="help-hero-label">PAYFLOW KNOWLEDGE CENTRE</span>
          <h2>How can we help you?</h2>
          <p>
            Explore guides and answers to common questions about payment
            operations and reconciliation.
          </p>

          <div className="help-search">
            <Search size={19} />
            <input
              type="text"
              placeholder="Search for help..."
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setOpenFaq(null);
              }}
            />
          </div>
        </div>

        <div className="help-hero-icon">
          <LifeBuoy size={100} strokeWidth={1.1} />
        </div>
      </section>

      <section className="help-section">
        <div className="help-section-heading">
          <div>
            <h2>Browse help topics</h2>
            <p>Explore guides by category.</p>
          </div>
        </div>

        <div className="help-category-grid">
          {helpCategories.map(({ title, description, icon: Icon, color, articles }) => (
            <article className="help-category-card" key={title}>
              <div className={`help-category-icon ${color}`}>
                <Icon size={22} />
              </div>
              <h3>{title}</h3>
              <p>{description}</p>
              <span>{articles} help topics</span>
            </article>
          ))}
        </div>
      </section>

      <section className="help-section faq-section">
        <div className="help-section-heading">
          <div>
            <h2>Frequently asked questions</h2>
            <p>Quick answers to common PayFlow questions.</p>
          </div>
          <span className="faq-count">
            {filteredFaqs.length} articles
          </span>
        </div>

        <div className="faq-list">
          {filteredFaqs.length === 0 ? (
            <div className="faq-empty">
              No help articles match your search.
            </div>
          ) : (
            filteredFaqs.map((faq, index) => (
              <article className="faq-item" key={faq.question}>
                <button
                  className="faq-question"
                  onClick={() =>
                    setOpenFaq(openFaq === index ? null : index)
                  }
                  aria-expanded={openFaq === index}
                >
                  <span>
                    <small>{faq.category}</small>
                    <strong>{faq.question}</strong>
                  </span>
                  <ChevronDown
                    size={19}
                    className={openFaq === index ? "faq-chevron open" : "faq-chevron"}
                  />
                </button>

                {openFaq === index && (
                  <div className="faq-answer">
                    {faq.answer}
                  </div>
                )}
              </article>
            ))
          )}
        </div>
      </section>

      <section className="help-contact">
        <div className="help-contact-icon">
          <ShieldCheck size={25} />
        </div>
        <div>
          <h3>Need additional assistance?</h3>
          <p>
            Review the application workflows or contact your system
            administrator for support.
          </p>
        </div>
        <ArrowRight size={21} />
      </section>

      <footer className="page-footer">
        <span>PayFlow Reconciliation Platform</span>
        <span>Help & Support Centre</span>
      </footer>
    </div>
  );
}

export default HelpSupport;
