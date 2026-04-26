import { siteContact } from "@/lib/storefront-content";

export const pharmacyComplianceItems = [
  {
    label: "Drug license",
    value: siteContact.pharmacyLicenseNumber
  },
  {
    label: "Licensing authority",
    value: siteContact.pharmacyLicenseAuthority
  },
  {
    label: "Licensed address",
    value: siteContact.pharmacyLicenseAddress
  },
  {
    label: "Pharmacist in charge",
    value: siteContact.pharmacistInCharge
  },
  {
    label: "Registration",
    value: siteContact.pharmacistRegistrationNumber
  }
] as const;
