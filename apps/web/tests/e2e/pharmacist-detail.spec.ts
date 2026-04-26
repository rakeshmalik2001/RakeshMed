import { expect, test } from "@playwright/test";

import { mockPharmacistQueue, setAuthSession } from "./helpers";

test.describe("pharmacist detail", () => {
  test("opens prescription detail and approves review", async ({ page }) => {
    await setAuthSession(page, "pharmacist");
    await mockPharmacistQueue(page);

    await page.goto("/pharmacist/prescriptions/RX-PLAY-001");
    await expect(page.getByRole("heading", { name: "Prescription detail review" })).toBeVisible();
    await page.getByRole("button", { name: "Approve" }).click();
    await expect(page.getByText("Approved by Pharmacist Example")).toBeVisible();
    await expect(page.getByText("Approved for dispensing")).toBeVisible();
  });
});
