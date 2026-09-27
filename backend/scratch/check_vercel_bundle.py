import httpx
import re

url = "https://smart-resort360.vercel.app"
r = httpx.get(url)
js_files = re.findall(r'src="(/assets/[^"]+)"', r.text)

print(f"Checking JS files from {url}: {js_files}")

for js_path in js_files:
    js_url = url + js_path
    js_resp = httpx.get(js_url)
    content = js_resp.text
    
    # Check for onrender URLs or localhost
    render_matches = re.findall(r'https?://[a-zA-Z0-9.-]+\.onrender\.com[^\s\'"]*', content)
    localhost_matches = re.findall(r'http://localhost:[0-9]+[^\s\'"]*', content)
    
    print(f"\n--- {js_path} ---")
    print(f"Render URLs found: {set(render_matches)}")
    print(f"Localhost URLs found: {set(localhost_matches)}")
