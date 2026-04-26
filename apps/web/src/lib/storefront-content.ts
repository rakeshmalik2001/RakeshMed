import {
  FiFacebook,
  FiFileText,
  FiHeadphones,
  FiInstagram,
  FiLinkedin,
  FiShield,
  FiYoutube
} from "react-icons/fi";
import type { IconType } from "react-icons";

export type MarketingPageSection = {
  title: string;
  body: string;
  points?: string[];
  callout?: string;
};

export type MarketingPageCard = {
  title: string;
  body: string;
  href?: string;
  ctaLabel?: string;
};

export type MarketingPageFaq = {
  question: string;
  answer: string;
};

export type MarketingPageContent = {
  eyebrow: string;
  title: string;
  intro: string;
  highlights: Array<{
    label: string;
    value: string;
  }>;
  sections: MarketingPageSection[];
  cards?: MarketingPageCard[];
  faqs?: MarketingPageFaq[];
  cta: {
    title: string;
    body: string;
    primaryLabel: string;
    primaryHref: string;
    secondaryLabel?: string;
    secondaryHref?: string;
  };
};

export const siteContact = {
  phone: process.env.NEXT_PUBLIC_SUPPORT_PHONE ?? "09240250346",
  supportEmail: process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? "support@truecare.in",
  grievanceEmail: process.env.NEXT_PUBLIC_GRIEVANCE_EMAIL ?? "grievance@truecare.in",
  grievanceOfficer: process.env.NEXT_PUBLIC_GRIEVANCE_OFFICER ?? "Kishor Kumar",
  officeName: process.env.NEXT_PUBLIC_COMPANY_NAME ?? "TrueCare Health Services Private Limited",
  officeAddress:
    process.env.NEXT_PUBLIC_OFFICE_ADDRESS ??
    "Unit-301 & 304, Lightbridge Tunga Village, Saki Vihar Rd, Chandivali, Powai, Mumbai, Maharashtra, India, 400072.",
  cin: process.env.NEXT_PUBLIC_COMPANY_CIN ?? "U62099MH2019PTC320566",
  serviceHours: process.env.NEXT_PUBLIC_SUPPORT_HOURS ?? "7 days a week from 8:00 am - 10:00 pm",
  locationLabel: process.env.NEXT_PUBLIC_DEFAULT_LOCATION ?? "Deliver to Mumbai",
  pharmacyLicenseNumber:
    process.env.NEXT_PUBLIC_PHARMACY_LICENSE_NUMBER ?? "MH-TRC-RDL-000214 / MH-TRC-WDL-000215",
  pharmacyLicenseAuthority:
    process.env.NEXT_PUBLIC_PHARMACY_LICENSE_AUTHORITY ?? "Maharashtra Food and Drug Administration",
  pharmacyLicenseAddress:
    process.env.NEXT_PUBLIC_PHARMACY_LICENSE_ADDRESS ??
    "Licensed fulfillment and review operations coordinated from Mumbai, Maharashtra.",
  pharmacistInCharge:
    process.env.NEXT_PUBLIC_PHARMACIST_IN_CHARGE ?? "Registered Pharmacist On Duty",
  pharmacistRegistrationNumber:
    process.env.NEXT_PUBLIC_PHARMACIST_REGISTRATION_NUMBER ?? "PCI-REG-TO-BE-CONFIRMED"
} as const;

export const headerTopbarMessages = [
  `Licensed pharmacy | Regulated by ${siteContact.pharmacyLicenseAuthority} | Fast delivery where available`,
  "Upload your prescription and compare smarter substitutes"
] as const;

export const footerCompanyLinks: Array<{ label: string; href: string }> = [
  { label: "About Us", href: "/about" },
  { label: "Health Articles", href: "/blog" },
  { label: "Health Library", href: "/health-guide" },
  { label: "Diseases & Health Conditions", href: "/health-guide/diseases-and-health-conditions" },
  { label: "Understanding Generic Medicines", href: "/generic-info" },
  { label: "All Medicines", href: "/categories/medicines" },
  { label: "Need Help", href: "/contact" },
  { label: "FAQ", href: "/faq" }
];

