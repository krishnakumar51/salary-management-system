import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";

import { Input } from "@/components/ui/form";
import { useDebouncedValue } from "@/hooks/useDebounce";
import { employeesApi } from "@/services/endpoints";

export interface PickedManager {
  id: number;
  label: string;
}

/** Search-as-you-type manager selector backed by the employee search API. */
export function ManagerPicker({
  id,
  value,
  excludeId,
  onChange,
}: {
  id: string;
  value: PickedManager | null;
  excludeId?: number;
  onChange: (m: PickedManager | null) => void;
}) {
  const [text, setText] = useState("");
  const debounced = useDebouncedValue(text.trim(), 250);
  const { data } = useQuery({
    queryKey: ["manager-search", debounced],
    queryFn: () =>
      employeesApi.list({ q: debounced, status: "active", currency: "USD", sort: "name", order: "asc", page: 1, page_size: 6 }),
    enabled: debounced.length >= 2,
  });

  if (value) {
    return (
      <div className="flex h-9 items-center justify-between rounded-lg border border-line-strong bg-surface px-3 text-sm shadow-card">
        <span>{value.label}</span>
        <button type="button" aria-label="Remove manager" className="text-ink-faint hover:text-ink" onClick={() => onChange(null)}>
          <X className="size-4" />
        </button>
      </div>
    );
  }
  const results = (data?.items ?? []).filter((e) => e.id !== excludeId);
  return (
    <div className="relative">
      <Input id={id} autoComplete="off" placeholder="Search by name, ID or email" value={text} onChange={(e) => setText(e.target.value)} />
      {debounced.length >= 2 && data && (
        <ul role="listbox" aria-label="Manager results" className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-line bg-surface shadow-pop">
          {results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-ink-faint">No matching active employees</li>
          ) : (
            results.map((e) => (
              <li key={e.id} role="option" aria-selected={false}>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-canvas"
                  onClick={() => {
                    onChange({ id: e.id, label: `${e.full_name} (${e.employee_code})` });
                    setText("");
                  }}
                >
                  {e.full_name} <span className="text-ink-faint">· {e.employee_code} · {e.designation}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
