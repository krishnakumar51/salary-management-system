import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";

import { ReportingCurrencyProvider } from "@/hooks/reporting-currency";
import type { EmployeeListItem, Lookups, Page } from "@/types/api";

export function renderWithProviders(ui: ReactElement, { route = "/employees" }: { route?: string } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <ReportingCurrencyProvider initialCurrency="USD">
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </ReportingCurrencyProvider>
    </QueryClientProvider>,
  );
}

export const lookups: Lookups = {
  countries: [
    { id: 1, code: "IN", name: "India", default_currency: "INR" },
    { id: 2, code: "US", name: "United States", default_currency: "USD" },
  ],
  departments: [
    { id: 10, name: "Engineering" },
    { id: 11, name: "Sales" },
  ],
  designations: ["Software Engineer", "Account Executive"],
  currencies: ["INR", "USD", "EUR"],
  frequencies: ["annual", "monthly", "hourly"],
  statuses: ["active", "on_leave", "terminated"],
  employment_types: ["full_time", "part_time", "contract", "intern"],
};

export function makeEmployee(n: number, over: Partial<EmployeeListItem> = {}): EmployeeListItem {
  return {
    id: n,
    employee_code: `ACME-${String(n).padStart(5, "0")}`,
    first_name: `First${n}`,
    last_name: `Last${n}`,
    full_name: `First${n} Last${n}`,
    email: `first${n}@acme-demo.com`,
    country: lookups.countries[0],
    department: lookups.departments[0],
    designation: "Software Engineer",
    employment_type: "full_time",
    status: "active",
    joining_date: "2022-03-01",
    compensation: {
      id: n,
      employee_id: n,
      amount: "1500000.00",
      currency: "INR",
      frequency: "annual",
      effective_date: "2022-03-01",
      updated_at: "2024-01-01T00:00:00Z",
    },
    ...over,
  };
}

export function makePage(items: EmployeeListItem[], over: Partial<Page<EmployeeListItem>> = {}): Page<EmployeeListItem> {
  return { items, total: items.length, page: 1, page_size: 25, pages: 1, ...over };
}
