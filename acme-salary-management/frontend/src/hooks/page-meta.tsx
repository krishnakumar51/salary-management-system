import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export interface Crumb {
  label: string;
  to?: string;
}
interface Meta {
  title: string;
  crumbs: Crumb[];
}
interface Ctx {
  meta: Meta;
  setMeta: (m: Meta) => void;
}

const PageMetaContext = createContext<Ctx>({ meta: { title: "", crumbs: [] }, setMeta: () => {} });

export function PageMetaProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta>({ title: "", crumbs: [] });
  const value = useMemo(() => ({ meta, setMeta }), [meta]);
  return <PageMetaContext.Provider value={value}>{children}</PageMetaContext.Provider>;
}

export function usePageMetaValue() {
  return useContext(PageMetaContext).meta;
}

/** Pages call this to set the title/breadcrumbs shown in the top bar. */
export function usePageMeta(title: string, crumbs: Crumb[] = []) {
  const { setMeta } = useContext(PageMetaContext);
  const key = JSON.stringify(crumbs);
  useEffect(() => {
    setMeta({ title, crumbs: JSON.parse(key) as Crumb[] });
    document.title = `${title} · ACME Salary Management`;
  }, [title, key, setMeta]);
}
