import { describe, expect, it } from "vite-plus/test";
import { toApiError } from "./errors";

describe("toApiError", () => {
  it("reads the error envelope", () => {
    const body = {
      error: {
        code: "slug_taken",
        message: "go/oncall already exists.",
        request_id: "req-1",
        details: [{ field: "slug", message: "go/oncall is already taken." }],
      },
    };

    expect(toApiError(409, body, "header-id")).toMatchObject({
      status: 409,
      code: "slug_taken",
      message: "go/oncall already exists.",
      requestId: "req-1",
      details: [{ field: "slug", message: "go/oncall is already taken." }],
    });
  });

  it("defaults missing details to an empty list and drops malformed ones", () => {
    const withoutDetails = { error: { code: "link_not_found", message: "Nope.", request_id: "r" } };
    const malformed = { error: { code: "validation_error", message: "Bad.", details: [{ x: 1 }] } };

    expect(toApiError(404, withoutDetails, null).details).toEqual([]);
    expect(toApiError(422, malformed, null).details).toEqual([]);
  });

  it.each([["<html>Bad gateway</html>"], [null], [{ detail: "Not Found" }], [{ error: "boom" }]])(
    "falls back to a generic error for a non-envelope body: %j",
    (body) => {
      expect(toApiError(502, body, "header-id")).toMatchObject({
        status: 502,
        code: "unexpected_response",
        requestId: "header-id",
        details: [],
      });
    },
  );
});
