import { type FormEvent, useRef, useState } from "react";
import { flushSync } from "react-dom";
import type { ApiError, FieldError } from "../api/errors";
import buttons from "../components/buttons.module.css";
import { TextField } from "../components/TextField";
import styles from "./CreateLinkForm.module.css";
import { type Link, useCreateLink } from "./queries";
import {
  type FieldErrors,
  LINK_FIELDS,
  type LinkDraft,
  type LinkField,
  MAX_DESCRIPTION_LENGTH,
  normalizeSlug,
  validateLink,
} from "./validation";

type CreateLinkFormProps = {
  initialSlug: string;
  onCreated: (link: Link) => void;
  onFailed: (error: ApiError) => void;
};

export function CreateLinkForm({ initialSlug, onCreated, onFailed }: CreateLinkFormProps) {
  const [draft, setDraft] = useState<LinkDraft>({
    slug: initialSlug,
    target_url: "",
    description: "",
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const createLink = useCreateLink();
  const slugRef = useRef<HTMLInputElement>(null);
  const targetUrlRef = useRef<HTMLInputElement>(null);
  const descriptionRef = useRef<HTMLInputElement>(null);

  function updateField(field: LinkField, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function showErrors(nextErrors: FieldErrors) {
    // Render the messages first, so the focused field is announced with its error.
    flushSync(() => setErrors(nextErrors));
    const inputs = { slug: slugRef, target_url: targetUrlRef, description: descriptionRef };
    const firstInvalid = LINK_FIELDS.find((field) => nextErrors[field]);
    if (firstInvalid) {
      inputs[firstInvalid].current?.focus();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const clientErrors = validateLink(draft);
    if (Object.keys(clientErrors).length > 0) {
      showErrors(clientErrors);
      return;
    }

    const description = draft.description.trim();
    createLink.mutate(
      {
        slug: normalizeSlug(draft.slug),
        target_url: draft.target_url,
        description: description || null,
      },
      {
        onSuccess: (link) => onCreated(link),
        onError: (error) => {
          showErrors(fieldErrorsFrom(error.details));
          onFailed(error);
        },
      },
    );
  }

  return (
    <form className={styles.form} noValidate onSubmit={handleSubmit}>
      <TextField
        ref={slugRef}
        name="slug"
        label="Short name"
        prefix="go/"
        hint="Becomes go/<name>. Lowercase letters, digits and hyphens."
        value={draft.slug}
        onChange={(event) => updateField("slug", event.target.value)}
        error={errors.slug}
        required
        autoComplete="off"
        autoCapitalize="none"
        spellCheck={false}
        autoFocus={initialSlug === ""}
      />
      <TextField
        ref={targetUrlRef}
        name="target_url"
        type="url"
        label="Destination URL"
        placeholder="https://"
        value={draft.target_url}
        onChange={(event) => updateField("target_url", event.target.value)}
        error={errors.target_url}
        required
        autoFocus={initialSlug !== ""}
      />
      <TextField
        ref={descriptionRef}
        name="description"
        label="Description (optional)"
        hint={`What's behind the link, in up to ${MAX_DESCRIPTION_LENGTH} characters.`}
        value={draft.description}
        onChange={(event) => updateField("description", event.target.value)}
        error={errors.description}
      />
      <div className={styles.actions}>
        <button type="submit" className={buttons.primary} disabled={createLink.isPending}>
          {createLink.isPending ? "Creating…" : "Create link"}
        </button>
      </div>
    </form>
  );
}

function isLinkField(field: string): field is LinkField {
  return (LINK_FIELDS as readonly string[]).includes(field);
}

function fieldErrorsFrom(details: FieldError[]): FieldErrors {
  const errors: FieldErrors = {};
  for (const { field, message } of details) {
    if (isLinkField(field)) {
      errors[field] = message;
    }
  }
  return errors;
}
