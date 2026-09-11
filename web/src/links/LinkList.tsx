import { useDeferredValue, ViewTransition } from "react";
import { goLinkHref } from "../config";
import styles from "./LinkList.module.css";
import type { Link } from "./queries";

type LinkListProps = {
  links: Link[];
};

export function LinkList({ links }: LinkListProps) {
  // TanStack Query updates are synchronous, and <ViewTransition> only animates transitions.
  // A deferred value re-renders as a transition, so a newly created link animates in.
  const deferredLinks = useDeferredValue(links);

  return (
    <ul role="list" className={styles.list}>
      {deferredLinks.map((link) => (
        <ViewTransition key={link.slug} enter="link-enter" exit="none" default="none">
          <li className={styles.item}>
            <a className={styles.slug} href={goLinkHref(link.slug)}>
              go/{link.slug}
            </a>
            <span className={styles.visits}>
              {link.visit_count} {link.visit_count === 1 ? "visit" : "visits"}
            </span>
            <span className={styles.target} title={link.target_url}>
              {link.target_url}
            </span>
            {link.description && <p className={styles.description}>{link.description}</p>}
          </li>
        </ViewTransition>
      ))}
    </ul>
  );
}
