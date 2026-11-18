import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EmployeeForm } from "@/features/employees/EmployeeForm";
import { ApiError } from "@/services/api";
import { employeesApi, lookupsApi } from "@/services/endpoints";
import { lookups, renderWithProviders } from "@/test/utils";

vi.mock("@/services/endpoints", () => ({
  employeesApi: { create: vi.fn(), update: vi.fn(), list: vi.fn() },
  lookupsApi: { get: vi.fn() },
}));
const create = vi.mocked(employeesApi.create);

async function fillValid() {
  await screen.findByRole("option", { name: "Engineering" });
  await userEvent.type(screen.getByLabelText(/first name/i), "Aarav");
  await userEvent.type(screen.getByLabelText(/last name/i), "Sharma");
  await userEvent.type(screen.getByLabelText(/work email/i), "aarav@acme-demo.com");
  await userEvent.selectOptions(screen.getByLabelText(/country/i), "India");
  await userEvent.selectOptions(screen.getByLabelText(/department/i), "Engineering");
  await userEvent.type(screen.getByLabelText(/designation/i), "Software Engineer");
  await userEvent.type(screen.getByLabelText(/joining date/i), "2024-02-01");
}

beforeEach(() => {
  create.mockReset();
  vi.mocked(lookupsApi.get).mockResolvedValue(lookups);
});

describe("EmployeeForm validation", () => {
  it("blocks submission and explains each problem when the form is empty", async () => {
    renderWithProviders(<EmployeeForm />, { route: "/employees/new" });
    await screen.findByRole("option", { name: "Engineering" });
    await userEvent.click(screen.getByRole("button", { name: /create employee/i }));

    const messages = screen.getAllByRole("alert").map((el) => el.textContent);
    expect(messages).toEqual(
      expect.arrayContaining([
        "First name is required",
        "Last name is required",
        "Email is required",
        "Select a country",
        "Select a department",
        "Joining date is required",
      ]),
    );
    expect(screen.getByLabelText(/first name/i)).toHaveAttribute("aria-invalid", "true");
    expect(create).not.toHaveBeenCalled();
  });

  it("rejects an invalid email and a negative starting salary", async () => {
    renderWithProviders(<EmployeeForm />, { route: "/employees/new" });
    await fillValid();
    await userEvent.clear(screen.getByLabelText(/work email/i));
    await userEvent.type(screen.getByLabelText(/work email/i), "not-an-email");
    await userEvent.type(screen.getByLabelText(/^amount/i), "-100");
    await userEvent.click(screen.getByRole("button", { name: /create employee/i }));
    expect(screen.getByText(/valid email address/i)).toBeInTheDocument();
    expect(screen.getByText(/non-negative amount/i)).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  it("defaults the pay currency from the selected country", async () => {
    renderWithProviders(<EmployeeForm />, { route: "/employees/new" });
    await screen.findByRole("option", { name: "India" });
    await userEvent.selectOptions(screen.getByLabelText(/country/i), "India");
    expect(screen.getByLabelText("Currency")).toHaveValue("INR");
  });

  it("submits normalised values when valid", async () => {
    create.mockResolvedValue({ id: 99 } as never);
    renderWithProviders(<EmployeeForm />, { route: "/employees/new" });
    await fillValid();
    await userEvent.type(screen.getByLabelText(/^amount/i), "1500000");
    await userEvent.click(screen.getByRole("button", { name: /create employee/i }));
    await waitFor(() => expect(create).toHaveBeenCalledTimes(1));
    expect(create.mock.calls[0][0]).toMatchObject({
      first_name: "Aarav",
      email: "aarav@acme-demo.com",
      country_id: 1,
      department_id: 10,
      phone: null,
      manager_id: null,
      compensation: { amount: "1500000", currency: "INR", frequency: "annual" },
    });
  });

  it("maps a server 'email already exists' error onto the email field", async () => {
    create.mockRejectedValue(
      new ApiError(409, "conflict", "An employee with this email already exists.", [{ field: "email", message: "Already in use" }]),
    );
    renderWithProviders(<EmployeeForm />, { route: "/employees/new" });
    await fillValid();
    await userEvent.click(screen.getByRole("button", { name: /create employee/i }));
    expect(await screen.findByText("Already in use")).toBeInTheDocument();
    expect(screen.getByText("An employee with this email already exists.")).toBeInTheDocument();
    expect(screen.getByLabelText(/work email/i)).toHaveAttribute("aria-invalid", "true");
  });
});