export const footerLegalLinks: Array<{ label: string; href: string }> = [
  { label: "Terms & Conditions", href: "/terms" },
  { label: "Privacy Policy", href: "/privacy" },
  { label: "Prescription Policy", href: "/prescription-policy" },
  { label: "Serviceability", href: "/serviceability" }
];

export const footerSocialLinks: Array<{ label: string; icon: IconType; href: string }> = [
  { label: "Instagram", icon: FiInstagram, href: "/contact" },
  { label: "Facebook", icon: FiFacebook, href: "/contact" },
  { label: "YouTube", icon: FiYoutube, href: "/contact" },
  { label: "LinkedIn", icon: FiLinkedin, href: "/contact" }
];

export const footerTrustHighlights: Array<{
  title: string;
  description: string;
  Icon: IconType;
}> = [
  {
    title: "Licensed support",
    description: "Pharmacy guidance, care answers, and order help from one support flow.",
    Icon: FiHeadphones
  },
  {
    title: "Transparent savings",
    description: "Compare substitutes, understand pricing, and see where everyday savings come from.",
    Icon: FiFileText
  },
  {
    title: "Private by design",
    description: "Prescription files and health details are handled with clear privacy and review policies.",
    Icon: FiShield
  }
];

export const uploadPrescriptionContent = {
  eyebrow: "Prescription Intake",
  title: "Upload your prescription for pharmacist review",
  intro:
    "Share a clear photo or PDF of your prescription. Our team verifies the medicines, checks availability, and helps you compare substitute options where appropriate.",
  steps: [
    {
      title: "Upload",
      body: "Attach a valid prescription in image or PDF format."
    },
    {
      title: "Review",
      body: "Pharmacists validate medicines and contact you if clarification is needed."
    },
    {
      title: "Order",
      body: "Approved items move forward to cart and checkout."
    }
  ],
  beforeUpload: [
    "Keep doctor name, patient name, and medicine lines clearly visible.",
    "Accepted formats: JPG, PNG, PDF.",
    "Use a valid prescription for restricted medicines.",
    "Our team may request clarification for unreadable uploads."
  ],
  guidanceCards: [
    {
      title: "Review priorities",
      body: "We check medicine names, dosage instructions, doctor identity, and whether substitute guidance is safe."
    },
    {
      title: "When support reaches out",
      body: "If the handwriting is unclear or the file is incomplete, pharmacy support will request a sharper upload before approval."
    }
  ]
} as const;

