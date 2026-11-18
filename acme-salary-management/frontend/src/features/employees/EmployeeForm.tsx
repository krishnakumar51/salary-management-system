import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { InlineAlert } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/form";
import { ManagerPicker, type PickedManager } from "@/features/employees/ManagerPicker";
import { useLookups } from "@/hooks/useLookups";
import { CURRENCY_LIST, EMPLOYMENT_LABEL, STATUS_LABEL } from "@/lib/format";
import { hasErrors, validateEmployee, type EmployeeFormValues, type Errors } from "@/lib/validation";
import { ApiError } from "@/services/api";
import { employeesApi } from "@/services/endpoints";
import type { Currency, EmployeeDetail, EmployeeInput } from "@/types/api";

export function toFormValues(e?: EmployeeDetail): EmployeeFormValues {
  return {
    first_name: e?.first_name ?? "",
    last_name: e?.last_name ?? "",
    email: e?.email ?? "",
    phone: e?.phone ?? "",
    country_id: e ? String(e.country.id) : "",
    department_id: e ? String(e.department.id) : "",
    designation: e?.designation ?? "",
    employment_type: e?.employment_type ?? "full_time",
    joining_date: e?.joining_date ?? "",
    status: e?.status ?? "active",
    manager_id: e?.manager ? String(e.manager.id) : "",
    amount: "",
    currency: "USD",
    frequency: "annual",
  };
}

