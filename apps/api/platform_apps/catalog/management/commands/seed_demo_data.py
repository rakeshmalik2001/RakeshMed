from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from platform_apps.catalog.models import Brand, Category, Product, ProductSubstitute
from platform_apps.notifications.models import Notification
from platform_apps.orders.models import Order, OrderEvent, OrderItem, PaymentAttempt, RefundRequest
from platform_apps.prescriptions.models import Prescription, PrescriptionReview
from platform_apps.users.models import CustomerAddress, SavedPaymentMethod, User


CATALOG_SEED = {
    "medicines": {
        "name": "Medicines",
        "description": "Prescription and OTC medicines for routine care and repeat orders.",
        "sort_order": 1,
        "children": [
            {
                "slug": "heart-care",
                "name": "Heart Care",
                "description": "Cardiac and cholesterol management medicines.",
                "sort_order": 1,
                "products": [
                    {
                        "brand": "Zydus",
                        "name": "Atorva 10 Tablet",
                        "slug": "atorva-10-tablet",
                        "sku": "MED-ATORVA-10",
                        "composition": "Atorvastatin",
                        "dosage_form": "Tablet",
                        "strength": "10 mg",
                        "pack_size": "Strip of 15 tablets",
                        "manufacturer": "Zydus Healthcare",
                        "mrp": "152.40",
                        "sale_price": "94.48",
                        "requires_prescription": True,
                        "is_otc": False,
                        "stock_status": "in_stock",
                        "description": "Prescription statin used in lipid management and repeat cardiac therapy.",
                        "warnings": "Use only under medical supervision. Regular doctor review is recommended.",
                        "side_effects": "Read the prescription label carefully and consult your doctor if symptoms feel unusual.",
                        "storage_instructions": "Store in a cool and dry place away from sunlight.",
                    },
                    {
                        "brand": "Sun Pharma",
                        "name": "Rosuvas 10 Tablet",
                        "slug": "rosuvas-10-tablet",
                        "sku": "MED-ROSUVAS-10",
                        "composition": "Rosuvastatin",
                        "dosage_form": "Tablet",
                        "strength": "10 mg",
                        "pack_size": "Strip of 10 tablets",
                        "manufacturer": "Sun Pharmaceutical Industries Ltd",
                        "mrp": "154.80",
                        "sale_price": "125.38",
                        "requires_prescription": True,
                        "is_otc": False,
                        "stock_status": "in_stock",
                        "description": "Used in long-term cholesterol control and cardiovascular risk management.",
                        "warnings": "Continue only as advised by your doctor and review alongside diet changes.",
                        "side_effects": "Check with your doctor before switching doses or stopping therapy.",
                        "storage_instructions": "Store below 30C in a dry place.",
                    },
                ],
            },
            {
                "slug": "respiratory-care",
                "name": "Respiratory Care",
                "description": "Supportive products and medicines for respiratory needs.",
                "sort_order": 2,
                "products": [
                    {
                        "brand": "Fdc",
                        "name": "Electral Sachet 4.4gm",
                        "slug": "electral-sachet-4-4gm",
                        "sku": "MED-ELECTRAL-4",
                        "composition": "Electrolytes",
                        "dosage_form": "Powder",
                        "strength": "4.4 gm",
                        "pack_size": "Single sachet",
                        "manufacturer": "FDC Ltd",
                        "mrp": "4.65",
                        "sale_price": "3.72",
                        "requires_prescription": False,
                        "is_otc": True,
                        "stock_status": "in_stock",
                        "description": "Oral rehydration support for recovery from fluid loss.",
                        "warnings": "Use according to pack directions and hydration advice.",
                        "side_effects": "Stop and seek medical guidance if symptoms worsen.",
                        "storage_instructions": "Store in a cool and dry place.",
                    }
                ],
            },
        ],
    },
    "personal-care": {
        "name": "Personal Care",
        "description": "Everyday care products across skin, hair, and family wellness.",
        "sort_order": 2,
        "children": [
            {
                "slug": "skin-care",
                "name": "Skin Care",
                "description": "Daily skincare and sunscreen products.",
                "sort_order": 1,
                "products": [
                    {
                        "brand": "Skinshine",
                        "name": "Skinshine SPF 30 Sunscreen Lotion 100ml",
                        "slug": "skinshine-spf-30-sunscreen-lotion-100ml",
                        "sku": "CARE-SKINSHINE-SPF30",
                        "composition": "All Other Combinations",
                        "dosage_form": "Lotion",
                        "strength": "SPF 30",
                        "pack_size": "Bottle of 100 ml",
                        "manufacturer": "Cadila Pharmaceuticals Ltd",
                        "mrp": "239.00",
                        "sale_price": "215.10",
                        "requires_prescription": False,
                        "is_otc": True,
                        "stock_status": "in_stock",
                        "description": "Broad-spectrum sunscreen for daily sun protection and skincare support.",
                        "warnings": "For external use only. Avoid direct eye contact.",
                        "side_effects": "Patch test before first use if you have sensitive skin.",
                        "storage_instructions": "Store below 30C away from direct sunlight.",
                    },
                    {
                        "brand": "Cetaphil",
                        "name": "Cetaphil Moisturising Cream 80gm",
                        "slug": "cetaphil-moisturising-cream-80gm",
                        "sku": "CARE-CETAPHIL-80",
                        "composition": "Moisturising Base",
                        "dosage_form": "Cream",
                        "strength": "80 gm",
                        "pack_size": "Tube of 80 gm",
                        "manufacturer": "Galderma India Pvt Ltd",
                        "mrp": "669.00",
                        "sale_price": "602.10",
                        "requires_prescription": False,
                        "is_otc": True,
                        "stock_status": "in_stock",
                        "description": "Hydration-focused cream for everyday dry skin support.",
                        "warnings": "Use externally and follow pack guidance.",
                        "side_effects": "Stop use if irritation develops.",
                        "storage_instructions": "Keep tightly closed in a cool dry place.",
                    },
                ],
            }
        ],
    },
    "healthcare-devices": {
        "name": "Healthcare Devices",
        "description": "Home monitoring and support devices.",
        "sort_order": 3,
        "children": [
            {
                "slug": "monitoring-devices",
                "name": "Monitoring Devices",
                "description": "Devices for home checks and routine monitoring.",
                "sort_order": 1,
                "products": [
                    {
                        "brand": "Dr Morepen",
                        "name": "Dr Morepen BP 02 Blood Pressure Monitor",
                        "slug": "dr-morepen-bp02-bp-monitor",
                        "sku": "DEV-BP02",
                        "composition": "Digital Blood Pressure Monitor",
                        "dosage_form": "Device",
                        "strength": "Single unit",
                        "pack_size": "Single monitoring device",
                        "manufacturer": "Dr Morepen",
                        "mrp": "1899.00",
                        "sale_price": "1557.18",
                        "requires_prescription": False,
                        "is_otc": True,
                        "stock_status": "in_stock",
                        "description": "Home blood pressure monitor for routine tracking.",
                        "warnings": "Use according to the device manual.",
                        "side_effects": "Recheck unusual readings with a medical professional.",
                        "storage_instructions": "Store safely in the provided box when not in use.",
                    }
                ],
            }
        ],
    },
    "health-conditions": {
        "name": "Health Conditions",
        "description": "Condition-led discovery for routine health needs.",
        "sort_order": 4,
        "children": [
            {
                "slug": "bone-and-joint-care",
                "name": "Bone and Joint Care",
                "description": "Bone and joint support products.",
                "sort_order": 1,
            },
            {
                "slug": "digestive-care",
                "name": "Digestive Care",
                "description": "Digestive wellness and gut support.",
                "sort_order": 2,
                "children": [
                    {"slug": "pre-and-probiotics", "name": "Pre and Probiotics", "description": "Gut flora support.", "sort_order": 1},
                    {"slug": "acidity", "name": "Acidity", "description": "Acidity support.", "sort_order": 2},
                    {"slug": "gas", "name": "Gas", "description": "Gas relief products.", "sort_order": 3},
                    {"slug": "constipation", "name": "Constipation", "description": "Constipation support.", "sort_order": 4},
                    {"slug": "loose-motion-diarrhoea", "name": "Loose Motion/Diarrhoea", "description": "Digestive recovery support.", "sort_order": 5},
                    {"slug": "digestive-fibres", "name": "Digestive Fibres", "description": "Daily fibre support.", "sort_order": 6},
                    {"slug": "digestive-enzymes", "name": "Digestive Enzymes", "description": "Digestive enzyme support.", "sort_order": 7},
                ],
            },
            {
                "slug": "eye-care",
                "name": "Eye Care",
                "description": "Eye comfort and support products.",
                "sort_order": 3,
                "children": [
                    {"slug": "eye-lubricant-drops", "name": "Eye Lubricant Drops", "description": "Eye moisture support.", "sort_order": 1},
                    {"slug": "lens-solution", "name": "Lens Solution", "description": "Lens care solutions.", "sort_order": 2},
                    {"slug": "safety-eye-wear", "name": "Safety Eye Wear", "description": "Protective eye wear.", "sort_order": 3},
                    {"slug": "eye-cream", "name": "Eye Cream", "description": "Eye area care.", "sort_order": 4},
                    {"slug": "eye-vitamins-and-supplements", "name": "Eye Vitamins and Supplements", "description": "Eye nutrition support.", "sort_order": 5},
                    {"slug": "eye-drops", "name": "Eye Drops", "description": "General eye drops.", "sort_order": 6},
                    {"slug": "eye-ointment-and-gel", "name": "Eye Ointment and Gel", "description": "Eye ointment and gel support.", "sort_order": 7},
                ],
            },
            {
                "slug": "pain-relief",
                "name": "Pain Relief",
                "description": "Pain relief products and support.",
                "sort_order": 4,
            },
            {
                "slug": "smoking-cessation",
                "name": "Smoking Cessation",
                "description": "Products to support smoking cessation.",
                "sort_order": 5,
                "children": [
                    {"slug": "nicotine-patch", "name": "Nicotine Patch", "description": "Nicotine patch support.", "sort_order": 1},
                    {"slug": "nicotine-gum", "name": "Nicotine Gum", "description": "Nicotine gum support.", "sort_order": 2},
                    {"slug": "nicotine-lozenges", "name": "Nicotine Lozenges", "description": "Nicotine lozenge support.", "sort_order": 3},
                ],
            },
            {"slug": "liver-care", "name": "Liver Care", "description": "Liver wellness support.", "sort_order": 6},
            {"slug": "stomach-care", "name": "Stomach Care", "description": "Stomach care support.", "sort_order": 7},
            {
                "slug": "cold-and-cough",
                "name": "Cold and Cough",
                "description": "Cold and cough care products.",
                "sort_order": 8,
                "children": [
                    {"slug": "cough-syrups", "name": "Cough Syrups", "description": "Cough syrup options.", "sort_order": 1},
                    {"slug": "chest-rubs-and-balms", "name": "Chest Rubs and Balms", "description": "Chest rubs and balms.", "sort_order": 2},
                    {"slug": "nasal-spray", "name": "Nasal Spray", "description": "Nasal spray care.", "sort_order": 3},
                    {"slug": "lozenges", "name": "Lozenges", "description": "Lozenge care.", "sort_order": 4},
                    {"slug": "inhalant-capsules", "name": "Inhalant Capsules", "description": "Inhalant capsule options.", "sort_order": 5},
                    {"slug": "cold-and-cough-tablets", "name": "Cold and Cough Tablets", "description": "Cold and cough tablet options.", "sort_order": 6},
                ],
            },
            {"slug": "heart-care-conditions", "name": "Heart Care", "description": "Heart condition support.", "sort_order": 9},
            {"slug": "kidney-care", "name": "Kidney Care", "description": "Kidney wellness support.", "sort_order": 10},
            {"slug": "piles-fissures-and-fistula", "name": "Piles, Fissures & Fistula", "description": "Comfort and support products.", "sort_order": 11},
            {"slug": "respiratory-care-conditions", "name": "Respiratory Care", "description": "Respiratory support.", "sort_order": 12},
            {"slug": "mental-wellness", "name": "Mental Wellness", "description": "Mental wellness support.", "sort_order": 13},
            {"slug": "derma-care", "name": "Derma Care", "description": "Dermatology-oriented care.", "sort_order": 14},
        ],
    },
    "vitamins-and-supplements": {
        "name": "Vitamins & Supplements",
        "description": "Daily nutrition and supplement support.",
        "sort_order": 5,
        "children": [
            {"slug": "multivitamins-multiminerals-and-antioxidants", "name": "Multivitamins, Multiminerals and Antioxidants", "description": "Daily multivitamin support.", "sort_order": 1},
            {"slug": "calcium-and-minerals", "name": "Calcium & Minerals", "description": "Calcium and mineral support.", "sort_order": 2},
            {"slug": "vitamin-a-to-z", "name": "Vitamin A to Z", "description": "Broad vitamin range.", "sort_order": 3},
            {"slug": "protein-supplements", "name": "Protein Supplements", "description": "Protein supplement options.", "sort_order": 4},
            {"slug": "supplement-powder", "name": "Supplement Powder", "description": "Powder supplement options.", "sort_order": 5},
            {"slug": "vitamin-b12-and-b-complex", "name": "Vitamin B12 and B Complex", "description": "Vitamin B support.", "sort_order": 6},
            {"slug": "mineral-supplements", "name": "Mineral Supplements", "description": "Mineral supplement options.", "sort_order": 7},
            {"slug": "immunity-boosters", "name": "Immunity Boosters", "description": "Immunity support.", "sort_order": 8},
            {"slug": "omega-and-fish-oil", "name": "Omega and Fish Oil", "description": "Omega and fish oil support.", "sort_order": 9},
        ],
    },
    "diabetes-care": {
        "name": "Diabetes Care",
        "description": "Monitoring and support for diabetes routines.",
        "sort_order": 6,
        "children": [
            {"slug": "test-strips-and-lancets", "name": "Test Strips and Lancets", "description": "Glucose test consumables.", "sort_order": 1},
            {"slug": "blood-glucose-monitors", "name": "Blood Glucose Monitors", "description": "Glucose monitor devices.", "sort_order": 2},
            {"slug": "diabetic-diet", "name": "Diabetic Diet", "description": "Diet support products.", "sort_order": 3},
            {"slug": "sugar-substitutes", "name": "Sugar Substitutes", "description": "Sugar substitute options.", "sort_order": 4},
            {"slug": "diabetes-ayurvedic-medicines", "name": "Diabetes Ayurvedic Medicines", "description": "Ayurvedic diabetes support.", "sort_order": 5},
            {"slug": "homeopathy", "name": "Homeopathy", "description": "Homeopathic diabetes support.", "sort_order": 6},
            {"slug": "syringes-and-pens", "name": "Syringes and Pens", "description": "Syringes and pen devices.", "sort_order": 7},
        ],
    },
    "homeopathic-medicine": {
        "name": "Homeopathic Medicine",
        "description": "Homeopathic care and wellness categories.",
        "sort_order": 7,
        "children": [
            {"slug": "homeopathy-for-skin-care", "name": "Homeopathy for Skin Care", "description": "Skin care homeopathy.", "sort_order": 1},
            {"slug": "homeopathy-digestive-care", "name": "Homeopathy Digestive Care", "description": "Digestive care homeopathy.", "sort_order": 2},
            {"slug": "homeopathy-for-seniors", "name": "Homeopathy for Seniors", "description": "Senior care homeopathy.", "sort_order": 3},
            {"slug": "homeopathy-heart-care", "name": "Homeopathy Heart Care", "description": "Heart care homeopathy.", "sort_order": 4},
            {"slug": "homeopathy-kidney-care", "name": "Homeopathy Kidney Care", "description": "Kidney care homeopathy.", "sort_order": 5},
            {"slug": "homeopathy-sexual-health", "name": "Homeopathy Sexual Health", "description": "Sexual health homeopathy.", "sort_order": 6},
            {"slug": "homeopathy-for-diabetes-care", "name": "Homeopathy for Diabetes Care", "description": "Diabetes care homeopathy.", "sort_order": 7},
            {"slug": "homeopathy-for-hair-care", "name": "Homeopathy for Hair Care", "description": "Hair care homeopathy.", "sort_order": 8},
            {"slug": "homeopathy-cold-and-cough", "name": "Homeopathy Cold & Cough", "description": "Cold and cough homeopathy.", "sort_order": 9},
        ],
    },
    "health-guide": {
        "name": "Health Guide",
        "description": "Health articles, stories, and educational guides.",
        "sort_order": 8,
        "children": [
            {"slug": "health-articles", "name": "Health Articles", "description": "Health articles.", "sort_order": 1},
            {"slug": "diseases-and-health-conditions", "name": "Diseases & Health Conditions", "description": "Condition education.", "sort_order": 2},
            {"slug": "health-stories", "name": "Health Stories", "description": "Health stories.", "sort_order": 3},
            {"slug": "ayurveda", "name": "Ayurveda", "description": "Ayurveda guides.", "sort_order": 4},
            {"slug": "understanding-generic-medicines", "name": "Understanding Generic Medicines", "description": "Generic medicine education.", "sort_order": 5},
            {"slug": "health-library", "name": "Health Library", "description": "Health library.", "sort_order": 6},
        ],
    },
}

