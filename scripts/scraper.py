import asyncio
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.skillindiadigital.gov.in/training-centres"

PAGE_SIZE = 18

#Use a NEW CSV for the fresh all-state scrape
CSV_FILE = Path("../data/raw/all_states_training_centres.csv")

#STATES
#EXACT ORDER OF THE RADIO BUTTONS

STATES = [
    "uttar pradesh",
    "rajasthan",
    "karnataka",
    "bihar",
    "maharashtra",
    "madhya pradesh",
    "odisha",
    "gujarat",
    "tamil nadu",
    "kerala",
    "andhra pradesh",
    "haryana",
    "punjab",
    "west bengal",
    "jharkhand",
    "telangana",
    "himachal pradesh",
    "chhattisgarh",
    "uttarakhand",
    "jammu and kashmir",
    "assam",
    "delhi",
    "tripura",
    "manipur",
    "nagaland",
    "arunachal pradesh",
    "meghalaya",
    "puducherry",
    "goa",
    "mizoram",
    "sikkim",
    "chandigarh",
    "andaman and nicobar islands",
    "daman and diu",
    "ladakh",
    "dadra and nagar haveli",
    "lakshadweep",
    "gujrat",
]

#CSV COLUMNS

COLUMNS = [
    "state",
    "centre_name",
    "address",
    "email",
    "phone",
    "courses_offered",
]

#CLEAN TEXT

def clean(text):

    if text is None:
        return ""

    return " ".join(
        str(text).split()
    ).strip()

#DUPLICATE KEY

def make_key(row):

    return (
        clean(row["state"]).lower(),
        clean(row["centre_name"]).lower(),
        clean(row["address"]).lower(),
    )

#LOAD / CREATE CSV

if CSV_FILE.exists():

    df = pd.read_csv(
        CSV_FILE,
        dtype=str
    ).fillna("")

    # Make sure every required column exists
    for col in COLUMNS:

        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS]

else:

    df = pd.DataFrame(
        columns=COLUMNS
    )

#CREATE EXISTING KEY SET

existing_keys = set()

for _, row in df.iterrows():

    existing_keys.add(
        make_key(row)
    )
    
def save_csv():

    df.to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8-sig"
    )

def build_url(
    state,
    page_number
):

    return (
        f"{BASE_URL}"
        f"?PageNumber={page_number}"
        f"&PageSize={PAGE_SIZE}"
        f'&State=%22{state.upper()}%22'
    )

#SELECT STATE RADIO BUTTON

async def select_state(
    page,
    state
):

    print(
        f"Selecting: {state.upper()}"
    )

    try:

        radio = page.locator(
            f'input[type="radio"][name="{state}"]'
        )

        await radio.wait_for(
            state="visible",
            timeout=10000
        )

        if not await radio.is_checked():

            await radio.check()

            await page.wait_for_timeout(
                1500
            )

        print(
            f"Selected: {state.upper()}"
        )

        return True

    except Exception as e:

        print(
            f"ERROR selecting {state}: {e}"
        )

        return False

#OPEN STATE PAGE

async def open_state_page(
    page,
    state,
    page_number
):

    url = build_url(
        state,
        page_number
    )

    print()
    print("=" * 90)

    print(
        f"OPENING {state.upper()} "
        f"- PAGE {page_number}"
    )

    print("=" * 90)

    print(
        "URL:",
        url
    )

    #Navigate
    try:

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

    except Exception as e:

        print(
            "Navigation error:",
            e
        )

        return False

    #Allow Angular to load

    await page.wait_for_timeout(
        2000
    )

    # Select state
    await select_state(
        page,
        state
    )

    # Wait for cards

    try:

        await page.locator(
            "app-training-card"
        ).first.wait_for(
            state="visible",
            timeout=15000
        )

    except PlaywrightTimeoutError:

        print(
            "WARNING: Training cards "
            "did not appear."
        )


    await page.wait_for_timeout(
        1000
    )

    return True

#SCRAPE ONE TRAINING CENTRE

async def scrape_centre(
    page,
    card,
    state
):

    dialog = None

    try:
        #CLICK VIEW DETAILS
        button = card.get_by_role(
            "button",
            name="View Details"
        )

        await button.wait_for(
            state="visible",
            timeout=5000
        )

        await button.click()


        dialog = page.locator(
            'mat-dialog-container[role="dialog"]'
        ).last

        await dialog.wait_for(
            state="visible",
            timeout=10000
        )

        await page.wait_for_timeout(
            500
        )

        #CENTRE NAME
        centre_name = ""

        try:

            centre_name = clean(
                await dialog.locator(
                    'h1[mat-dialog-title]'
                ).inner_text()
            )

        except Exception:

            pass

        #PRIMARY DETAILS

        primary_details = []

        try:

            elements = dialog.locator(
                ".primary-detail p"
            )

            count = await elements.count()

            for i in range(count):

                try:

                    text = clean(
                        await elements.nth(i).inner_text()
                    )

                    if text:

                        primary_details.append(
                            text
                        )

                except Exception:

                    pass

        except Exception:

            pass

        #ADDRESS

        address = ""

        if len(primary_details) > 0:

            address = primary_details[0]

        #EMAIL
        email = ""

        for item in primary_details:

            if "@" in item:

                email = item

                break

        #PHONE
        phone = ""

        try:

            phone_link = dialog.locator(
                'p.training-center-mobile '
                'a[href^="tel:"]'
            )

            if await phone_link.count() > 0:

                phone = clean(
                    await phone_link.first.inner_text()
                )


                if not phone:

                    href = await phone_link.first.get_attribute(
                        "href"
                    )

                    if href:

                        phone = href.replace(
                            "tel:",
                            ""
                        ).strip()

        except Exception:

            pass

        #COURSES

        courses = []

        try:

            chips = dialog.locator(
                "mat-chip-listbox "
                "mat-chip-option "
                "span.mdc-evolution-chip__text-label."
                "mat-mdc-chip-action-label"
            )

            count = await chips.count()

            for i in range(count):

                try:

                    course = clean(
                        await chips.nth(i).inner_text()
                    )

                    if (
                        course
                        and course not in courses
                    ):

                        courses.append(
                            course
                        )

                except Exception:

                    pass

        except Exception:

            pass


        courses_offered = " | ".join(
            courses
        )
        try:

            close_button = dialog.locator(
                "button.skill-icon-close"
            )

            if await close_button.count() > 0:

                await close_button.first.click()

            else:

                await page.keyboard.press(
                    "Escape"
                )


            await dialog.wait_for(
                state="hidden",
                timeout=5000
            )

        except Exception:

            try:

                await page.keyboard.press(
                    "Escape"
                )

            except Exception:

                pass

            await page.wait_for_timeout(
                300
            )
        record = {

            "state": state.upper(),

            "centre_name": centre_name,

            "address": address,

            "email": email,

            "phone": phone,

            "courses_offered":
                courses_offered,
        }


        return record


    except Exception as e:

        print(
            "ERROR scraping centre:",
            str(e)[:300]
        )

        try:

            await page.keyboard.press(
                "Escape"
            )

            await page.wait_for_timeout(
                500
            )

        except Exception:

            pass


        return None

