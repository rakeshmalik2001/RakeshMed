import { expect, test } from "@playwright/test";

import { mockFinanceFlows, setAuthSession } from "./helpers";

test.describe("finance flow", () => {
  test("renders reconciliation and settlement detail workflows", async ({ page }) => {
    await setAuthSession(page, "finance");
    await mockFinanceFlows(page);

    await page.goto("/admin/reconciliation");
    await expect(page.getByRole("heading", { name: "Payment Reconciliation" })).toBeVisible();
    await expect(page.getByText("payment.captured")).toBeVisible();

    await page.getByTestId("save-reconciliation-snapshot-button").click();
    await expect(page.getByText("Checkpoint saved")).toBeVisible();

    await page.goto("/admin/settlements/71");
    await expect(page.getByRole("heading", { name: "Settlement SET-PLAY-001" })).toBeVisible();
    await page.getByTestId("mark-settlement-closed-button").click();
    await expect(page.getByText("Settlement batch moved to closed.")).toBeVisible();
  });
});
