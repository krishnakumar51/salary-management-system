import {
  BarChart3,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  Settings,
  Users,
  Wallet,
  X,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Select } from "@/components/ui/form";
import { useAuth } from "@/hooks/auth";
import { usePageMetaValue } from "@/hooks/page-meta";
import { useReportingCurrency } from "@/hooks/reporting-currency";
import { CURRENCY_LIST } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Currency } from "@/types/api";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/employees", label: "Employees", icon: Users },
  { to: "/compensation", label: "Compensation", icon: Wallet },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
];

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5 px-2">
      <span className="grid size-8 place-items-center rounded-lg bg-brand-600 text-white shadow-card">
        <svg viewBox="0 0 32 32" className="size-5" aria-hidden>
          <path d="M9 22 16 9l7 13h-4l-3-6-3 6z" fill="currentColor" />
        </svg>
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold text-ink">ACME</span>
        <span className="block text-[11px] text-ink-faint">Salary Management</span>
      </span>
    </Link>
  );
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="mt-8 flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive ? "bg-brand-50 text-brand-700" : "text-ink-soft hover:bg-canvas hover:text-ink",
            )
          }
        >
          <Icon className="size-[18px]" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

function Topbar({ onMenu }: { onMenu: () => void }) {
  const meta = usePageMetaValue();
  const { user, logout } = useAuth();
  const { currency, setCurrency } = useReportingCurrency();
  const navigate = useNavigate();
  const [term, setTerm] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    navigate(`/employees${term.trim() ? `?q=${encodeURIComponent(term.trim())}` : ""}`);
  };
  const initials = (user?.full_name ?? "?")
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-30 flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line bg-surface/90 px-4 py-3 backdrop-blur sm:px-6 lg:px-8">
      <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation" onClick={onMenu}>
        <Menu />
      </Button>
      <div className="min-w-0 flex-1 basis-40">
        {meta.crumbs.length > 0 && (
          <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-ink-faint">
            {meta.crumbs.map((c, i) => (
              <span key={`${c.label}-${i}`} className="flex items-center gap-1">
                {i > 0 && <ChevronRight className="size-3" />}
                {c.to ? (
                  <Link to={c.to} className="hover:text-ink">
                    {c.label}
                  </Link>
                ) : (
                  <span aria-current="page">{c.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <p className="truncate text-sm font-semibold text-ink">{meta.title}</p>
      </div>

      <form role="search" onSubmit={submit} className="relative order-last w-full sm:order-none sm:w-64">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" />
        <input
          type="search"
          aria-label="Search employees"
          placeholder="Search name, ID or email…"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          className="h-9 w-full rounded-lg border border-line-strong bg-canvas pl-9 pr-3 text-sm placeholder:text-ink-faint focus-visible:border-brand-500 focus-visible:bg-surface"
        />
      </form>

      <label className="flex items-center gap-2 text-xs text-ink-faint">
        <span className="hidden md:inline">Reporting currency</span>
        <Select
          aria-label="Reporting currency"
          className="h-9 w-24"
          value={currency}
          onChange={(e) => setCurrency(e.target.value as Currency)}
        >
          {CURRENCY_LIST.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </Select>
      </label>

      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="Account menu"
          className="flex items-center gap-2 rounded-full p-0.5 hover:ring-2 hover:ring-line"
        >
          <span className="grid size-8 place-items-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
            {initials}
          </span>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuLabel>
            <p className="text-sm font-medium text-ink">{user?.full_name}</p>
            <p className="text-xs text-ink-faint">{user?.email}</p>
            <p className="mt-1 text-xs text-ink-faint">HR Manager</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => navigate("/settings")}>
            <Settings /> Settings
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={() => {
              logout();
              navigate("/login");
            }}
          >
            <LogOut /> Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}

export function AppLayout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  return (
    <div className="flex h-full">
      <aside className="hidden w-60 shrink-0 border-r border-line bg-surface px-3 py-5 lg:block">
        <Logo />
        <SidebarNav />
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button className="absolute inset-0 bg-ink/40" aria-label="Close navigation" onClick={() => setOpen(false)} />
          <aside className="relative h-full w-64 bg-surface px-3 py-5 shadow-pop">
            <Button variant="ghost" size="icon" className="absolute right-2 top-2" aria-label="Close navigation" onClick={() => setOpen(false)}>
              <X />
            </Button>
            <Logo />
            <SidebarNav onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        <Topbar onMenu={() => setOpen(true)} />
        <main key={location.pathname} className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