export function EmployeeForm({ employee }: { employee?: EmployeeDetail }) {
  const editing = !!employee;
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: lookups } = useLookups();
  const [values, setValues] = useState<EmployeeFormValues>(() => toFormValues(employee));
  const [manager, setManager] = useState<PickedManager | null>(
    employee?.manager ? { id: employee.manager.id, label: `${employee.manager.full_name} (${employee.manager.employee_code})` } : null,
  );
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);

  const set = <K extends keyof EmployeeFormValues>(k: K, v: EmployeeFormValues[K]) => {
    setValues((prev) => ({ ...prev, [k]: v }));
    if (errors[k]) setErrors((prev) => ({ ...prev, [k]: "" }));
  };

  const onCountry = (countryId: string) => {
    set("country_id", countryId);
    const c = lookups?.countries.find((x) => String(x.id) === countryId);
    if (c && !editing) set("currency", c.default_currency);
  };

  const mutation = useMutation({
    mutationFn: async () => {
      const base: EmployeeInput = {
        first_name: values.first_name.trim(),
        last_name: values.last_name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim() || null,
        country_id: Number(values.country_id),
        department_id: Number(values.department_id),
        designation: values.designation.trim(),
        employment_type: values.employment_type,
        joining_date: values.joining_date,
        status: values.status,
        manager_id: manager?.id ?? null,
      };
      if (employee) return employeesApi.update(employee.id, base);
      return employeesApi.create({
        ...base,
        compensation: values.amount.trim()
          ? { amount: values.amount.trim(), currency: values.currency, frequency: values.frequency }
          : null,
      });
    },
    onSuccess: async (saved) => {
      await qc.invalidateQueries();
      navigate(`/employees/${saved.id}`);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setFormError(err.status === 422 || err.status === 409 ? err.message : err.message);
        setErrors(err.fieldErrors());
      } else setFormError("Something went wrong while saving.");
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const errs = validateEmployee(values, { creating: !editing });
    setErrors(errs);
    setFormError(null);
    if (hasErrors(errs)) {
      setFormError("Please fix the highlighted fields.");
      return;
    }
    mutation.mutate();
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-6">
      {formError && <InlineAlert>{formError}</InlineAlert>}

      <Card>
        <CardHeader title="Personal & contact" />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field id="first_name" label="First name" error={errors.first_name} required>
            {(p) => <Input {...p} autoComplete="given-name" value={values.first_name} onChange={(e) => set("first_name", e.target.value)} />}
          </Field>
          <Field id="last_name" label="Last name" error={errors.last_name} required>
            {(p) => <Input {...p} autoComplete="family-name" value={values.last_name} onChange={(e) => set("last_name", e.target.value)} />}
          </Field>
          <Field id="email" label="Work email" error={errors.email} required>
            {(p) => <Input {...p} type="email" value={values.email} onChange={(e) => set("email", e.target.value)} />}
          </Field>
          <Field id="phone" label="Phone" error={errors.phone} hint="Include the country code, e.g. +91 98765 43210">
            {(p) => <Input {...p} type="tel" value={values.phone} onChange={(e) => set("phone", e.target.value)} />}
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Role" />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field id="country_id" label="Country" error={errors.country_id} required>
            {(p) => (
              <Select {...p} value={values.country_id} onChange={(e) => onCountry(e.target.value)}>
                <option value="">Select a country</option>
                {lookups?.countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </Select>
            )}
          </Field>
          <Field id="department_id" label="Department" error={errors.department_id} required>
            {(p) => (
              <Select {...p} value={values.department_id} onChange={(e) => set("department_id", e.target.value)}>
                <option value="">Select a department</option>
                {lookups?.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </Select>
            )}
          </Field>
          <Field id="designation" label="Designation" error={errors.designation} required>
            {(p) => (
              <>
                <Input {...p} list="designation-options" value={values.designation} onChange={(e) => set("designation", e.target.value)} />
                <datalist id="designation-options">
                  {lookups?.designations.map((d) => <option key={d} value={d} />)}
                </datalist>
              </>
            )}
          </Field>
          <Field id="employment_type" label="Employment type" required>
            {(p) => (
              <Select {...p} value={values.employment_type} onChange={(e) => set("employment_type", e.target.value as EmployeeFormValues["employment_type"])}>
                {lookups?.employment_types.map((t) => <option key={t} value={t}>{EMPLOYMENT_LABEL[t]}</option>)}
              </Select>
            )}
          </Field>
          <Field id="joining_date" label="Joining date" error={errors.joining_date} required>
            {(p) => <Input {...p} type="date" value={values.joining_date} onChange={(e) => set("joining_date", e.target.value)} />}
          </Field>
          <Field id="status" label="Employment status" required>
            {(p) => (
              <Select {...p} value={values.status} onChange={(e) => set("status", e.target.value as EmployeeFormValues["status"])}>
                {lookups?.statuses.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
              </Select>
            )}
          </Field>
          <Field id="manager" label="Manager" error={errors.manager_id} className="sm:col-span-2">
            {(p) => <ManagerPicker id={p.id} value={manager} excludeId={employee?.id} onChange={setManager} />}
          </Field>
        </CardBody>
      </Card>

      {!editing && (
        <Card>
          <CardHeader title="Initial compensation" description="Optional. You can add or change it later from the employee profile." />
          <CardBody className="grid gap-4 sm:grid-cols-3">
            <Field id="amount" label="Amount" error={errors.amount}>
              {(p) => <Input {...p} inputMode="decimal" placeholder="e.g. 1500000" value={values.amount} onChange={(e) => set("amount", e.target.value)} />}
            </Field>
            <Field id="currency" label="Currency">
              {(p) => (
                <Select {...p} value={values.currency} onChange={(e) => set("currency", e.target.value as Currency)}>
                  {CURRENCY_LIST.map((c) => <option key={c}>{c}</option>)}
                </Select>
              )}
            </Field>
            <Field id="frequency" label="Pay frequency">
              {(p) => (
                <Select {...p} value={values.frequency} onChange={(e) => set("frequency", e.target.value as EmployeeFormValues["frequency"])}>
                  <option value="annual">Annual</option>
                  <option value="monthly">Monthly</option>
                  <option value="hourly">Hourly</option>
                </Select>
              )}
            </Field>
          </CardBody>
        </Card>
      )}

      <div className="flex justify-end gap-2">
        <Button variant="secondary" asChild>
          <Link to={employee ? `/employees/${employee.id}` : "/employees"}>Cancel</Link>
        </Button>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : editing ? "Save changes" : "Create employee"}
        </Button>
      </div>
    </form>
  );
}
