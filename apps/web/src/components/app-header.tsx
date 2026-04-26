"use client";

import type { Route } from "next";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FiDownload, FiShoppingCart, FiUser } from "react-icons/fi";

import { useCart } from "@/components/cart-provider";
import { HeaderCategoryNav } from "@/components/header-category-nav";
import { useAuthSession } from "@/hooks/use-auth-session";
import { SiteSearchBar } from "@/components/site-search-bar";
import { headerTopbarMessages, siteContact } from "@/lib/storefront-content";

export function AppHeader() {
  const pathname = usePathname();
  const { itemCount } = useCart();
  const session = useAuthSession();
  const [showInlineSearch, setShowInlineSearch] = useState(false);
  const isHomePage = pathname === "/";

  useEffect(() => {
    if (!isHomePage) {
      setShowInlineSearch(false);
      return;
    }

    function onScroll() {
      setShowInlineSearch(window.scrollY > 220);
    }

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => window.removeEventListener("scroll", onScroll);
  }, [isHomePage]);

  const isAuthenticated = session.isAuthenticated;
  const accountLabel = session.user?.full_name || "Account";

  return (
    <div className="header-wrap">
      <div className="topbar">
        <span>{headerTopbarMessages[0]}</span>
        <span>{headerTopbarMessages[1]}</span>
      </div>

      <header className={`header${isHomePage ? " header-home" : ""}`}>
        <Link href="/" className="brand">
          <span className="brand-mark">+</span>
          <span className="brand-text">
            True<span>Care</span>
          </span>
        </Link>

        <div className={`header-search-slot${showInlineSearch || !isHomePage ? " visible" : ""}`}>
          {isHomePage ? (
            showInlineSearch ? (
              <SiteSearchBar className="header-inline-search" locationLabel={siteContact.locationLabel} />
            ) : (
              <div className="header-home-gap" />
            )
          ) : (
            <SiteSearchBar className="header-inline-search" locationLabel={siteContact.locationLabel} />
          )}
        </div>

        <div className="header-actions">
          <Link href={"/download-app" as Route} className="header-icon" data-testid="header-download-link">
            <FiDownload />
            Download App
          </Link>
          <Link
            href={(isAuthenticated ? "/account" : "/login") as Route}
            className="header-icon"
            data-testid="header-account-link"
          >
            <FiUser />
            {accountLabel}
          </Link>
          <Link href={"/cart" as Route} className="header-icon" data-testid="header-cart-link">
            <FiShoppingCart />
            Cart
            <span className="header-cart-badge">{itemCount}</span>
          </Link>
        </div>
      </header>

      <HeaderCategoryNav />
    </div>
  );
}
