import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { PageHeader } from "@/components/common";
import { ErrorState, LoadingState } from "@/components/states";
import { Card } from "@/components/ui/card";
import { EmployeeForm } from "@/features/employees/EmployeeForm";
import { usePageMeta } from "@/hooks/page-meta";
import { employeesApi } from "@/services/endpoints";

export default function EmployeeFormPage() {
  const { id } = useParams();
  const editing = id !== undefined;
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["employee", id],
    queryFn: () => employeesApi.get(id!),
    enabled: editing,
  });
  usePageMeta(editing ? "Edit employee" : "New employee", [
    { label: "Employees", to: "/employees" },
    ...(editing && data ? [{ label: data.full_name, to: `/employees/${data.id}` }] : []),
    { label: editing ? "Edit" : "New" },
  ]);

  if (editing && isLoading) return <LoadingState />;
  if (editing && (isError || !data)) {
    return (
      <Card>
        <ErrorState error={error} onRetry={() => refetch()} />
      </Card>
    );
  }
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title={editing ? `Edit ${data!.full_name}` : "Add employee"}
        description={editing ? "Update profile details. Compensation is managed from the profile page." : "Create an employee record, optionally with their starting compensation."}
      />
      <EmployeeForm employee={data} />
    </div>
  );
}