#SCRAPE ONE STATE

async def scrape_state(
    page,
    state
):

    global df
    global existing_keys


    print()
    print()
    print("#" * 90)

    print(
        f"STARTING STATE: {state.upper()}"
    )

    print(
        "STARTING FROM PAGE: 1"
    )

    print("#" * 90)


    page_number = 1


    while True:
        success = await open_state_page(
            page,
            state,
            page_number
        )


        if not success:
            print(
                f"Could not open "
                f"{state.upper()} page "
                f"{page_number}"
            )

            print(
                "Moving to next state..."
            )

            break

        cards = page.locator(
            "app-training-card"
        )

        card_count = await cards.count()


        print()
        print(
            f"{state.upper()} "
            f"PAGE {page_number} "
            f"-> {card_count} CARDS"
        )
        if card_count == 0:

            print(
                "No cards found."
            )

            print(
                f"Finished {state.upper()}."
            )

            break


        new_records = 0
        duplicate_records = 0
        failed_records = 0
        #SCRAPE EACH CARD
        for card_index in range(
            card_count
        ):

            print(
                f"[{state.upper()}] "
                f"Page {page_number} "
                f"Card {card_index + 1}/"
                f"{card_count}"
            )

            cards = page.locator(
                "app-training-card"
            )


            try:

                card = cards.nth(
                    card_index
                )

                await card.scroll_into_view_if_needed()

                await page.wait_for_timeout(
                    200
                )

            except Exception as e:

                print(
                    "Could not locate card:",
                    e
                )

                failed_records += 1

                continue

            #SCRAPE
            record = await scrape_centre(
                page,
                card,
                state
            )

            #FAILED
            if record is None:

                failed_records += 1

                print(
                    "  FAILED"
                )

                continue
            key = make_key(
                record
            )


            if key in existing_keys:

                duplicate_records += 1

                print(
                    "  DUPLICATE:",
                    record["centre_name"]
                )

                continue
            df.loc[len(df)] = record

            existing_keys.add(
                key
            )

            new_records += 1


            print(
                "  ADDED:",
                record["centre_name"]
            )


            print(
                "  Courses:",
                record["courses_offered"]
                if record["courses_offered"]
                else "(none)"
            )


            # Small delay
            await page.wait_for_timeout(
                250
            )

        save_csv()


        print()
        print("-" * 90)

        print(
            f"{state.upper()} "
            f"PAGE {page_number} COMPLETED"
        )

        print(
            f"New records       : "
            f"{new_records}"
        )

        print(
            f"Duplicates        : "
            f"{duplicate_records}"
        )

        print(
            f"Failed            : "
            f"{failed_records}"
        )

        print(
            f"Total CSV records : "
            f"{len(df)}"
        )

        print("-" * 90)
        if card_count < PAGE_SIZE:

            print()
            print(
                f"FINISHED: {state.upper()}"
            )

            print(
                f"Last page: {page_number}"
            )

            break
        page_number += 1

async def main():

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False
        )


        context = await browser.new_context(

            viewport={
                "width": 1400,
                "height": 900
            }

        )


        page = await context.new_page()

        total_states = len(STATES)


        for state_index, state in enumerate(
            STATES,
            start=1
        ):

            print()
            print()
            print("*" * 100)

            print(
                f"STATE {state_index}/{total_states}"
            )

            print(
                f"{state.upper()}"
            )

            print("*" * 100)


            try:

                await scrape_state(
                    page,
                    state
                )


            except Exception as e:

                print()
                print(
                    "=" * 90
                )

                print(
                    f"UNEXPECTED ERROR "
                    f"IN {state.upper()}"
                )

                print(
                    str(e)
                )

                print(
                    "Moving to next state..."
                )

                print(
                    "=" * 90
                )

        save_csv()


        print()
        print()
        print("=" * 100)

        print(
            "ALL STATES SCRAPING COMPLETED"
        )

        print("=" * 100)

        print(
            "Total records:",
            len(df)
        )

        print(
            "CSV file:",
            CSV_FILE.resolve()
        )

        print("=" * 100)


        await browser.close()

if __name__ == "__main__":

    asyncio.run(main())