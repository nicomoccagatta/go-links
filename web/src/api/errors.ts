import type { components } from "./schema";

export type FieldError = components["schemas"]["ErrorDetail"];

type ApiErrorInit = {
  status: number;
  code: string;
  message: string;
  requestId: string | null;
  details: FieldError[];
};

/** Every failed API call surfaces as this, whether or not the server answered with our envelope. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: FieldError[];

  constructor({ status, code, message, requestId, details }: ApiErrorInit) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

/**
 * Parses `{ error: { code, message, request_id, details? } }`. Anything else (a proxy's HTML
 * error page, an empty body) becomes a generic error that still carries the header request ID.
 */
export function toApiError(
  status: number,
  body: unknown,
  headerRequestId: string | null,
): ApiError {
  const error = isRecord(body) ? body.error : undefined;
  if (!isRecord(error)) {
    return unexpectedResponse(status, headerRequestId);
  }
  const { code, message, request_id: requestId, details } = error;
  if (typeof code !== "string" || typeof message !== "string") {
    return unexpectedResponse(status, headerRequestId);
  }
  return new ApiError({
    status,
    code,
    message,
    requestId: typeof requestId === "string" ? requestId : headerRequestId,
    details: Array.isArray(details) ? details.filter(isFieldError) : [],
  });
}

export function networkError(): ApiError {
  return new ApiError({
    status: 0,
    code: "network_error",
    message: "Couldn't reach the server. Check your connection and try again.",
    requestId: null,
    details: [],
  });
}

function unexpectedResponse(status: number, requestId: string | null): ApiError {
  return new ApiError({
    status,
    code: "unexpected_response",
    message: `Unexpected response from the server (HTTP ${status}).`,
    requestId,
    details: [],
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isFieldError(value: unknown): value is FieldError {
  return isRecord(value) && typeof value.field === "string" && typeof value.message === "string";
}
