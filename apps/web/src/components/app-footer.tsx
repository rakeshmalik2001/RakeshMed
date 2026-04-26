import type { Route } from "next";
import Link from "next/link";
import { FiMail, FiPhone } from "react-icons/fi";
import { FaCcMastercard, FaCcVisa, FaGooglePay, FaPaypal } from "react-icons/fa";
import { SiPaytm } from "react-icons/si";
import {
  footerCompanyLinks,
  footerLegalLinks,
  footerSocialLinks,
  footerTrustHighlights,
  siteContact
} from "@/lib/storefront-content";
import { pharmacyComplianceItems } from "@/lib/compliance";

export function AppFooter() {
  return (
    <footer className="footer footer-reference">
      <div className="page-shell footer-shell">
        <div className="footer-trust-grid">
          {footerTrustHighlights.map(({ title, description, Icon }) => (
            <article key={title} className="footer-trust-card">
              <span className="footer-trust-icon">
                <Icon />
              </span>
              <div>
                <strong>{title}</strong>
                <p>{description}</p>
              </div>
            </article>
          ))}
        </div>

        <div className="footer-reference-grid">
          <div className="footer-column">
            <h3>TrueCare</h3>
            <ul className="footer-link-list">
              {footerCompanyLinks.map((item) => (
                <li key={item.label}>
                  <Link href={item.href as Route}>{item.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="footer-column footer-stack-column">
            <div>
              <h3>Social</h3>
              <div className="footer-social-row">
                {footerSocialLinks.map((item) => {
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.label}
                      href={item.href as Route}
                      className="footer-social-icon"
                      aria-label={item.label}
                    >
                      <Icon />
                    </Link>
                  );
                })}
              </div>
            </div>

            <div>
              <h3>Legal</h3>
              <ul className="footer-link-list compact">
                {footerLegalLinks.map((item) => (
                  <li key={item.label}>
                    <Link href={item.href as Route}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="footer-column footer-stack-column">
            <div>
              <h3>Stay Updated</h3>
              <p className="footer-muted-copy">
                Get practical medicine savings tips, refill reminders, and health guidance in one inbox.
              </p>
              <div className="footer-subscribe-row">
                <input type="email" placeholder="Enter your email ID" className="footer-subscribe-input" />
                <button type="button" className="footer-subscribe-button">
                  Subscribe
                </button>
              </div>
            </div>

            <div className="footer-detail-block">
              <h3>Registered Office Address</h3>
              <p className="footer-detail-strong">{siteContact.officeName}</p>
              <p className="footer-muted-copy">{siteContact.officeAddress}</p>
              <p className="footer-muted-copy">CIN: {siteContact.cin}</p>
              <p className="footer-detail-line">Telephone: {siteContact.phone}</p>
            </div>

            <div className="footer-detail-block">
              <h3>Grievance Officer</h3>
              <p className="footer-muted-copy">Name: {siteContact.grievanceOfficer}</p>
              <p className="footer-detail-line">Email: {siteContact.grievanceEmail}</p>
            </div>

            <div className="footer-detail-block">
              <h3>Pharmacy Compliance</h3>
              {pharmacyComplianceItems.map((item) => (
                <p key={item.label} className="footer-muted-copy">
                  {item.label}: {item.value}
                </p>
              ))}
            </div>
          </div>

          <div className="footer-column footer-stack-column">
            <div>
              <h3>Download TrueCare</h3>
              <p className="footer-detail-strong">Manage medicines, prescriptions, and refills in one calmer flow.</p>
              <p className="footer-muted-copy">
                Access your cart, uploads, support history, and substitute savings faster from the app.
              </p>
              <div className="footer-store-row">
                <div className="store-badge">Get it on Google Play</div>
                <div className="store-badge">Download on the App Store</div>
              </div>
            </div>

            <div className="footer-detail-block">
              <h3>Contact Us</h3>
              <p className="footer-muted-copy">
                Our customer representative team is available {siteContact.serviceHours}.
              </p>
              <div className="footer-contact-line">
                <span>
                  <FiMail /> {siteContact.supportEmail}
                </span>
                <span>
                  <FiPhone /> {siteContact.phone}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="footer-reference-bottom">
          <div className="footer-bottom-left">
            <span className="footer-copyright-badge">TC</span>
            <p>
              2026 - TrueCare | All rights reserved. Our content is for informational purposes only.
              <Link href="/privacy"> See additional information.</Link>
            </p>
          </div>

          <div className="footer-trust-badge">CARE FIRST</div>

          <div className="footer-payment-group">
            <span>Our Payment Partners</span>
            <div className="footer-payment-icons">
              <FaCcVisa />
              <FaCcMastercard />
              <FaPaypal />
              <SiPaytm />
              <FaGooglePay />
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
