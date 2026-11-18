import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Field, PasswordInput } from "@/components/ui/form";

function setup() {
  render(<Field id="pw" label="Password">{(p) => <PasswordInput {...p} defaultValue="s3cret-Pass" />}</Field>);
  return screen.getByLabelText("Password");
}

describe("PasswordInput", () => {
  it("is masked by default", () => {
    const input = setup();
    expect(input).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: "Show password" })).toHaveAttribute("aria-pressed", "false");
  });

  it("reveals and re-hides the password with the eye button, keeping the typed value", async () => {
    const input = setup();
    await userEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveValue("s3cret-Pass");
    expect(screen.getByRole("button", { name: "Hide password" })).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveValue("s3cret-Pass");
  });

  it("does not submit the surrounding form when toggled", async () => {
    let submitted = false;
    render(
      <form onSubmit={(e) => { e.preventDefault(); submitted = true; }}>
        <PasswordInput aria-label="pw" />
      </form>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(submitted).toBe(false);
  });
});
