export type Currency = "INR" | "USD" | "EUR";
export type Frequency = "annual" | "monthly" | "hourly";
export type EmployeeStatus = "active" | "on_leave" | "terminated";
export type EmploymentType = "full_time" | "part_time" | "contract" | "intern";

/** Money is always a decimal *string* from the API; never parse it into a float for arithmetic. */
export type MoneyString = string;

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Country {
  id: number;
  code: string;
  name: string;
  default_currency: Currency;
}
export interface Department {
  id: number;
  name: string;
}

export interface Compensation {
  id: number;
  employee_id: number;
  amount: MoneyString;
  currency: Currency;
  frequency: Frequency;
  effective_date: string;
  updated_at: string;
}

export interface EmployeeListItem {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  country: Country;
  department: Department;
  designation: string;
  employment_type: EmploymentType;
  status: EmployeeStatus;
  joining_date: string;
  compensation: Compensation | null;
}

export interface ManagerRef {
  id: number;
  employee_code: string;
  full_name: string;
}

export interface EmployeeDetail extends EmployeeListItem {
  phone: string | null;
  manager: ManagerRef | null;
}

export interface EmployeeInput {
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  country_id: number;
  department_id: number;
  designation: string;
  employment_type: EmploymentType;
  joining_date: string;
  status: EmployeeStatus;
  manager_id: number | null;
}
export interface EmployeeCreateInput extends EmployeeInput {
  compensation?: { amount: MoneyString; currency: Currency; frequency: Frequency } | null;
}

export interface EmployeeQuery {
  q?: string;
  department_id?: string;
  country_id?: string;
  designation?: string;
  status?: string;
  salary_min?: string;
  salary_max?: string;
  currency: Currency;
  sort: "name" | "joining_date" | "salary";
  order: "asc" | "desc";
  page: number;
  page_size: number;
}

export interface Lookups {
  countries: Country[];
  departments: Department[];
  designations: string[];
  currencies: Currency[];
  frequencies: Frequency[];
  statuses: EmployeeStatus[];
  employment_types: EmploymentType[];
}

export interface SalaryHistoryEntry {
  id: number;
  employee_id: number;
  compensation_id: number;
  change_type: "initial" | "set" | "fixed_increment" | "percentage_increment";
  previous_amount: MoneyString | null;
  new_amount: MoneyString;
  previous_currency: Currency | null;
  new_currency: Currency;
  previous_frequency: Frequency | null;
  new_frequency: Frequency;
  increment_percentage: MoneyString | null;
  increment_amount: MoneyString | null;
  effective_date: string;
  reason: string;
  changed_by: number | null;
  changed_by_name: string | null;
  created_at: string;
}

export interface CompensationListItem extends Compensation {
  employee_code: string;
  employee_name: string;
  department: string;
  country: string;
  status: EmployeeStatus;
}

export interface IncrementRequest {
  type: "percentage" | "fixed";
  value: string;
  effective_date: string;
  reason: string;
}
export interface IncrementPreview {
  previous_amount: MoneyString;
  new_amount: MoneyString;
  increment_amount: MoneyString;
  increment_percentage: MoneyString;
  currency: Currency;
  frequency: Frequency;
}
export interface CompensationUpdate {
  amount: MoneyString;
  currency?: Currency;
  frequency?: Frequency;
  effective_date: string;
  reason: string;
}

export interface ExchangeRate {
  id: number;
  base_currency: Currency;
  target_currency: Currency;
  rate: string;
  effective_date: string;
  source: string;
  created_at: string;
}
export interface ExchangeRateInput {
  base_currency: Currency;
  target_currency: Currency;
  rate: string;
  effective_date: string;
  source: string;
}
export interface Conversion {
  amount: string;
  from_currency: Currency;
  to_currency: Currency;
  converted: MoneyString;
  rate: string;
  effective_date: string | null;
}

// ---- analytics ----
export interface RateInfo {
  reporting_currency: Currency;
  as_of: string | null;
  rates: { from_currency: Currency; to_currency: Currency; rate: string; effective_date: string | null }[];
}
export interface CountItem {
  id: number | null;
  label: string;
  count: number;
}
export interface CurrencyTotal {
  currency: Currency;
  employee_count: number;
  total_annual: MoneyString;
  total_annual_reporting: MoneyString;
}
export interface GroupStats {
  id: number | null;
  label: string;
  count: number;
  average: MoneyString;
  median: MoneyString;
  minimum: MoneyString;
  maximum: MoneyString;
  p25: MoneyString;
  p75: MoneyString;
}
export interface Band {
  label: string;
  lower: MoneyString;
  upper: MoneyString | null;
  count: number;
}
export interface RecentChange {
  id: number;
  employee_id: number;
  employee_code: string;
  employee_name: string;
  change_type: string;
  previous_amount: MoneyString | null;
  new_amount: MoneyString;
  previous_currency: Currency | null;
  new_currency: Currency;
  new_frequency: Frequency;
  increment_percentage: string | null;
  effective_date: string;
}
export interface Dashboard {
  rate_info: RateInfo;
  total_employees: number;
  active_employees: number;
  employees_without_compensation: number;
  by_country: CountItem[];
  by_department: CountItem[];
  by_status: CountItem[];
  totals_by_currency: CurrencyTotal[];
  total_compensation_reporting: MoneyString;
  overall: GroupStats;
  department_extremes: GroupStats[];
  salary_bands: Band[];
  recent_changes: RecentChange[];
}
export interface GroupAnalytics {
  rate_info: RateInfo;
  groups: GroupStats[];
}
export interface Distribution {
  rate_info: RateInfo;
  bands: Band[];
}
export interface TrendPoint {
  month: string;
  changes: number;
  average_increment_percentage: string | null;
  average_new_salary_reporting: string | null;
}
export interface Trends {
  rate_info: RateInfo;
  points: TrendPoint[];
}
export interface CurrencyBreakdown {
  rate_info: RateInfo;
  items: CurrencyTotal[];
}

export interface User {
  id: number;
  email: string;
  full_name: string;
}
export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}
