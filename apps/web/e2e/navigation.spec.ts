import { expect, test } from "@playwright/test";

const pages = [
  ["/", "Command Center"],
  ["/signal-station", "Signal Station"],
  ["/automation-station", "Automation Station"],
  ["/market-weather", "Market Weather"],
  ["/decision-ledger", "Decision Ledger"],
  ["/positions-orders", "Positions & Orders"],
  ["/learning-lab", "Learning Lab"],
  ["/model-health", "Model Health"],
  ["/incidents-controls", "Incidents & Controls"],
  ["/settings", "Settings"],
] as const;

for (const [path, heading] of pages) {
  test(`renders ${heading}`, async ({ page }) => {
    await page.goto(path);

    await expect(
      page.getByRole("heading", { name: heading, level: 1 }),
    ).toBeVisible();
    await expect(page.getByText("fixture mode")).toBeVisible();
    await expect(page.getByLabel("Live trading status")).toBeVisible();
  });
}
