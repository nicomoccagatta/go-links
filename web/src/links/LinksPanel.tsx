import { useId, useState } from "react";
import buttons from "../components/buttons.module.css";
import { Notice } from "../components/Notice";
import { LinkList } from "./LinkList";
import styles from "./LinksPanel.module.css";
import { type Link, useLinks } from "./queries";

type LinksPanelProps = {
  onCreateFirst: () => void;
};

export function LinksPanel({ onCreateFirst }: LinksPanelProps) {
  const filterId = useId();
  const [filter, setFilter] = useState("");

  return (
    <section className={styles.panel} aria-labelledby="links-heading">
      <div className={styles.toolbar}>
        <h2 id="links-heading">Links</h2>
        <div className={styles.filter}>
          <label htmlFor={filterId}>Filter</label>
          <input
            id={filterId}
            type="search"
            className={styles.filterInput}
            placeholder="Name or description"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          />
        </div>
      </div>
      <LinksBody filter={filter} onCreateFirst={onCreateFirst} />
    </section>
  );
}

type LinksBodyProps = {
  filter: string;
  onCreateFirst: () => void;
};

function LinksBody({ filter, onCreateFirst }: LinksBodyProps) {
  const { data: links, error, isPending, isFetching, refetch } = useLinks();

  if (isPending) {
    return <p role="status">Loading links…</p>;
  }

  // Only a failed first load hides the list; a failed background refetch keeps showing data.
  if (links === undefined) {
    return (
      <div role="alert">
        <Notice
          tone="error"
          requestId={error?.requestId}
          action={
            <button
              type="button"
              className={buttons.secondary}
              disabled={isFetching}
              onClick={() => refetch()}
            >
              {isFetching ? "Retrying…" : "Try again"}
            </button>
          }
        >
          Couldn't load links. {error?.message}
        </Notice>
      </div>
    );
  }

  if (links.length === 0) {
    return (
      <div className={styles.empty}>
        <p>No links yet.</p>
        <button type="button" className={buttons.primary} onClick={onCreateFirst}>
          Create the first one
        </button>
      </div>
    );
  }

  const visibleLinks = filterLinks(links, filter);
  if (visibleLinks.length === 0) {
    return <p className={styles.empty}>No links match “{filter.trim()}”.</p>;
  }
  return <LinkList links={visibleLinks} />;
}

function filterLinks(links: Link[], filter: string): Link[] {
  const needle = filter.trim().toLowerCase();
  if (!needle) {
    return links;
  }
  return links.filter(
    (link) => link.slug.includes(needle) || (link.description ?? "").toLowerCase().includes(needle),
  );
}
