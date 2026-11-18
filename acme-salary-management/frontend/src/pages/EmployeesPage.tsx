import { Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { EmployeeDirectory } from "@/features/employees/EmployeeDirectory";
import { usePageMeta } from "@/hooks/page-meta";

export default function EmployeesPage() {
  usePageMeta("Employees", [{ label: "Employees" }]);
  return (
    <>
      <PageHeader
        title="Employees"
        description="Search, filter and manage everyone at ACME."
        actions={
          <Button asChild>
            <Link to="/employees/new">
              <Plus /> Add employee
            </Link>
          </Button>
        }
      />
      <EmployeeDirectory />
    </>
  );
}
