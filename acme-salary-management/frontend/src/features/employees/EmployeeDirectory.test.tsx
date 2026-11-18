import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EmployeeDirectory } from "@/features/employees/EmployeeDirectory";
import { ApiError } from "@/services/api";
import { employeesApi, lookupsApi } from "@/services/endpoints";
import { lookups, makeEmployee, makePage, renderWithProviders } from "@/test/utils";

vi.mock("@/services/endpoints", () => ({
  employeesApi: { list: vi.fn() },
  lookupsApi: { get: vi.fn() },
}));

const list = vi.mocked(employeesApi.list);
const lastQuery = () => list.mock.calls.at(-1)![0];

beforeEach(() => {
  list.mockReset();
  vi.mocked(lookupsApi.get).mockResolvedValue(lookups);
  list.mockResolvedValue(makePage([makeEmployee(1), makeEmployee(2, { status: "on_leave", full_name: "Asha Rao" })]));
});

describe("EmployeeDirectory rendering", () => {
  it("shows a loading state, then the employees with pay in the original currency", async () => {
    renderWithProviders(<EmployeeDirectory />);
    expect(screen.getByRole("status", { name: /loading employees/i })).toBeInTheDocument();

    expect(await screen.findByText("First1 Last1")).toBeInTheDocument();
    expect(screen.getByText("Asha Rao")).toBeInTheDocument();
    expect(screen.getAllByText(/₹\s?15,00,000 \/yr/)[0]).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getByText("On leave")).toBeInTheDocument();
    expect(screen.getByText(/Showing/)).toHaveTextContent("Showing 1–2 of 2");
  });

  it("requests the first page with defaults and the reporting currency", async () => {
    renderWithProviders(<EmployeeDirectory />);
    await screen.findByText("First1 Last1");
    expect(lastQuery()).toMatchObject({ page: 1, page_size: 25, sort: "name", order: "asc", currency: "USD" });
  });

  it("shows an error state with a working retry", async () => {
    list.mockRejectedValueOnce(new ApiError(500, "internal_error", "Database unavailable"));
    renderWithProviders(<EmployeeDirectory />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");

    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("First1 Last1")).toBeInTheDocument();
  });

  it("shows an empty state and offers to clear filters when nothing matches", async () => {
    list.mockResolvedValue(makePage([], { total: 0 }));
    renderWithProviders(<EmployeeDirectory />, { route: "/employees?status=terminated" });
    expect(await screen.findByText(/no employees match/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /clear all filters/i }).length).toBeGreaterThan(0);
  });
});

describe("EmployeeDirectory search and filters (server-side)", () => {
  it("sends the search term to the API after the user stops typing", async () => {
    renderWithProviders(<EmployeeDirectory />);
    await screen.findByText("First1 Last1");
    list.mockClear();

    await userEvent.type(screen.getByLabelText("Search"), "asha");
    // debounced: not called per keystroke
    expect(list).not.toHaveBeenCalled();
    await waitFor(() => expect(lastQuery().q).toBe("asha"), { timeout: 2000 });
    expect(list.mock.calls.length).toBe(1);
  });

  it("filters by department, country, designation and status", async () => {
    renderWithProviders(<EmployeeDirectory />);
    await screen.findByText("First1 Last1");
    await screen.findByRole("option", { name: "Sales" }); // lookups loaded

    await userEvent.selectOptions(screen.getByLabelText("Department"), "Sales");
    await waitFor(() => expect(lastQuery().department_id).toBe("11"));
    await userEvent.selectOptions(screen.getByLabelText("Country"), "United States");
    await waitFor(() => expect(lastQuery().country_id).toBe("2"));
    await userEvent.selectOptions(screen.getByLabelText("Designation"), "Account Executive");
    await waitFor(() => expect(lastQuery().designation).toBe("Account Executive"));
    await userEvent.selectOptions(screen.getByLabelText("Status"), "On leave");
    await waitFor(() => expect(lastQuery().status).toBe("on_leave"));
    expect(lastQuery()).toMatchObject({ department_id: "11", country_id: "2" });
  });

  it("sends the salary range in the reporting currency", async () => {
    renderWithProviders(<EmployeeDirectory />);
    await screen.findByText("First1 Last1");
    await userEvent.type(screen.getByLabelText(/min annual salary/i), "50000");
    await userEvent.type(screen.getByLabelText(/max annual salary/i), "90000");
    await waitFor(() => expect(lastQuery()).toMatchObject({ salary_min: "50000", salary_max: "90000", currency: "USD" }), {
      timeout: 3000,
    });
  });

  it("'Clear all filters' resets every filter and the search box", async () => {
    renderWithProviders(<EmployeeDirectory />, { route: "/employees?q=asha&department_id=11&status=active&page=3" });
    await screen.findByText("First1 Last1");
    expect(lastQuery()).toMatchObject({ q: "asha", department_id: "11", status: "active", page: 3 });

    await userEvent.click(screen.getByRole("button", { name: /clear all filters \(3\)/i }));
    await waitFor(() => {
      const q = lastQuery();
      expect(q.q).toBeUndefined();
      expect(q.department_id).toBeUndefined();
      expect(q.status).toBeUndefined();
      expect(q.page).toBe(1);
    });
    expect(screen.getByLabelText("Search")).toHaveValue("");
    expect(screen.queryByRole("button", { name: /clear all filters/i })).not.toBeInTheDocument();
  });
});

describe("EmployeeDirectory sorting and pagination", () => {
  it("sorts by salary and toggles direction", async () => {
    renderWithProviders(<EmployeeDirectory />);
    await screen.findByText("First1 Last1");
    await userEvent.click(screen.getByRole("button", { name: "Sort by Salary" }));
    await waitFor(() => expect(lastQuery()).toMatchObject({ sort: "salary", order: "desc" }));
    await userEvent.click(screen.getByRole("button", { name: "Sort by Salary" }));
    await waitFor(() => expect(lastQuery().order).toBe("asc"));
  });

  it("pages forward and back, and resets to page 1 when the page size changes", async () => {
    list.mockImplementation(async (q) => makePage([makeEmployee(q.page)], { total: 120, pages: 5, page: q.page, page_size: q.page_size }));
    renderWithProviders(<EmployeeDirectory />);
    await screen.findByText("First1 Last1");
    expect(screen.getByText(/Page 1 of 5/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("First2 Last2")).toBeInTheDocument();
    expect(lastQuery().page).toBe(2);
    expect(screen.getByText(/Showing/)).toHaveTextContent("Showing 26–50 of 120");

    await userEvent.click(screen.getByRole("button", { name: "Previous page" }));
    await waitFor(() => expect(lastQuery().page).toBe(1));

    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    await screen.findByText("First2 Last2");
    await userEvent.selectOptions(screen.getByLabelText("Rows per page"), "50");
    await waitFor(() => expect(lastQuery()).toMatchObject({ page: 1, page_size: 50 }));
  });

  it("disables 'Next' on the last page", async () => {
    list.mockResolvedValue(makePage([makeEmployee(9)], { total: 51, pages: 3, page: 3 }));
    renderWithProviders(<EmployeeDirectory />, { route: "/employees?page=3" });
    await screen.findByText("First9 Last9");
    const nav = screen.getByText(/Page 3 of 3/).parentElement!;
    expect(within(nav).getByRole("button", { name: "Next page" })).toBeDisabled();
  });
});
