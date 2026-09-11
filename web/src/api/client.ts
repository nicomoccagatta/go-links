import createClient from "openapi-fetch";
import { type ApiError, networkError, toApiError } from "./errors";
import type { paths } from "./schema";

// Every queryFn and mutationFn goes through `unwrap`, so TanStack Query errors are always ApiError.
declare module "@tanstack/react-query" {
  interface Register {
    defaultError: ApiError;
  }
}

export const api = createClient<paths>({ baseUrl: "" });

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/** Resolves to the response data; throws ApiError on network failures and non-2xx responses. */
export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw networkError();
  }
  const { data, error, response } = result;
  if (!response.ok || data === undefined) {
    throw toApiError(response.status, error, response.headers.get("x-request-id"));
  }
  return data;
}
