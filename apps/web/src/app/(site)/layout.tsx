import type { ReactNode } from "react";

import { AppFooter } from "@/components/app-footer";
import { AppHeader } from "@/components/app-header";

export default function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <AppHeader />
      {children}
      <AppFooter />
    </>
  );
}
