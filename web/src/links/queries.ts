import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../api/client";
import type { components } from "../api/schema";

export type Link = components["schemas"]["LinkOut"];
export type LinkCreate = components["schemas"]["LinkCreate"];

const linksKey = ["links"] as const;

export function useLinks() {
  return useQuery({
    queryKey: linksKey,
    queryFn: () => unwrap(api.GET("/api/links")),
    select: (data) => data.items,
  });
}

export function useCreateLink() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: LinkCreate) => unwrap(api.POST("/api/links", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: linksKey }),
  });
}
