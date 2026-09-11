import { type ComponentProps, useId } from "react";
import styles from "./TextField.module.css";

type TextFieldProps = ComponentProps<"input"> & {
  label: string;
  hint?: string;
  error?: string;
  /** Visual prefix inside the control, e.g. "go/". Hidden from assistive tech; say it in `hint`. */
  prefix?: string;
};

export function TextField({ label, hint, error, prefix, ref, ...inputProps }: TextFieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label}
      </label>
      <div className={styles.control} data-invalid={error ? true : undefined}>
        {prefix && (
          <span className={styles.prefix} aria-hidden="true">
            {prefix}
          </span>
        )}
        <input
          {...inputProps}
          ref={ref}
          id={id}
          className={styles.input}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        />
      </div>
      {hint && (
        <p id={hintId} className={styles.hint}>
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
}
