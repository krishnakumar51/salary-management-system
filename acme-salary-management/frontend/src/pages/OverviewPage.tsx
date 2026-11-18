import { PageHeader } from "@/components/common";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { usePageMeta } from "@/hooks/page-meta";

export default function OverviewPage() {
  usePageMeta("Overview", [{ label: "Overview" }]);
  return (
    <>
      <PageHeader title="Overview" description="How ACME's workforce and compensation look right now." />
      <Dashboard />
    </>
  );
}
