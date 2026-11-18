import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IncrementDialog } from "@/features/compensation/IncrementDialog";
import { ApiError } from "@/services/api";
import { compensationApi } from "@/services/endpoints";
import { renderWithProviders } from "@/test/utils";
import type { Compensation } from "@/types/api";

vi.mock("@/services/endpoints", () => ({ compensationApi: { increment: vi.fn() } }));
const increment = vi.mocked(compensationApi.increment);

const comp: Compensation = {
  id: 7,
  employee_id: 1,
  amount: "1500000.00",
  currency: "INR",
  frequency: "annual",
  effective_date: "2020-01-01",
  updated_at: "2024-01-01T00:00:00Z",
};

function setup(onOpenChange = vi.fn()) {
  renderWithProviders(<IncrementDialog compensation={comp} employeeName="Aarav Sharma" open onOpenChange={onOpenChange} />);
  return onOpenChange;
}

beforeEach(() => {
  increment.mockReset();
});

describe("IncrementDialog", () => {
  it("previews a 10% increment on INR 1,500,000 as INR 1,650,000", async () => {
    setup();
    expect(screen.getByText(/enter a value to preview/i)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/increment percentage/i), "10");
    expect(screen.getByTestId("new-salary")).toHaveTextContent(/₹\s?16,50,000\.00/);
    expect(screen.getByText(/₹\s?1,50,000\.00 \(10%\)/)).toBeInTheDocument();
  });

  it("switches to a fixed amount and previews the derived percentage", async () => {
    setup();
    await userEvent.click(screen.getByRole("radio", { name: /fixed amount/i }));
    await userEvent.type(screen.getByLabelText(/increment amount \(INR\)/i), "75000");
    expect(screen.getByTestId("new-salary")).toHaveTextContent(/₹\s?15,75,000\.00/);
    expect(screen.getByText(/\(5%\)/)).toBeInTheDocument();
  });

  it("validates before reviewing and never calls the API with bad input", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: /review increment/i }));
    expect(screen.getByText("Enter a value")).toBeInTheDocument();
    expect(screen.getByText(/give a reason/i)).toBeInTheDocument();
    expect(increment).not.toHaveBeenCalled();
  });

  it("requires explicit confirmation, then submits exactly what was reviewed", async () => {
    increment.mockResolvedValue({ ...comp, amount: "1650000.00" });
    const onOpenChange = setup();
    await userEvent.type(screen.getByLabelText(/increment percentage/i), "10");
    await userEvent.type(screen.getByLabelText(/reason/i), "Annual performance review");
    await userEvent.click(screen.getByRole("button", { name: /review increment/i }));

    // confirmation step: nothing sent yet
    expect(screen.getByText(/confirm salary increment/i)).toBeInTheDocument();
    expect(increment).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /confirm increment/i }));
    await waitFor(() => expect(increment).toHaveBeenCalledTimes(1));
    expect(increment).toHaveBeenCalledWith(
      7,
      expect.objectContaining({ type: "percentage", value: "10", reason: "Annual performance review" }),
    );
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it("shows server-side rejections and returns to the form", async () => {
    increment.mockRejectedValue(new ApiError(409, "conflict", "Compensation cannot be changed for a terminated employee."));
    setup();
    await userEvent.type(screen.getByLabelText(/increment percentage/i), "5");
    await userEvent.type(screen.getByLabelText(/reason/i), "Spot adjustment");
    await userEvent.click(screen.getByRole("button", { name: /review increment/i }));
    await userEvent.click(screen.getByRole("button", { name: /confirm increment/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/terminated employee/i);
    expect(screen.getByRole("button", { name: /review increment/i })).toBeInTheDocument();
  });
});
