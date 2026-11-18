import { api } from "@/services/api";
import type {
  Compensation,
  CompensationListItem,
  CompensationUpdate,
  Conversion,
  Currency,
  CurrencyBreakdown,
  Dashboard,
  Distribution,
  EmployeeCreateInput,
  EmployeeDetail,
  EmployeeInput,
  EmployeeListItem,
  EmployeeQuery,
  ExchangeRate,
  ExchangeRateInput,
  GroupAnalytics,
  IncrementPreview,
  IncrementRequest,
  Lookups,
  Page,
  SalaryHistoryEntry,
  TokenResponse,
  Trends,
  User,
} from "@/types/api";

export const authApi = {
  login: (email: string, password: string) => api.post<TokenResponse>("/auth/login", { email, password }),
  me: () => api.get<User>("/auth/me"),
};

export const lookupsApi = { get: () => api.get<Lookups>("/lookups") };

export const employeesApi = {
  list: (q: EmployeeQuery) => api.get<Page<EmployeeListItem>>("/employees", { ...q }),
  get: (id: number | string) => api.get<EmployeeDetail>(`/employees/${id}`),
  create: (body: EmployeeCreateInput) => api.post<EmployeeDetail>("/employees", body),
  update: (id: number | string, body: Partial<EmployeeInput>) => api.patch<EmployeeDetail>(`/employees/${id}`, body),
  history: (id: number | string) => api.get<SalaryHistoryEntry[]>(`/employees/${id}/salary-history`),
};

export const compensationApi = {
  list: (p: { q?: string; currency?: string; department_id?: string; page: number; page_size: number }) =>
    api.get<Page<CompensationListItem>>("/compensation", p),
  create: (body: {
    employee_id: number;
    amount: string;
    currency: Currency;
    frequency: string;
    effective_date: string;
    reason: string;
  }) => api.post<Compensation>("/compensation", body),
  update: (id: number, body: CompensationUpdate) => api.patch<Compensation>(`/compensation/${id}`, body),
  previewIncrement: (id: number, body: IncrementRequest) =>
    api.post<IncrementPreview>(`/compensation/${id}/increment/preview`, body),
  increment: (id: number, body: IncrementRequest) => api.post<Compensation>(`/compensation/${id}/increment`, body),
};

export const analyticsApi = {
  dashboard: (currency: Currency) => api.get<Dashboard>("/analytics/dashboard", { currency }),
  departments: (currency: Currency) => api.get<GroupAnalytics>("/analytics/departments", { currency }),
  countries: (currency: Currency) => api.get<GroupAnalytics>("/analytics/countries", { currency }),
  distribution: (currency: Currency, p: { department_id?: string; country_id?: string } = {}) =>
    api.get<Distribution>("/analytics/distribution", { currency, ...p }),
  trends: (currency: Currency) => api.get<Trends>("/analytics/trends", { currency }),
  currencies: (currency: Currency) => api.get<CurrencyBreakdown>("/analytics/currencies", { currency }),
};

export const ratesApi = {
  list: () => api.get<ExchangeRate[]>("/exchange-rates"),
  create: (body: ExchangeRateInput) => api.post<ExchangeRate>("/exchange-rates", body),
  convert: (amount: string, from: Currency, to: Currency) =>
    api.get<Conversion>("/exchange-rates/convert", { amount, from_currency: from, to_currency: to }),
};
