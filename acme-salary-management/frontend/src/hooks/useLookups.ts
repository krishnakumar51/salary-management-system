import { useQuery } from "@tanstack/react-query";

import { lookupsApi } from "@/services/endpoints";

export function useLookups() {
  return useQuery({ queryKey: ["lookups"], queryFn: lookupsApi.get, staleTime: 5 * 60_000 });
}