export const marketingPageContent: Record<string, MarketingPageContent> = {
  about: {
    eyebrow: "About TrueCare",
    title: "Pharmacy support built for everyday medicine decisions",
    intro:
      "TrueCare brings pharmacy guidance, substitute comparison, prescription review, and repeat-order support into one clearer customer journey.",
    highlights: [
      { label: "Support hours", value: siteContact.serviceHours },
      { label: "Office", value: "Mumbai operations and support desk" },
      { label: "Focus", value: "Prescription review, refills, and savings clarity" },
      { label: "Pharmacy license", value: siteContact.pharmacyLicenseNumber }
    ],
    sections: [
      {
        title: "Why the experience exists",
        body:
          "People often know the medicine they need but not whether a substitute is appropriate, whether the prescription upload is sufficient, or what to do when a refill is due. TrueCare is designed to reduce that friction."
      },
      {
        title: "How the storefront helps",
        body:
          "The frontend is organized around search, product education, category browsing, and pharmacist review so customers can move from confusion to action without leaving the site.",
        points: [
          "Search for medicines and compare substitute options.",
          "Upload a prescription and let the pharmacy team validate the order.",
          "Track repeat purchases and account activity from one place."
        ]
      },
      {
        title: "Trust and compliance",
        body:
          "Support, prescription review, and customer-care flows are paired with clear legal pages, escalation details, and privacy language so customers know what happens to their data and what is required for restricted medicines.",
        callout: `${siteContact.officeName} | CIN ${siteContact.cin} | Drug license ${siteContact.pharmacyLicenseNumber}`
      }
    ],
    cards: [
      {
        title: "Prescription-first support",
        body: "Customers can start with a prescription upload instead of guessing which medicines can be ordered directly.",
        href: "/upload-prescription",
        ctaLabel: "Upload Prescription"
      },
      {
        title: "Substitute comparison",
        body: "Search and product pages are built to explain alternatives, pack sizes, and pricing more clearly.",
        href: "/search",
        ctaLabel: "Search Medicines"
      },
      {
        title: "Customer help desk",
        body: "Delivery help, account assistance, and escalations route through the same support flow.",
        href: "/contact",
        ctaLabel: "Contact Support"
      }
    ],
    faqs: [
      {
        question: "Is TrueCare a marketplace or a pharmacy support experience?",
        answer:
          "The site is positioned as a pharmacy-led storefront with prescription intake, medicine discovery, and customer-support guidance combined in one experience."
      },
      {
        question: "Can customers order prescription medicines directly?",
        answer:
          "Prescription medicines require valid review. The site guides customers to upload a prescription and receive pharmacist validation before fulfillment."
      }
    ],
    cta: {
      title: "Need help with a medicine decision?",
      body: "Search, upload a prescription, or contact support and continue from the path that fits the customer’s need.",
      primaryLabel: "Search Medicines",
      primaryHref: "/search",
      secondaryLabel: "Contact Support",
      secondaryHref: "/contact"
    }
  },
  contact: {
    eyebrow: "Customer Support",
    title: "Talk to pharmacy support, delivery help, or escalations",
    intro:
      "Use the support desk for order help, refill questions, prescription-upload issues, and escalation paths when something needs a manual review.",
    highlights: [
      { label: "Phone", value: siteContact.phone },
      { label: "Support email", value: siteContact.supportEmail },
      { label: "Hours", value: siteContact.serviceHours },
      { label: "Grievance officer", value: siteContact.grievanceOfficer }
    ],
    sections: [
      {
        title: "Support desk",
        body:
          "For medicine availability, order questions, address updates, or upload issues, the support team is the first point of contact."
      },
      {
        title: "Escalation path",
        body:
          "Privacy, grievance, or unresolved-case escalations can be directed to the grievance contact so customers do not get stuck in a general support loop.",
        points: [
          `Grievance officer: ${siteContact.grievanceOfficer}`,
          `Grievance email: ${siteContact.grievanceEmail}`,
          `Registered office: ${siteContact.officeAddress}`,
          `Retail and wholesale drug licenses: ${siteContact.pharmacyLicenseNumber}`
        ]
      },
      {
        title: "Licensed pharmacy details",
        body:
          "Customers and partners should be able to verify the operating pharmacy identity without needing to ask support for basic compliance details.",
        points: [
          `Licensing authority: ${siteContact.pharmacyLicenseAuthority}`,
          `Licensed address: ${siteContact.pharmacyLicenseAddress}`,
          `Pharmacist in charge: ${siteContact.pharmacistInCharge}`,
          `Registration reference: ${siteContact.pharmacistRegistrationNumber}`
        ]
      },
      {
        title: "Best time to reach out",
        body:
          "Customers should have the order number, prescription reference, or registered phone number ready so the team can trace the request faster."
      }
    ],
    cards: [
      {
        title: "Prescription support",
        body: "Need help with upload quality, missing pages, or pharmacist clarification?",
        href: "/upload-prescription",
        ctaLabel: "Upload Prescription"
      },
      {
        title: "Delivery and serviceability",
        body: "Check whether the delivery promise or special fulfillment applies for a location.",
        href: "/serviceability",
        ctaLabel: "View Coverage"
      },
      {
        title: "Refund or policy questions",
        body: "Legal and service policies are published clearly so support conversations can move faster.",
        href: "/faq",
        ctaLabel: "Open FAQ"
      }
    ],
    faqs: [
      {
        question: "What details should a customer share when asking for help?",
        answer:
          "An order ID, registered phone number, prescription reference, and a short summary of the issue usually make the review much faster."
      },
      {
        question: "When should a grievance be escalated?",
        answer:
          "Escalation is appropriate when privacy, unresolved service issues, or repeated failed support attempts need a formal review path."
      }
    ],
    cta: {
      title: "Start with the most relevant help flow",
      body: "Use the support desk for general help or the prescription flow if the request depends on a doctor’s note.",
      primaryLabel: "Upload Prescription",
      primaryHref: "/upload-prescription",
      secondaryLabel: "Browse FAQ",
      secondaryHref: "/faq"
    }
  },
  faq: {
    eyebrow: "Help Center",
    title: "Answers for orders, uploads, substitutes, and delivery",
    intro:
      "This help page groups the most common customer questions so the storefront has a clear self-service layer before support is needed.",
    highlights: [
      { label: "Coverage", value: "Ordering, delivery, prescription, and account help" },
      { label: "Audience", value: "Customers, caretakers, and repeat-order users" },
      { label: "Escalation", value: "Support and grievance details included" }
    ],
    sections: [
      {
        title: "Ordering and checkout",
        body:
          "Customers can add available medicines to cart, review address details, and confirm the order from their account and checkout flows."
      },
      {
        title: "Prescription and substitute review",
        body:
          "The storefront explains when an upload is required, how pharmacist review works, and when substitute comparison should be treated as a guided decision rather than a direct swap.",
        points: [
          "Restricted medicines require valid prescriptions.",
          "Unreadable files may need re-upload before approval.",
          "Substitutes should be reviewed in the context of strength, dosage form, and patient history."
        ]
      },
      {
        title: "Delivery and serviceability",
        body:
          "Delivery availability varies by location, medicine type, and operational constraints. Serviceability details help set expectations before checkout."
      }
    ],
    faqs: [
      {
        question: "Can I search first and upload the prescription later?",
        answer:
          "Yes. Customers can browse and compare first, but prescription medicines still require review before fulfillment is approved."
      },
      {
        question: "Why might an uploaded prescription be rejected?",
        answer:
          "Common reasons include unclear handwriting, missing pages, invalid dates, incomplete patient or doctor details, or restrictions tied to the requested medicine."
      },
      {
        question: "Do all medicines have the same delivery promise?",
        answer:
          "No. Delivery depends on location, serviceability, stock, and whether the order requires extra prescription validation."
      }
    ],
    cards: [
      {
        title: "Need policy details?",
        body: "Review legal, privacy, and prescription rules in full.",
        href: "/terms",
        ctaLabel: "Open Policies"
      },
      {
        title: "Still need help?",
        body: "Move from self-service to direct support if the case needs manual handling.",
        href: "/contact",
        ctaLabel: "Contact Us"
      }
    ],
    cta: {
      title: "Move from answer to action",
      body: "After reviewing the help content, continue into search, upload, or direct support without restarting the customer journey.",
      primaryLabel: "Search Medicines",
      primaryHref: "/search",
      secondaryLabel: "Contact Support",
      secondaryHref: "/contact"
    }
  },
  "download-app": {
    eyebrow: "Mobile Experience",
    title: "Keep medicine search and refill support on hand",
    intro:
      "The app page explains why customers should continue medicine discovery, prescription uploads, and repeat-order reminders from a mobile flow.",
    highlights: [
      { label: "Use case", value: "Search, refill, upload, and track" },
      { label: "Best for", value: "Repeat orders and family-care coordination" },
      { label: "Support", value: "Connected to the same TrueCare help desk" }
    ],
    sections: [
      {
        title: "Why the mobile flow matters",
        body:
          "Medicine decisions often happen away from a desktop. The app page gives customers a clear reason to continue uploads, substitute checks, and refill reminders on their phone."
      },
      {
        title: "What customers can expect",
        body:
          "The same storefront journeys can continue in a mobile-friendly format, especially for repeat purchases and prescription-led orders.",
        points: [
          "Search medicines faster from recent history.",
          "Upload prescription images directly from the camera roll.",
          "Track order progress and refill needs more easily."
        ]
      },
      {
        title: "Device and support expectations",
        body:
          "Customers should still be able to complete key flows on the website, but the app page serves as a continuation path for users who prefer mobile ordering."
      }
    ],
    cards: [
      {
        title: "Start with search",
        body: "Find the medicine first, then continue on mobile if needed.",
        href: "/search",
        ctaLabel: "Search Now"
      },
      {
        title: "Prescription-led ordering",
        body: "For prescription medicines, the upload flow remains the fastest starting point.",
        href: "/upload-prescription",
        ctaLabel: "Upload Prescription"
      }
    ],
    faqs: [
      {
        question: "Do customers need the app to place an order?",
        answer:
          "No. Core storefront flows remain available on the website. The app is a convenience layer for mobile-first repeat usage."
      }
    ],
    cta: {
      title: "Continue the storefront journey on mobile",
      body: "Use search or prescription upload as the real starting point, then move into the app experience when it is helpful.",
      primaryLabel: "Search Medicines",
      primaryHref: "/search",
      secondaryLabel: "Upload Prescription",
      secondaryHref: "/upload-prescription"
    }
  },
  "generic-info": {
    eyebrow: "Generic Medicine Education",
    title: "Understand substitutes with clearer language and safer context",
    intro:
      "This page explains why substitute discovery matters, what a customer should compare, and when pharmacist review becomes important before switching.",
    highlights: [
      { label: "Focus", value: "Composition, dosage form, and affordability" },
      { label: "Goal", value: "Better savings decisions with review context" },
      { label: "Guidance", value: "Use search plus pharmacist confirmation" }
    ],
    sections: [
      {
        title: "What a substitute comparison actually means",
        body:
          "A substitute view is not just a cheaper card on the screen. It should help customers compare formulation details, strengths, and suitability before assuming products are interchangeable."
      },
      {
        title: "What customers should compare",
        body:
          "The safest comparison is based on multiple signals rather than price alone.",
        points: [
          "Active ingredient and strength",
          "Dosage form and pack size",
          "Prescription requirement and pharmacist review",
          "Brand reputation and stock continuity"
        ]
      },
      {
        title: "When to ask for review",
        body:
          "Chronic therapies, dose-sensitive medicines, and prescription-only items deserve pharmacist review before the customer acts on a substitute suggestion."
      }
    ],
    cards: [
      {
        title: "Search for a medicine",
        body: "Use the storefront search flow to see available products and alternatives.",
        href: "/search",
        ctaLabel: "Open Search"
      },
      {
        title: "Need prescription validation?",
        body: "Upload the prescription so the pharmacy team can review the selection safely.",
        href: "/upload-prescription",
        ctaLabel: "Upload Now"
      }
    ],
    faqs: [
      {
        question: "Does a lower price always mean the medicines are equivalent?",
        answer:
          "No. Customers should compare composition, strength, formulation, and prescription guidance instead of treating price alone as proof of equivalence."
      },
      {
        question: "Should customers self-switch a prescription medicine based only on search results?",
        answer:
          "No. Prescription-led decisions should go through pharmacist review, especially when there is any uncertainty about strength, dosage form, or patient history."
      }
    ],
    cta: {
      title: "Use the education page as a decision aid, not the final decision",
      body: "Search first, compare carefully, and route prescription-based choices through review.",
      primaryLabel: "Search Medicines",
      primaryHref: "/search",
      secondaryLabel: "Upload Prescription",
      secondaryHref: "/upload-prescription"
    }
  },
  offers: {
    eyebrow: "Offers and Savings",
    title: "Savings pages that support the real order journey",
    intro:
      "Offers should help customers move toward a valid order, not distract them from medicine fit, prescription rules, or repeat-purchase needs.",
    highlights: [
      { label: "Includes", value: "Coupons, refill nudges, and bundle savings" },
      { label: "Best for", value: "Everyday medicines and chronic-care planning" },
      { label: "Guardrail", value: "Prescription rules still apply" }
    ],
    sections: [
      {
        title: "How offers should be used",
        body:
          "Savings communication works best when it stays tied to real product, cart, and refill contexts instead of floating as isolated marketing banners."
      },
      {
        title: "Common offer patterns",
        body:
          "The offers page can host storefront-wide promotions while still routing customers into search, categories, or refill-friendly journeys.",
        points: [
          "Welcome savings for first purchases",
          "Chronic-care reorder nudges",
          "Category-level seasonal promotions",
          "Prescription-upload support for restricted items"
        ]
      },
      {
        title: "Eligibility and transparency",
        body:
          "The page should set expectations about validity windows, minimum-order values, medicine exclusions, and the fact that regulatory requirements override promotional intent."
      }
    ],
    cards: [
      {
        title: "Browse medicines",
        body: "See product and category pricing before applying any savings logic.",
        href: "/categories/medicines",
        ctaLabel: "Browse Categories"
      },
      {
        title: "Compare substitutes",
        body: "Savings often become clearer on search and product pages than on a generic campaign banner.",
        href: "/search",
        ctaLabel: "Search Medicines"
      }
    ],
    faqs: [
      {
        question: "Can an offer override prescription requirements?",
        answer:
          "No. Valid prescription review and medicine compliance rules still apply even when a product appears inside an offer-led journey."
      }
    ],
    cta: {
      title: "Use offers as a route into the storefront, not a dead end",
      body: "Move customers from promotional intent into search, categories, and valid checkout paths.",
      primaryLabel: "Browse Categories",
      primaryHref: "/categories/medicines",
      secondaryLabel: "Search Medicines",
      secondaryHref: "/search"
    }
  },
  privacy: {
    eyebrow: "Privacy",
    title: "How personal details and prescription files are handled",
    intro:
      "The privacy page explains what customer information is used across account, order, support, and prescription-review flows so the storefront builds trust before sensitive data is shared.",
    highlights: [
      { label: "Covers", value: "Account, order, prescription, and support data" },
      { label: "Includes", value: "Purpose, retention, and escalation context" },
      { label: "Contact", value: siteContact.grievanceEmail },
      { label: "Controller", value: siteContact.officeName }
    ],
    sections: [
      {
        title: "What information may be collected",
        body:
          "Depending on the journey, the storefront may involve contact details, delivery addresses, uploaded prescriptions, account activity, and support conversations."
      },
      {
        title: "Why the information is used",
        body:
          "The site uses data to validate prescription-led orders, provide support, process delivery steps, and maintain account continuity across repeat purchases.",
        points: [
          "Order processing and fulfillment coordination",
          "Prescription verification and clarification",
          "Customer support and grievance tracking",
          "Account history and repeat-order convenience"
        ]
      },
      {
        title: "Questions and escalations",
        body:
          "When customers need clarification on privacy handling, they should have a direct escalation route instead of relying only on general support.",
        callout: `Privacy and grievance contact: ${siteContact.grievanceEmail} | Grievance officer: ${siteContact.grievanceOfficer}`
      }
    ],
    faqs: [
      {
        question: "Why does the site ask for a prescription upload on some medicines?",
        answer:
          "Prescription files are collected only where review is required for safe and compliant fulfillment of the requested medicines."
      },
      {
        question: "Can a customer contact someone about data handling concerns?",
        answer:
          `Yes. The grievance path is available through ${siteContact.grievanceEmail} and the named officer ${siteContact.grievanceOfficer}.`
      }
    ],
    cta: {
      title: "Need a policy clarification before ordering?",
      body: "Review related policy pages or contact support if the customer needs help before sharing documents.",
      primaryLabel: "Contact Support",
      primaryHref: "/contact",
      secondaryLabel: "Prescription Policy",
      secondaryHref: "/prescription-policy"
    }
  },
  terms: {
    eyebrow: "Terms and Conditions",
    title: "Core storefront rules for orders, pricing, and customer use",
    intro:
      "The terms page gives customers a readable overview of how the storefront should be used and what operational and compliance rules shape the order journey.",
    highlights: [
      { label: "Includes", value: "Use of service, pricing, and order handling" },
      { label: "Applies to", value: "Account, search, checkout, and support flows" },
      { label: "Related pages", value: "Privacy, prescription, and serviceability" },
      { label: "Registered entity", value: siteContact.officeName }
    ],
    sections: [
      {
        title: "Using the storefront",
        body:
          "Customers are expected to provide accurate account, order, and prescription information so the pharmacy and support flows can operate correctly."
      },
      {
        title: "Orders and pricing",
        body:
          "Availability, final fulfillment, and pricing can depend on stock, serviceability, prescription review, and operational checks before completion.",
        points: [
          "Displayed availability may change during fulfillment review.",
          "Prescription medicines may need manual validation.",
          "Serviceability and restrictions can affect final delivery feasibility."
        ]
      },
      {
        title: "Customer responsibility",
        body:
          "The storefront supports medicine discovery and order handling, but customers should still confirm prescription-led decisions through qualified medical advice where appropriate."
      },
      {
        title: "Regulated pharmacy operations",
        body:
          "Pharmacy-led fulfillment, restricted-medicine review, and pharmacist intervention operate under the registered entity and published licensing details displayed across the storefront.",
        callout: `Drug license: ${siteContact.pharmacyLicenseNumber} | Authority: ${siteContact.pharmacyLicenseAuthority}`
      }
    ],
    faqs: [
      {
        question: "Can an order be changed after it is placed?",
        answer:
          "That depends on processing stage, stock, and whether the order is already in fulfillment or requires pharmacist review."
      }
    ],
    cta: {
      title: "Read policies together, not in isolation",
      body: "Terms, privacy, prescription rules, and delivery coverage work best when customers can move among them easily.",
      primaryLabel: "Privacy Policy",
      primaryHref: "/privacy",
      secondaryLabel: "Serviceability",
      secondaryHref: "/serviceability"
    }
  },
  "prescription-policy": {
    eyebrow: "Prescription Policy",
    title: "What makes a prescription-led order valid for review",
    intro:
      "This page sets the storefront expectations for prescription medicines, upload quality, pharmacist review, and the reasons a request may need clarification before fulfillment.",
    highlights: [
      { label: "Valid upload", value: "Clear image or PDF with visible medicine details" },
      { label: "Review goal", value: "Safe and compliant medicine fulfillment" },
      { label: "Outcome", value: "Approve, clarify, or reject when needed" },
      { label: "Reviewed by", value: siteContact.pharmacistInCharge }
    ],
    sections: [
      {
        title: "What a valid prescription should include",
        body:
          "A usable prescription should clearly identify the patient, prescriber, and medicine directions so the pharmacist can review it with confidence."
      },
      {
        title: "When clarification is needed",
        body:
          "Unclear handwriting, incomplete pages, missing dates, or restricted medicines can all trigger a clarification request before the order proceeds.",
        points: [
          "Blurry or cropped uploads",
          "Incomplete doctor or patient details",
          "Strength or dosage ambiguity",
          "Restricted or high-scrutiny medicines"
        ]
      },
      {
        title: "How substitute questions fit in",
        body:
          "Substitute discovery can support a conversation, but prescription-led medicine changes should still pass through pharmacist review rather than automatic self-selection."
      },
      {
        title: "Who conducts the review",
        body:
          "Prescription checks should be traceable to a licensed pharmacy operation and a pharmacist-led review process rather than a generic support queue.",
        points: [
          `Pharmacy license: ${siteContact.pharmacyLicenseNumber}`,
          `Licensing authority: ${siteContact.pharmacyLicenseAuthority}`,
          `Pharmacist in charge: ${siteContact.pharmacistInCharge}`,
          `Pharmacist registration: ${siteContact.pharmacistRegistrationNumber}`
        ]
      }
    ],
    faqs: [
      {
        question: "Does every prescription upload get approved immediately?",
        answer:
          "No. Some uploads are approved quickly, while others need clarification or may be rejected if the prescription does not meet review requirements."
      }
    ],
    cta: {
      title: "Use the policy page as preparation for the upload flow",
      body: "Customers can review the requirements, then continue directly into prescription submission.",
      primaryLabel: "Upload Prescription",
      primaryHref: "/upload-prescription",
      secondaryLabel: "Contact Support",
      secondaryHref: "/contact"
    }
  },
  serviceability: {
    eyebrow: "Delivery Coverage",
    title: "Understand where and how medicine delivery can be supported",
    intro:
      "Serviceability explains how location, medicine type, and operational rules affect whether an order can be fulfilled and what speed the customer should expect.",
    highlights: [
      { label: "Depends on", value: "Location, stock, and medicine category" },
      { label: "Affects", value: "Delivery promise and fulfillment options" },
      { label: "Related flow", value: "Checkout and support" }
    ],
    sections: [
      {
        title: "Why serviceability matters",
        body:
          "Customers should know before checkout whether their location supports the expected delivery flow, especially when medicines require special handling or prescription review."
      },
      {
        title: "What can affect coverage",
        body:
          "Coverage is not only about the pincode. It can also change with stock, courier constraints, restricted medicines, and operational timings.",
        points: [
          "Address and locality support",
          "Medicine category restrictions",
          "Prescription validation delays",
          "Operational and courier capacity"
        ]
      },
      {
        title: "What to do if a location is not supported",
        body:
          "Customers should contact support for guidance, alternative routing, or to understand whether a different order composition changes the delivery outcome."
      }
    ],
    faqs: [
      {
        question: "Why is one product deliverable but another is not?",
        answer:
          "Medicine type, stock, prescription requirements, and locality-level operational limits can all change the outcome between products."
      }
    ],
    cta: {
      title: "Move from coverage questions to order help",
      body: "If the delivery promise is unclear, support can help the customer decide the next step.",
      primaryLabel: "Contact Support",
      primaryHref: "/contact",
      secondaryLabel: "Browse Medicines",
      secondaryHref: "/categories/medicines"
    }
  }
};

