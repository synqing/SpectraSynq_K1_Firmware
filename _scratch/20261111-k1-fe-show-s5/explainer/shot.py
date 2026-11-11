import sys
from playwright.sync_api import sync_playwright
H="/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/audio-forensics/design/k1-audio-front-end.html"
with sync_playwright() as p:
    b=p.chromium.launch()
    for w,scheme in ((1280,"light"),(500,"light"),(500,"dark")):
        pg=b.new_page(viewport={"width":w,"height":900},color_scheme=scheme); pg.goto("file://"+H); pg.wait_for_timeout(800)
        print(w,scheme,"scrollW",pg.evaluate("document.documentElement.scrollWidth"))
        for sid in ("s2","s3"):
            pg.locator("#"+sid).locator("xpath=..").screenshot(path=f"{sid}_{w}_{scheme}.png")
        if scheme=="light": pg.screenshot(path=f"full_{w}.png",full_page=True)
    b.close()
