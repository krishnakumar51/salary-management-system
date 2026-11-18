import { PageHeader } from "@/components/common";
import { AnalyticsView } from "@/features/analytics/AnalyticsView";
import { usePageMeta } from "@/hooks/page-meta";

export default function AnalyticsPage() {
  usePageMeta("Analytics", [{ label: "Analytics" }]);
  return (
    <>
      <PageHeader title="Compensation analytics" description="How ACME pays its workforce, compared on one reporting currency." />
      <AnalyticsView />
    </>
  );
}
