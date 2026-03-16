#!/usr/bin/env python

import argparse
import re
import subprocess
import tomllib

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

DEFAULT_TIMEOUT = 2000
verbose = False
base_url = "http://localhost:5844"


def log(msg):
    if verbose:
        print(f"  {msg}")


def reset_database():
    log("resetting database")
    subprocess.run(
        [
            "docker", "compose",
            "-f", "docker-compose.test.yml",
            "-p", "your5e-test",
            "exec", "-T", "db-test",
            "psql", "-U", "your5e", "postgres",
        ],
        input=b"""
            SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity WHERE datname = 'your5e_test';
            DROP DATABASE IF EXISTS your5e_test;
            CREATE DATABASE your5e_test WITH TEMPLATE your5e_seed;
        """,
        capture_output=True,
    )


def load_config():
    config_path = "scrying/scry.toml"
    with open(config_path, "rb") as handle:
        return tomllib.load(handle)


def login(page, username, password):
    log(f"logging in as {username}")
    page.goto(base_url + "/login")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(base_url + "/**")
    log(f"logged in, now at {page.url}")


def logout(page):
    log("logging out")
    page.context.clear_cookies()


class StepError(Exception):
    pass


def execute_steps(page, steps):
    scope = page

    for step in steps:
        step_type = list(step.keys())[0]
        params = step[step_type]
        timeout = params.get("timeout", DEFAULT_TIMEOUT)

        try:
            if step_type == "form":
                selector = params["selector"]
                log(f"scoping to form: {selector}")
                scope = page.locator(selector)
                try:
                    scope.wait_for(timeout=timeout)
                except PlaywrightError:
                    raise StepError(f'form "{selector}" not found') from None
            elif step_type == "fill":
                field = params["field"]
                value = params["value"]
                log(f"fill {field} = {value}")
                locator = scope.locator(f'[name="{field}"]')
                try:
                    locator.fill(value, timeout=timeout)
                except PlaywrightError:
                    raise StepError(f'fill field "{field}" not found') from None
            elif step_type == "click":
                if "text" in params:
                    text = params["text"]
                    role = params.get("role")
                    if role:
                        log(f"click {role}: {text}")
                        locator = scope.get_by_role(role, name=text)
                    else:
                        log(f"click text: {text}")
                        locator = scope.get_by_text(text)
                elif "selector" in params:
                    selector = params["selector"]
                    log(f"click selector: {selector}")
                    locator = scope.locator(selector)
                with page.expect_navigation():
                    locator.click(timeout=timeout)
                log(f"clicked, now at {page.url}")
        except PlaywrightError as e:
            msg = str(e)
            if "strict mode violation" in msg:
                match = re.search(r'resolved to (\d+) elements', msg)
                if match:
                    count = match.group(1)
                else:
                    count = "multiple"
                raise StepError(f'{step_type} matched {count} elements') from None
            if "Timeout" in msg:
                raise StepError(f'{step_type} timed out') from None
            raise


def screenshot(page, name, widths):
    print(f"{name}:")
    for size, width in widths.items():
        page.set_viewport_size({"width": width, "height": 800})

        rendered_width = page.evaluate("document.documentElement.scrollWidth")
        overflow = rendered_width > width

        if overflow:
            page_height = page.evaluate("document.documentElement.scrollHeight")
            page.evaluate(f"""
                const overlay = document.createElement('div');
                overlay.id = 'scry-overflow-overlay';
                overlay.style.cssText = `
                    position: absolute;
                    top: 0;
                    left: {width}px;
                    width: {rendered_width - width}px;
                    height: {page_height}px;
                    background: rgba(0, 0, 0, 0.2);
                    z-index: 999999;
                    pointer-events: none;
                `;
                document.body.appendChild(overlay);
            """)

        filename = name + "-" + size + ".png"
        filepath = "scrying/" + filename
        page.screenshot(path=filepath, full_page=True)

        img_width = page.evaluate("document.documentElement.scrollWidth")
        img_height = page.evaluate("document.documentElement.scrollHeight")

        if overflow:
            print(
                f"    - {size}: {filename} "
                f"(WIDTH OVERFLOW {rendered_width}px > {width}px)"
            )
            page.evaluate(
                "document.getElementById('scry-overflow-overlay')?.remove()"
            )
        else:
            print(f"    - {size}: {filename} ({img_width}px x {img_height}px)")


def main():
    global verbose

    parser = argparse.ArgumentParser(
        description="Take screenshots of the dev server",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="verbose output",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="skip database reset",
    )
    parser.add_argument(
        "pages",
        nargs="*",
        help="specific pages to screenshot",
    )
    args = parser.parse_args()

    verbose = args.verbose

    if not args.no_reset:
        reset_database()

    config = load_config()
    all_widths = config.get("widths", {})
    users = config.get("users", {})
    all_pages = config.get("pages", {})
    current_user = None

    pages = all_pages
    if args.pages:
        pages = {}
        for name, spec in all_pages.items():
            if name in args.pages:
                pages[name] = spec

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for name, spec in pages.items():
            required_user = spec.get("user")
            log(f"processing {name} (user={required_user})")

            try:
                if required_user != current_user:
                    if current_user is not None:
                        logout(page)
                    if required_user is not None:
                        password = users[required_user]
                        login(page, required_user, password)
                    current_user = required_user

                if "path" in spec:
                    log(f"goto {spec['path']}")
                    page.goto(base_url + spec["path"])
                    log(f"now at {page.url}")
                if "steps" in spec:
                    execute_steps(page, spec["steps"])

                page_widths = spec.get("widths")
                if page_widths is None:
                    widths = dict(all_widths)
                else:
                    widths = {
                        k: all_widths[k]
                            for k in page_widths
                    }

                for extra in spec.get("add_widths", []):
                    widths[extra["name"]] = extra["value"]

                screenshot(page, name, widths)

            except (StepError, PlaywrightError) as e:
                print(f"{name}:")
                print(f"    ERROR: {e}")

        browser.close()


if __name__ == "__main__":
    main()
