# Manual Cookie Extraction Guide

## Quick Method (Browser Console)

1. **Navigate to the protected page:**
   - Go to `https://datacrew.circle.so/`
   - Make sure you're logged in

2. **Open Developer Tools:**
   - Press `F12` or right-click → "Inspect"
   - Go to the **Console** tab

3. **Run the extraction script:**
   - Copy the contents of `extract_cookies.js`
   - Paste into the console
   - Press Enter
   - The cookie string will be displayed and copied to clipboard

## Alternative Method (Network Tab)

1. **Open Developer Tools:**
   - Press `F12`
   - Go to the **Network** tab

2. **Refresh the page:**
   - Press `F5` or click refresh
   - Wait for requests to load

3. **Find any request:**
   - Click on any request to `datacrew.circle.so`
   - Look at the **Request Headers** section

4. **Copy the Cookie header:**
   - Find the `Cookie:` header
   - Copy the entire value (everything after `Cookie: `)

## Alternative Method (Application Tab)

1. **Open Developer Tools:**
   - Press `F12`
   - Go to the **Application** tab (Chrome) or **Storage** tab (Firefox)

2. **Navigate to Cookies:**
   - Expand **Cookies** in the left sidebar
   - Click on `https://datacrew.circle.so`

3. **Copy cookies:**
   - You'll see a table of all cookies
   - You can manually construct the cookie string: `name1=value1; name2=value2`
   - Or use the browser console script above

## Using the Extracted Cookies

Once you have the cookie string, use it in the MCP tool:

```python
crawl_single_page(
    url="https://datacrew.circle.so/",
    cookies="your-cookie-string-here",
    chunk_size=1000,
    chunk_overlap=200
)
```

Or via REST API:

```bash
curl -X POST http://lambda-server:8000/api/v1/crawl/single \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://datacrew.circle.so/",
    "cookies": "your-cookie-string-here"
  }'
```

## Note on Authentication

Circle.so uses session-based authentication. You'll need:
- Session cookies (typically `_circle_session` or similar)
- Authentication cookies from your logged-in session

If cookies don't work, try extracting headers from the Network tab instead, or use the Playwright-based extraction method in `extract_and_crawl.py`.