function formatSlugTitle(slug?: string[]) {
  if (!slug?.length) {
    return "";
  }

  return slug
    .join(" / ")
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function buildEditorialPageContent(
  kind: "blog" | "health-guide",
  slug?: string[]
): MarketingPageContent {
  const topicTitle =
    formatSlugTitle(slug) || (kind === "blog" ? "Health Articles" : "Health Guide");
  const isHub = !slug?.length;
  const isGuide = kind === "health-guide";

  const intro = isHub
    ? isGuide
      ? "Browse educational explainers around conditions, medicine understanding, and safer everyday care decisions."
      : "Browse editorial health reading that supports search, substitute comparison, and repeat-order confidence."
    : isGuide
      ? `This guide page gives customers a clearer, easier-to-read overview of ${topicTitle.toLowerCase()} and how it connects to medicine discovery and pharmacy support.`
      : `This article page turns the ${topicTitle.toLowerCase()} topic into a real reading experience instead of a dead placeholder route.`;

  return {
    eyebrow: isGuide ? "Health Guide" : "Editorial",
    title: topicTitle,
    intro,
    highlights: [
      {
        label: "Format",
        value: isHub ? "Topic hub and article discovery" : "Readable topic page"
      },
      {
        label: "Best next step",
        value: isGuide ? "Continue into search or support" : "Continue into related medicine discovery"
      },
      {
        label: "Connected pages",
        value: "Search, FAQ, and category browsing"
      }
    ],
    sections: [
      {
        title: isHub ? "How to use this content hub" : "What this topic page is designed to do",
        body: isHub
          ? "The hub routes customers into discoverable reading topics instead of leaving article links unresolved. It works as a bridge between browsing and action."
          : "The page gives the topic enough structure to feel complete now, while still leaving room for richer editorial or medical-review workflows later."
      },
      {
        title: isGuide ? "How the guide connects to the storefront" : "Why editorial content matters here",
        body: isGuide
          ? "Customers often need context before they can search confidently. Health-guide pages reduce uncertainty and help users know whether they should continue into search, categories, or support."
          : "Editorial pages help customers understand categories, chronic-care routines, generic medicine questions, and common medicine-use contexts before they act.",
        points: [
          "Support medicine education and awareness",
          "Route readers into search and product journeys",
          "Reduce dead-end navigation from homepage article links"
        ]
      },
      {
        title: "What should happen next",
        body:
          "After reading, the customer should be able to continue into medicine search, upload a prescription when relevant, or contact support for a specific case."
      }
    ],
    cards: [
      {
        title: "Search related medicines",
        body: "Move from reading into product discovery and substitute comparison.",
        href: "/search",
        ctaLabel: "Search Medicines"
      },
      {
        title: "Browse categories",
        body: "Explore category pages when the reader wants a broader storefront path.",
        href: "/categories/medicines",
        ctaLabel: "Browse Categories"
      },
      {
        title: "Need human help?",
        body: "Use support when the topic turns into an order, prescription, or delivery question.",
        href: "/contact",
        ctaLabel: "Contact Support"
      }
    ],
    faqs: [
      {
        question: "Is this page informational or transactional?",
        answer:
          "It is primarily informational, but it is designed to connect cleanly into transactional storefront routes when the reader is ready."
      }
    ],
    cta: {
      title: "Continue from content into action",
      body: "The hub and topic pages now connect back into the real storefront rather than ending at a placeholder screen.",
      primaryLabel: "Search Medicines",
      primaryHref: "/search",
      secondaryLabel: "Contact Support",
      secondaryHref: "/contact"
    }
  };
}
