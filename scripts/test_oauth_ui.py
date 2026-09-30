#!/usr/bin/env python3
"""Synthetic browser check for the dedicated Paper OAuth surface; no GitHub credentials."""
from __future__ import annotations
import argparse
import base64
import functools
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=Path, default=ROOT / 'dist/site')
    parser.add_argument('--output', type=Path, default=ROOT / 'test-results')
    args = parser.parse_args()
    site = args.site.resolve()
    if not (site / 'index.html').is_file() or not (site / 'oauth-ui.mjs').is_file():
        raise SystemExit('Build the Paper site first, or provide --site with built assets')
    args.output.mkdir(parents=True, exist_ok=True)
    port = free_port()
    origin = f'http://127.0.0.1:{port}'
    env = os.environ.copy()
    env.update({
        'PORT': str(port),
        'PUBLIC_BASE_URL': origin,
        'PAPER_SITE_ORIGIN': origin,
        'PAPER_SITE_DIR': str(site),
        'ALLOW_INSECURE_LOCAL': '1',
        'GITHUB_APP_CLIENT_ID': 'Iv1.synthetic-browser-test',
        'GITHUB_APP_CLIENT_SECRET': 'synthetic-browser-secret',
        'COOKIE_KEY_BASE64URL': base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip('='),
    })
    gateway = subprocess.Popen(['node', 'auth-gateway/server.mjs'], cwd=ROOT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    static = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(site)))
    thread = threading.Thread(target=static.serve_forever, daemon=True)
    thread.start()
    try:
        for _ in range(80):
            if gateway.poll() is not None:
                raise RuntimeError('Synthetic gateway exited: ' + gateway.stderr.read().decode()[-1200:])
            try:
                with urllib.request.urlopen(origin + '/auth/config', timeout=1) as response:
                    assert json.load(response)['mode'] == 'github-app'
                break
            except Exception:
                time.sleep(.1)
        else:
            raise RuntimeError('Synthetic gateway did not become ready')
        chrome = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=chrome if chrome else None)
            context = browser.new_context(viewport={'width': 390, 'height': 844})
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda err: errors.append(str(err)))
            page.goto(origin + '/#/sync', wait_until='domcontentloaded')
            page.locator('#paper-oauth-panel').wait_for(timeout=30000)
            assert page.locator('#vault-connect').is_hidden()
            assert page.locator('#personal-status-panel').is_hidden()
            assert page.get_by_role('button', name='使用 GitHub 登录').is_enabled()
            assert page.get_by_role('button', name='立即核对云端').is_disabled()
            assert '仅保存在本机' in page.locator('#paper-oauth-badge').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 3')
            page.screenshot(path=str(args.output / 'oauth-ui-mobile.png'), full_page=True)
            page.route('**/auth/config', lambda route: route.abort())
            page.reload(wait_until='domcontentloaded')
            page.locator('#paper-oauth-panel').wait_for(timeout=30000)
            assert page.locator('#vault-connect').is_hidden()
            assert not errors, errors
            mirror = browser.new_context()
            plain = mirror.new_page()
            static_origin = f'http://127.0.0.1:{static.server_address[1]}'
            plain.goto(static_origin + '/#/sync', wait_until='domcontentloaded')
            plain.locator('#vault-connect').wait_for(timeout=30000)
            assert plain.locator('#paper-oauth-panel').count() == 0
            assert plain.locator('#vault-connect').is_visible()
            mirror.close()
            context.close()
            browser.close()
        report = {'passed': True, 'checks': 10, 'credentials': 'synthetic only'}
        (args.output / 'oauth-ui-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report))
    finally:
        static.shutdown()
        static.server_close()
        gateway.terminate()
        try:
            gateway.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gateway.kill()
            gateway.wait(timeout=5)


if __name__ == '__main__':
    main()

