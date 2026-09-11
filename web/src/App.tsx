import { useRef, useState } from "react";
import type { ApiError } from "./api/errors";
import styles from "./App.module.css";
import buttons from "./components/buttons.module.css";
import { Notice } from "./components/Notice";
import { CreateLinkForm } from "./links/CreateLinkForm";
import { LinksPanel } from "./links/LinksPanel";
import type { Link } from "./links/queries";

type Outcome =
  | { tone: "success"; text: string }
  | { tone: "error"; text: string; requestId: string | null };

// The API redirects unknown go/<slug> visits here as /?new=<slug>.
function readPrefillSlug(): string | null {
  return new URLSearchParams(window.location.search).get("new");
}

function clearPrefillFromUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete("new");
  window.history.replaceState(null, "", url);
}

export default function App() {
  const [prefillSlug, setPrefillSlug] = useState(readPrefillSlug);
  const [formOpen, setFormOpen] = useState(prefillSlug !== null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);

  function openForm() {
    setOutcome(null);
    setFormOpen(true);
  }

  function closeForm() {
    setFormOpen(false);
    setPrefillSlug(null);
    clearPrefillFromUrl();
  }

  function cancelForm() {
    setOutcome(null);
    closeForm();
  }

  function handleCreated(link: Link) {
    closeForm();
    setOutcome({ tone: "success", text: `Created go/${link.slug}.` });
    // The form (and its focused submit button) is gone; keep focus somewhere predictable.
    toggleRef.current?.focus();
  }

  function handleFailed(error: ApiError) {
    setOutcome({
      tone: "error",
      text: `Couldn't create the link. ${error.message}`,
      requestId: error.requestId,
    });
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>go/links</h1>
          <p className={styles.tagline}>Short, memorable links to everything internal.</p>
        </div>
        <button
          ref={toggleRef}
          type="button"
          className={formOpen ? buttons.secondary : buttons.primary}
          aria-expanded={formOpen}
          aria-controls="create-link"
          onClick={formOpen ? cancelForm : openForm}
        >
          {formOpen ? "Cancel" : "New link"}
        </button>
      </header>

      <main className={styles.main}>
        <div aria-live="polite">
          {outcome && (
            <Notice
              tone={outcome.tone}
              requestId={outcome.tone === "error" ? outcome.requestId : null}
            >
              {outcome.text}
            </Notice>
          )}
        </div>

        {formOpen && (
          <section id="create-link" className={styles.card} aria-labelledby="create-link-heading">
            <h2 id="create-link-heading">New link</h2>
            {prefillSlug !== null && (
              <Notice tone="info">go/{prefillSlug} doesn't exist yet — create it?</Notice>
            )}
            <CreateLinkForm
              initialSlug={prefillSlug ?? ""}
              onCreated={handleCreated}
              onFailed={handleFailed}
            />
          </section>
        )}

        <LinksPanel onCreateFirst={openForm} />
      </main>
    </div>
  );
}
