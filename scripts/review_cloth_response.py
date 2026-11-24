"""Measure actual uploaded cloth response, propagation and release duration."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


PROBE = """(()=>{
  window.__clothResponse=[];
  const original=WebGLRenderingContext.prototype.bufferData;
  WebGLRenderingContext.prototype.bufferData=function(target,data,usage){
    if(this.canvas.classList.contains('awning-fabric')&&target===this.ARRAY_BUFFER&&data instanceof Float32Array){
      let peakY=0,left=1,right=0,pinnedMax=0;
      for(let i=0;i<data.length;i+=5){
        const y=Math.abs(data[i+3]);peakY=Math.max(peakY,y);
        if(y>=.5){left=Math.min(left,data[i]);right=Math.max(right,data[i]);}
        const u=data[i],v=data[i+1];
        if(u===0||u===1||[0,16/300,182/300,190/300].some(row=>Math.abs(v-row)<.00001)){
          pinnedMax=Math.max(pinnedMax,Math.abs(data[i+2]),y);
        }
      }
      window.__clothResponse.push({time:performance.now(),peakY,pinnedMax,spread:Math.max(0,right-left)*this.canvas.getBoundingClientRect().width});
    }
    return original.call(this,target,data,usage);
  };
})()"""


def scroll_gust(page, delta):
    awning = page.locator(".site-awning")
    bounds = awning.bounding_box()
    start = page.evaluate("""delta=>{
      window.__clothResponse=[];const start=performance.now();
      scrollBy({top:delta,behavior:'instant'});return start;
    }""", delta)
    expect(awning).to_have_attribute("data-fabric-state", "moving")
    page.wait_for_timeout(14600)
    expect(awning).to_have_attribute("data-fabric-state", "rest", timeout=26000)
    trace = page.evaluate("start=>window.__clothResponse.map(p=>({...p,seconds:(p.time-start)/1000}))", start)
    early = [sample for sample in trace if sample["seconds"] <= .65]
    late = {second: [sample for sample in trace if abs(sample["seconds"] - second) <= .5]
            for second in (5, 10, 14)}
    bound = min(26, bounds["height"] * .14)
    assert early and max(sample["peakY"] for sample in early) >= bound * .6, early
    assert max(sample["spread"] for sample in early) >= bounds["width"] * .7
    assert all(late.values()), "Actual uploaded late-gust frames are missing."
    assert max(sample["peakY"] for sample in late[5]) >= bound * .35
    assert max(sample["peakY"] for sample in late[10]) >= 1.5
    assert max(sample["peakY"] for sample in late[14]) >= 1
    assert all(sample["pinnedMax"] == 0 and sample["peakY"] <= 19.50001 for sample in trace)
    assert 18 <= trace[-1]["seconds"] <= 26, trace[-1]
    last_visible = max(sample["seconds"] for sample in trace if sample["peakY"] >= .25)
    assert last_visible >= 16, last_visible
    expect(page.locator("canvas.awning-fabric")).to_be_hidden()
    count = page.evaluate("window.__clothResponse.length")
    page.wait_for_timeout(400)
    assert page.evaluate("window.__clothResponse.length") == count
    return {
        "delta": delta, "viewport_width": page.viewport_size["width"],
        "initial_peak_y": max(sample["peakY"] for sample in early),
        "initial_spread": max(sample["spread"] for sample in early),
        "late_peaks": {second: max(sample["peakY"] for sample in samples) for second, samples in late.items()},
        "last_quarter_pixel_motion_seconds": last_visible, "exact_idle_seconds": trace[-1]["seconds"],
        "pinned_offset": 0, "idle_uploads": 0, "trace": trace,
    }


def review(url, output):
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=["--mute-audio"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script(PROBE)
        page.goto(url + "#home", wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.evaluate("scrollTo({top:0,behavior:'instant'})")
        awning = page.locator(".site-awning")
        expect(awning).to_have_attribute("data-fabric-state", "rest", timeout=26000)
        bounds = awning.bounding_box()
        start = page.evaluate("()=>{window.__clothResponse=[];return performance.now()}")
        page.mouse.move(bounds["width"] / 2, bounds["y"] + bounds["height"] * .86)
        page.wait_for_timeout(650)
        early = page.evaluate("start=>window.__clothResponse.filter(p=>p.time-start<=650)", start)
        assert early and max(p["peakY"] for p in early) >= 12, early
        assert max(p["spread"] for p in early) >= 700, early
        expect(awning).to_have_attribute("data-fabric-state", "held", timeout=10000)
        release = page.evaluate("()=>{window.__clothResponse=[];return performance.now()}")
        page.mouse.move(20, 20)
        page.wait_for_timeout(2450)
        tail = page.evaluate("start=>window.__clothResponse.filter(p=>p.time-start>=1600&&p.time-start<=2400)", release)
        assert tail and max(p["peakY"] for p in tail) >= .4, "The visible reaction must linger after the pointer leaves."
        expect(awning).to_have_attribute("data-fabric-state", "rest", timeout=10000)
        trace = page.evaluate("start=>window.__clothResponse.map(p=>({...p,seconds:(p.time-start)/1000}))", release)
        rest_seconds = trace[-1]["seconds"]
        assert 4 <= rest_seconds <= 8.5, rest_seconds
        visible_seconds = max(p["seconds"] for p in trace if p["peakY"] >= .25)
        assert visible_seconds >= 2.3, visible_seconds
        expect(page.locator("canvas.awning-fabric")).to_be_hidden()
        count = page.evaluate("window.__clothResponse.length")
        page.wait_for_timeout(400)
        assert page.evaluate("window.__clothResponse.length") == count
        gusts = [scroll_gust(page, delta) for delta in (60, -60)]
        touch = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        mobile = touch.new_page()
        mobile.add_init_script(PROBE)
        mobile.goto(url + "#home", wait_until="networkidle")
        mobile.evaluate("document.fonts.ready")
        mobile.evaluate("scrollTo({top:0,behavior:'instant'})")
        expect(mobile.locator(".site-awning")).to_have_attribute("data-fabric-state", "rest", timeout=26000)
        gusts.append(scroll_gust(mobile, 60))
        touch.close()
        assert not errors, errors
        result = {
            "status": "passed", "url": url, "viewport": [1440, 1000],
            "peak_screen_displacement_first_650ms": max(p["peakY"] for p in early),
            "affected_width_first_650ms": max(p["spread"] for p in early),
            "release_peak_1600_to_2400ms": max(p["peakY"] for p in tail),
            "last_quarter_pixel_motion_seconds": visible_seconds,
            "exact_rest_seconds": rest_seconds, "idle_uploads": 0,
            "early_trace": early, "release_trace": trace, "image_tool_views": 0,
            "scroll_gusts": gusts,
        }
        browser.close()
    (output / "review.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if not key.endswith("_trace")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:4173/")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review(args.url, args.output)
