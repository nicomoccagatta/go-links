import type { ReactNode } from "react";
import styles from "./Notice.module.css";

type NoticeProps = {
  tone: "info" | "success" | "error";
  /** Shown so users can quote it in a bug report and we can find the matching log line. */
  requestId?: string | null;
  action?: ReactNode;
  children: ReactNode;
};

export function Notice({ tone, requestId, action, children }: NoticeProps) {
  return (
    <div className={styles.notice} data-tone={tone}>
      <p>
        {children}
        {requestId && (
          <span className={styles.requestId}>
            {" "}
            Request ID: <code>{requestId}</code>
          </span>
        )}
      </p>
      {action}
    </div>
  );
}
