"""One-time manual login: opens Edge, you log in yourself, session gets saved."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

PROFILE_DIR = Path(__file__).parent / "chrome_profile"


async def manual_login():
    PROFILE_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="msedge",
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=90000)

        print("=" * 60)
        print("  LOG IN TO X MANUALLY IN THE BROWSER WINDOW")
        print("  Once you see your home feed, come back here")
        print("  and press Enter to save the session.")
        print("=" * 60)

        input("\nPress Enter after you've logged in...")

        # Verify
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(3000)

        if "login" in page.url.lower():
            print("[!] Still on login page. Try again.")
        else:
            print("[OK] Session saved! You can now run: python main.py scrape")

        await context.close()


if __name__ == "__main__":
    asyncio.run(manual_login())
