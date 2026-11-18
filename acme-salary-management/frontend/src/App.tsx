import { lazy, Suspense } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppLayout } from "@/components/Layout";
import { EmptyState, LoadingState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/auth";
import LoginPage from "@/pages/LoginPage";

// Route-level code splitting keeps the initial bundle small (Recharts is the heavy part).
const OverviewPage = lazy(() => import("@/pages/OverviewPage"));
const EmployeesPage = lazy(() => import("@/pages/EmployeesPage"));
const EmployeeProfilePage = lazy(() => import("@/pages/EmployeeProfilePage"));
const EmployeeFormPage = lazy(() => import("@/pages/EmployeeFormPage"));
const CompensationPage = lazy(() => import("@/pages/CompensationPage"));
const AnalyticsPage = lazy(() => import("@/pages/AnalyticsPage"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));

function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingState label="Checking your session…" className="mx-auto max-w-md pt-24" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <AppLayout />;
}

function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you are looking for doesn't exist or has moved."
      action={
        <Button asChild variant="secondary">
          <Link to="/">Back to overview</Link>
        </Button>
      }
    />
  );
}

export default function App() {
  return (
    <Suspense fallback={<LoadingState className="mx-auto max-w-md pt-24" />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route index element={<OverviewPage />} />
          <Route path="employees" element={<EmployeesPage />} />
          <Route path="employees/new" element={<EmployeeFormPage />} />
          <Route path="employees/:id" element={<EmployeeProfilePage />} />
          <Route path="employees/:id/edit" element={<EmployeeFormPage />} />
          <Route path="compensation" element={<CompensationPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
