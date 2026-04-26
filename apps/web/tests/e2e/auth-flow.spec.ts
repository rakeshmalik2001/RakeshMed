import { expect, test } from "@playwright/test";

import { mockOtpAuth } from "./helpers";

test.describe("auth flow", () => {
  test("supports login and otp verification flow", async ({ page }) => {
    await mockOtpAuth(page);

    await page.goto("/verify-otp?phone=7002579537&next=%2Faccount");
    await expect(page.getByRole("heading", { name: "Verify one-time password" })).toBeVisible();

    await page.getByTestId("verify-otp-input").fill("123456");
    await page.getByTestId("verify-otp-button").click();

    await expect(page.getByText("Welcome, Playwright User.")).toBeVisible();
    await expect
      .poll(async () =>
        page.evaluate(() => window.localStorage.getItem("rakeshmed-auth-token"))
      )
      .toBe("playwright-token");
  });
});
