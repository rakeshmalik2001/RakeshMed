import { expect, test } from "@playwright/test";

import { mockPrescriptionUpload, setAuthSession } from "./helpers";

test.describe("upload prescription", () => {
  test("submits a prescription and lands on submitted status page", async ({ page }) => {
    await setAuthSession(page, "customer");
    await mockPrescriptionUpload(page);

    await page.goto("/upload-prescription");
    await page.setInputFiles('[data-testid="prescription-file-input"]', {
      name: "rx-upload.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("fake-image")
    });
    await page.getByTestId("prescription-patient-name").fill("Playwright User");
    await page.getByTestId("prescription-doctor-name").fill("Dr Example");
    await page.getByTestId("submit-prescription-button").click();

    await expect
      .poll(async () =>
        page.evaluate(() => window.localStorage.getItem("netmeds-prescription"))
      )
      .toContain("RX-UP-001");

    await page.goto("/upload-prescription/submitted");
    await expect(page.getByRole("heading", { name: "Prescription submitted successfully" })).toBeVisible();
  });
});