SUBSTITUTES = [
    ("atorva-10-tablet", "rosuvas-10-tablet", "Alternative lipid-control option"),
]


class Command(BaseCommand):
    help = "Seed demo catalog, substitutes, prescription, and order data for local development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--phone",
            default="7002579537",
            help="Customer phone number for seeding demo prescription and order data.",
        )
        parser.add_argument(
            "--name",
            default="Rakesh Malik",
            help="Customer full name for the seeded demo account.",
        )

    def handle(self, *args, **options):
        phone = options["phone"]
        full_name = options["name"]

        customer, _ = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                "full_name": full_name,
                "role": "customer",
                "is_phone_verified": True,
            },
        )
        customer.full_name = customer.full_name or full_name
        customer.role = "customer"
        customer.is_phone_verified = True
        customer.save(update_fields=["full_name", "role", "is_phone_verified"])
        Notification.objects.update_or_create(
            user=customer,
            title="Welcome back to TrueCare",
            defaults={
                "kind": "account",
                "body": "Your demo account is ready with saved addresses, payment methods, orders, and prescriptions.",
                "link": "/account",
                "meta": {"seed": True},
            },
        )

        pharmacist, _ = User.objects.get_or_create(
            phone_number="9999990001",
            defaults={
                "full_name": "TrueCare Pharmacist",
                "role": "pharmacist",
                "is_phone_verified": True,
                "is_staff": True,
            },
        )
        pharmacist.full_name = pharmacist.full_name or "TrueCare Pharmacist"
        pharmacist.role = "pharmacist"
        pharmacist.is_phone_verified = True
        pharmacist.is_staff = True
        pharmacist.save(update_fields=["full_name", "role", "is_phone_verified", "is_staff"])

        for phone_number, full_name_value, role_value in [
            ("9999990002", "TrueCare Admin", "admin"),
            ("9999990003", "TrueCare Finance", "finance"),
            ("9999990004", "TrueCare Catalog", "catalog_manager"),
            ("9999990005", "TrueCare Support", "support_agent"),
        ]:
            ops_user, _ = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={
                    "full_name": full_name_value,
                    "role": role_value,
                    "is_phone_verified": True,
                    "is_staff": True,
                },
            )
            ops_user.full_name = ops_user.full_name or full_name_value
            ops_user.role = role_value
            ops_user.is_phone_verified = True
            ops_user.is_staff = True
            update_fields = ["full_name", "role", "is_phone_verified", "is_staff"]
            if role_value == "admin":
                ops_user.is_superuser = True
                update_fields.append("is_superuser")
            ops_user.save(update_fields=update_fields)

        created_categories = 0
        created_brands = 0
        created_products = 0

        product_map: dict[str, Product] = {}

        for root_slug, root_data in CATALOG_SEED.items():
            counts = self.upsert_category_branch(
                {
                    "slug": root_slug,
                    **root_data,
                },
                None,
                product_map,
            )
            created_categories += counts["categories"]
            created_brands += counts["brands"]
            created_products += counts["products"]

        for source_slug, substitute_slug, reason in SUBSTITUTES:
            source_product = product_map.get(source_slug)
            substitute_product = product_map.get(substitute_slug)
            if not source_product or not substitute_product:
                continue
            ProductSubstitute.objects.update_or_create(
                source_product=source_product,
                substitute_product=substitute_product,
                defaults={"reason": reason},
            )

        prescription, _ = Prescription.objects.update_or_create(
            reference_code="RX-700257",
            defaults={
                "user": customer,
                "patient_name": full_name,
                "doctor_name": "Dr. Sharma",
                "notes": "Repeat lipid therapy and routine refill review.",
                "uploaded_file_name": "demo-prescription.jpg",
                "uploaded_file_url": "https://example.com/demo-prescription.jpg",
                "uploaded_file_type": "image/jpeg",
                "status": "approved",
                "review_priority": "normal",
                "review_eta_hours": 4,
                "reviewed_by": pharmacist,
                "reviewed_at": timezone.now(),
            },
        )

        PrescriptionReview.objects.update_or_create(
            prescription=prescription,
            reviewer=pharmacist,
            decision="approved",
            defaults={
                "notes": "Prescription reviewed and approved for repeat order fulfilment.",
                "substitute_guidance": "Atorva and Rosuvas comparison available if the doctor permits.",
            },
        )

        CustomerAddress.objects.update_or_create(
            user=customer,
            label="Home",
            defaults={
                "recipient": full_name,
                "line1": "21/4 Lake View Residency, Powai",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400079",
                "phone_number": customer.phone_number,
                "is_default": True,
            },
        )

        CustomerAddress.objects.update_or_create(
            user=customer,
            label="Office",
            defaults={
                "recipient": full_name,
                "line1": "Business Park Tower, Andheri East",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400093",
                "phone_number": customer.phone_number,
                "is_default": False,
            },
        )

        SavedPaymentMethod.objects.update_or_create(
            user=customer,
            label="UPI - rakesh@okaxis",
            defaults={
                "method_type": "UPI",
                "upi_id": "rakesh@okaxis",
                "masked_details": "",
                "is_default": True,
                "is_active": True,
            },
        )

        SavedPaymentMethod.objects.update_or_create(
            user=customer,
            label="Primary card",
            defaults={
                "method_type": "CARD",
                "upi_id": "",
                "masked_details": "**** **** **** 4242",
                "is_default": False,
                "is_active": True,
            },
        )

        atorva = product_map.get("atorva-10-tablet")
        skinshine = product_map.get("skinshine-spf-30-sunscreen-lotion-100ml")

        if atorva and skinshine:
            order, _ = Order.objects.update_or_create(
                order_number="TC-20260418-1001",
                defaults={
                    "user": customer,
                    "status": "pending_prescription_review",
                    "payment_method": "UPI",
                    "payment_status": "pending",
                    "address_label": "Home",
                    "recipient": full_name,
                    "line1": "21/4 Lake View Residency, Powai",
                    "city": "Mumbai",
                    "pincode": "400079",
                    "upi_id": "rakesh@okaxis",
                    "notes": "Demo seeded order for account history and checkout verification.",
                    "subtotal": Decimal("391.40"),
                    "discount": Decimal("82.30"),
                    "delivery_fee": Decimal("40.00"),
                    "total": Decimal("349.10"),
                    "requires_prescription_count": 1,
                },
            )
            order.items.all().delete()
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=atorva,
                        product_slug=atorva.slug,
                        product_name=atorva.name,
                        meta=f"{atorva.composition} | {atorva.pack_size}",
                        mrp=atorva.mrp,
                        sale_price=atorva.sale_price,
                        qty=1,
                        requires_prescription=True,
                    ),
                    OrderItem(
                        order=order,
                        product=skinshine,
                        product_slug=skinshine.slug,
                        product_name=skinshine.name,
                        meta=f"{skinshine.brand.name} | {skinshine.pack_size}",
                        mrp=skinshine.mrp,
                        sale_price=skinshine.sale_price,
                        qty=1,
                        requires_prescription=False,
                    ),
                ]
            )
            PaymentAttempt.objects.update_or_create(
                payment_reference="PAY-TC-20260418-1001-seed",
                defaults={
                    "order": order,
                    "provider": "simulated_gateway",
                    "status": "pending",
                    "amount": order.total,
                    "raw_payload": {"seed": True, "kind": "pending_upi"},
                },
            )
            OrderEvent.objects.filter(order=order).delete()
            OrderEvent.objects.bulk_create(
                [
                    OrderEvent(
                        order=order,
                        event_type="placed",
                        actor=customer,
                        actor_label=customer.full_name,
                        summary="Seeded order placed and awaiting prescription review.",
                        meta={"seed": True},
                    ),
                    OrderEvent(
                        order=order,
                        event_type="payment_session_started",
                        actor=customer,
                        actor_label=customer.full_name,
                        summary="UPI payment session started for the seeded pending order.",
                        meta={"seed": True, "payment_reference": "PAY-TC-20260418-1001-seed"},
                    ),
                ]
            )
            Notification.objects.update_or_create(
                user=customer,
                title="Prescription review pending",
                defaults={
                    "kind": "order_update",
                    "body": "TC-20260418-1001 is waiting for pharmacist review before dispatch.",
                    "link": "/account/orders/TC-20260418-1001",
                    "meta": {"seed": True, "order_number": "TC-20260418-1001"},
                },
            )

            confirmed_order, _ = Order.objects.update_or_create(
                order_number="TC-20260418-1002",
                defaults={
                    "user": customer,
                    "status": "confirmed",
                    "payment_method": "CARD",
                    "payment_status": "paid",
                    "address_label": "Office",
                    "recipient": full_name,
                    "line1": "Business Park Tower, Andheri East",
                    "city": "Mumbai",
                    "pincode": "400093",
                    "upi_id": "",
                    "notes": "Demo confirmed card order for admin/payment testing.",
                    "subtotal": Decimal("154.80"),
                    "discount": Decimal("29.42"),
                    "delivery_fee": Decimal("40.00"),
                    "total": Decimal("165.38"),
                    "requires_prescription_count": 1,
                },
            )
            confirmed_order.items.all().delete()
            OrderItem.objects.create(
                order=confirmed_order,
                product=product_map.get("rosuvas-10-tablet"),
                product_slug="rosuvas-10-tablet",
                product_name="Rosuvas 10 Tablet",
                meta="Rosuvastatin | Strip of 10 tablets",
                mrp=Decimal("154.80"),
                sale_price=Decimal("125.38"),
                qty=1,
                requires_prescription=True,
            )
            PaymentAttempt.objects.update_or_create(
                payment_reference="PAY-TC-20260418-1002-seed",
                defaults={
                    "order": confirmed_order,
                    "provider": "simulated_gateway",
                    "status": "captured",
                    "amount": confirmed_order.total,
                    "confirmed_at": timezone.now(),
                    "raw_payload": {"seed": True, "kind": "captured_card"},
                },
            )
            RefundRequest.objects.update_or_create(
                order=confirmed_order,
                reason="Customer requested a test refund for local finance review.",
                defaults={
                    "payment_attempt": confirmed_order.payment_attempts.first(),
                    "requested_by": customer,
                    "status": "requested",
                    "amount": confirmed_order.total,
                    "resolution_notes": "",
                },
            )
            OrderEvent.objects.filter(order=confirmed_order).delete()
            OrderEvent.objects.bulk_create(
                [
                    OrderEvent(
                        order=confirmed_order,
                        event_type="placed",
                        actor=customer,
                        actor_label=customer.full_name,
                        summary="Seeded order placed from the office address.",
                        meta={"seed": True},
                    ),
                    OrderEvent(
                        order=confirmed_order,
                        event_type="payment_captured",
                        actor_label="Seeded gateway",
                        summary="Card payment captured for the confirmed seeded order.",
                        meta={"seed": True, "payment_reference": "PAY-TC-20260418-1002-seed"},
                    ),
                    OrderEvent(
                        order=confirmed_order,
                        event_type="status_updated",
                        actor_label="Seeded ops flow",
                        summary="Order progressed to confirmed for dispatch.",
                        meta={"seed": True},
                    ),
                ]
            )
            Notification.objects.update_or_create(
                user=customer,
                title="Confirmed order on the way",
                defaults={
                    "kind": "payment_update",
                    "body": "TC-20260418-1002 is confirmed with a captured card payment.",
                    "link": "/account/orders/TC-20260418-1002",
                    "meta": {"seed": True, "order_number": "TC-20260418-1002"},
                },
            )

            cancelled_order, _ = Order.objects.update_or_create(
                order_number="TC-20260418-1003",
                defaults={
                    "user": customer,
                    "status": "cancelled",
                    "payment_method": "UPI",
                    "payment_status": "failed",
                    "address_label": "Home",
                    "recipient": full_name,
                    "line1": "21/4 Lake View Residency, Powai",
                    "city": "Mumbai",
                    "pincode": "400079",
                    "upi_id": "rakesh@okaxis",
                    "notes": "Demo cancelled order for support workflow testing.",
                    "subtotal": Decimal("239.00"),
                    "discount": Decimal("23.90"),
                    "delivery_fee": Decimal("40.00"),
                    "total": Decimal("255.10"),
                    "requires_prescription_count": 0,
                },
            )
            cancelled_order.items.all().delete()
            OrderItem.objects.create(
                order=cancelled_order,
                product=skinshine,
                product_slug=skinshine.slug,
                product_name=skinshine.name,
                meta=f"{skinshine.brand.name} | {skinshine.pack_size}",
                mrp=skinshine.mrp,
                sale_price=skinshine.sale_price,
                qty=1,
                requires_prescription=False,
            )
            PaymentAttempt.objects.update_or_create(
                payment_reference="PAY-TC-20260418-1003-seed",
                defaults={
                    "order": cancelled_order,
                    "provider": "simulated_gateway",
                    "status": "failed",
                    "amount": cancelled_order.total,
                    "raw_payload": {"seed": True, "kind": "failed_upi"},
                },
            )
            OrderEvent.objects.filter(order=cancelled_order).delete()
            OrderEvent.objects.bulk_create(
                [
                    OrderEvent(
                        order=cancelled_order,
                        event_type="placed",
                        actor=customer,
                        actor_label=customer.full_name,
                        summary="Seeded order placed for retry and failure testing.",
                        meta={"seed": True},
                    ),
                    OrderEvent(
                        order=cancelled_order,
                        event_type="payment_failed",
                        actor_label="Seeded gateway",
                        summary="UPI payment attempt failed for the cancelled test order.",
                        meta={"seed": True, "payment_reference": "PAY-TC-20260418-1003-seed"},
                    ),
                    OrderEvent(
                        order=cancelled_order,
                        event_type="cancelled",
                        actor_label="Seeded support flow",
                        summary="Order cancelled after payment failure.",
                        meta={"seed": True},
                    ),
                ]
            )
            Notification.objects.update_or_create(
                user=customer,
                title="Payment retry needed",
                defaults={
                    "kind": "payment_update",
                    "body": "TC-20260418-1003 shows a failed payment attempt and a cancelled order.",
                    "link": "/account/orders/TC-20260418-1003",
                    "meta": {"seed": True, "order_number": "TC-20260418-1003"},
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write(
            f"Categories created: {created_categories}, brands created: {created_brands}, products created: {created_products}"
        )
        self.stdout.write(f"Demo customer ready: {customer.phone_number}")
        self.stdout.write("Demo order: TC-20260418-1001")
        self.stdout.write("Demo order: TC-20260418-1002")
        self.stdout.write("Demo order: TC-20260418-1003")
        self.stdout.write("Demo prescription: RX-700257")
        self.stdout.write("Demo addresses: Home, Office")
        self.stdout.write("Demo payment methods: UPI, Card")
        self.stdout.write("Demo ops users: admin 9999990002, finance 9999990003, catalog 9999990004, support 9999990005")
        self.stdout.write("Demo notifications: welcome, pending review, confirmed order, payment retry")
        self.stdout.write("Demo refund request: TC-20260418-1002")

    @staticmethod
    def slugify(value: str) -> str:
        return (
            value.lower()
            .replace("&", "and")
            .replace(".", "")
            .replace(" ", "-")
        )

    def upsert_category_branch(self, node: dict, parent: Category | None, product_map: dict[str, Product]) -> dict[str, int]:
        category, category_created = Category.objects.update_or_create(
            slug=node["slug"],
            defaults={
                "name": node["name"],
                "description": node.get("description", ""),
                "parent": parent,
                "is_active": True,
                "sort_order": node.get("sort_order", 0),
            },
        )

        counts = {
            "categories": int(category_created),
            "brands": 0,
            "products": 0,
        }

        for child in node.get("children", []):
            child_counts = self.upsert_category_branch(child, category, product_map)
            counts["categories"] += child_counts["categories"]
            counts["brands"] += child_counts["brands"]
            counts["products"] += child_counts["products"]

        for product_data in node.get("products", []):
            brand, brand_created = Brand.objects.update_or_create(
                slug=self.slugify(product_data["brand"]),
                defaults={
                    "name": product_data["brand"],
                    "description": f"{product_data['brand']} catalog brand",
                    "is_active": True,
                },
            )
            counts["brands"] += int(brand_created)

            product, product_created = Product.objects.update_or_create(
                slug=product_data["slug"],
                defaults={
                    "name": product_data["name"],
                    "sku": product_data["sku"],
                    "category": category,
                    "brand": brand,
                    "manufacturer": product_data["manufacturer"],
                    "composition": product_data["composition"],
                    "dosage_form": product_data["dosage_form"],
                    "strength": product_data["strength"],
                    "pack_size": product_data["pack_size"],
                    "description": product_data["description"],
                    "warnings": product_data["warnings"],
                    "side_effects": product_data["side_effects"],
                    "storage_instructions": product_data["storage_instructions"],
                    "mrp": Decimal(product_data["mrp"]),
                    "sale_price": Decimal(product_data["sale_price"]),
                    "requires_prescription": product_data["requires_prescription"],
                    "is_otc": product_data["is_otc"],
                    "is_active": True,
                    "stock_status": product_data["stock_status"],
                },
            )
            counts["products"] += int(product_created)
            product_map[product.slug] = product

        return counts
