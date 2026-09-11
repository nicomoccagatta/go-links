import { GO_BASE_URL } from "../config";

// Mirrors the API's rules for instant feedback; the server stays the source of truth.
const SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$/;
const RESERVED_SLUGS = new Set(["api", "healthz", "metrics", "docs", "redoc", "static"]);
const ALLOWED_PROTOCOLS = new Set(["http:", "https:"]);
const MAX_URL_LENGTH = 2048;
export const MAX_DESCRIPTION_LENGTH = 280;

export type LinkDraft = { slug: string; target_url: string; description: string };
export type LinkField = keyof LinkDraft;
export type FieldErrors = Partial<Record<LinkField, string>>;

export const LINK_FIELDS: readonly LinkField[] = ["slug", "target_url", "description"];

export function normalizeSlug(slug: string): string {
  return slug.trim().toLowerCase();
}

export function validateLink(draft: LinkDraft): FieldErrors {
  const errors: FieldErrors = {};
  const slugError = validateSlug(normalizeSlug(draft.slug));
  const targetUrlError = validateTargetUrl(draft.target_url);
  if (slugError) errors.slug = slugError;
  if (targetUrlError) errors.target_url = targetUrlError;
  if (draft.description.length > MAX_DESCRIPTION_LENGTH) {
    errors.description = `Keep it under ${MAX_DESCRIPTION_LENGTH} characters.`;
  }
  return errors;
}

function validateSlug(slug: string): string | undefined {
  if (!SLUG_PATTERN.test(slug)) {
    return "Use 1-64 lowercase letters, digits or hyphens, not starting or ending with a hyphen.";
  }
  if (RESERVED_SLUGS.has(slug)) {
    return `go/${slug} is reserved.`;
  }
  return undefined;
}

function validateTargetUrl(value: string): string | undefined {
  if (value.length > MAX_URL_LENGTH) {
    return `URLs can be at most ${MAX_URL_LENGTH} characters.`;
  }
  const url = URL.parse(value);
  const isWebUrl = url !== null && ALLOWED_PROTOCOLS.has(url.protocol) && url.hostname !== "";
  const hasWhitespace = /\s/.test(value);
  if (url === null || !isWebUrl || hasWhitespace) {
    return "Enter an absolute http(s) URL, like https://example.com/page.";
  }
  if (url.hostname === new URL(GO_BASE_URL).hostname) {
    return "Can't point at go links itself: it would redirect in a loop.";
  }
  return undefined;
}
