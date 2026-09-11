/** Where go/<slug> resolves: the API's redirect endpoint, not this SPA. */
export const GO_BASE_URL = import.meta.env.VITE_GO_BASE_URL ?? "http://localhost:8000";

export function goLinkHref(slug: string): string {
  return `${GO_BASE_URL}/${slug}`;
}
