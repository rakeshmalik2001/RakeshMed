import { expect, test } from "@playwright/test";

import { mockCustomerFlows, mockPrescriptionAccount, setAuthSession } from "./helpers";

test.describe("prescription flow", () => {
  test("renders account prescription list and detail", async ({ page }) => {
    await mockCustomerFlows(page);
    await mockPrescriptionAccount(page);
    await setAuthSession(page, "customer");

    await page.goto("/account/prescriptions");
    await expect(page.getByRole("heading", { name: "Prescription uploads" })).toBeVisible();
    await expect(page.getByText("RX-PLAY-001")).toBeVisible();

    await page.getByRole("link", { name: "Open detail" }).click();
    await expect(page).toHaveURL(/\/account\/prescriptions\/RX-PLAY-001$/);
    await expect(page.getByRole("heading", { name: "Prescription detail" })).toBeVisible();
    await expect(page.getByText("Approved for dispensing")).toBeVisible();
  });
});
