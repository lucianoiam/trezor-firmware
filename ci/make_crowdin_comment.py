import json
import sys

(RUN_ID, LANGS_JSON) = sys.argv[1:]
MAIN = json.loads(LANGS_JSON)

REPORT_URL = f"https://data.trezor.io/dev/firmware/ui_report/{RUN_ID}"
CI_RUN_URL = f"https://github.com/trezor/trezor-firmware/actions/runs/{RUN_ID}"
TEST_TYPES = ["device_test", "click_test"]
MODELS = [
    "T2T1",
    "T3B1",
    "T3T1",
    "T3W1",
]
LAYOUTS = [
    "Bolt",
    "Caesar",
    "Delizia",
    "Eckhart",
]
LANG_NAMES = {
    "cs": "Czech",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
}


def display_lang(code: str) -> str:
    return LANG_NAMES.get(code, code)  # fallback to the code if unknown


def main():
    # a special marker for finding this comment (via CI)
    print("<!-- ui-comment-Core -->")
    for lang in MAIN:
        print_table(lang)

    print(f"\nLatest CI run: [{RUN_ID}]({CI_RUN_URL})")


def print_table(lang):
    print(f"\n#`{display_lang(lang)}`\n")

    header = ["layout"] + TEST_TYPES
    print("|".join(header))
    print("|".join(["-"] * len(header)))

    for model, layout in zip(MODELS, LAYOUTS):
        row = [f"{layout}"]
        for test_type in TEST_TYPES:
            test_prefix = f"{REPORT_URL}/{model}-{lang}-core_{test_type}"

            test_diff = f"[UI flows]({test_prefix}-index.html)"

            cell = f"{test_diff}"
            row.append(cell)

        print("|".join(row))


if __name__ == "__main__":
    main()
