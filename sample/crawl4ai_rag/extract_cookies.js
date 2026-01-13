/**
 * Browser Console Script to Extract Cookies
 *
 * Instructions:
 * 1. Navigate to https://datacrew.circle.so/ in your browser
 * 2. Make sure you're logged in
 * 3. Open Developer Tools (F12)
 * 4. Go to Console tab
 * 5. Paste this entire script and press Enter
 * 6. Copy the output cookie string
 */

(function() {
    // Get all cookies for the current domain
    const cookies = document.cookie;

    // Format as cookie string (ready to use in MCP tool)
    const cookieString = cookies;

    // Also format as individual cookie pairs
    const cookiePairs = cookies.split('; ').map(cookie => {
        const [name, value] = cookie.split('=');
        return { name, value };
    });

    console.log('='.repeat(80));
    console.log('COOKIE STRING (ready to use):');
    console.log('='.repeat(80));
    console.log(cookieString);
    console.log('\n');

    console.log('='.repeat(80));
    console.log('COOKIE DICT FORMAT (alternative):');
    console.log('='.repeat(80));
    const cookieDict = {};
    cookiePairs.forEach(({ name, value }) => {
        cookieDict[name] = value;
    });
    console.log(JSON.stringify(cookieDict, null, 2));
    console.log('\n');

    console.log('='.repeat(80));
    console.log('INDIVIDUAL COOKIES:');
    console.log('='.repeat(80));
    cookiePairs.forEach(({ name, value }) => {
        console.log(`${name}: ${value}`);
    });
    console.log('\n');

    // Copy to clipboard if possible
    if (navigator.clipboard) {
        navigator.clipboard.writeText(cookieString).then(() => {
            console.log('✅ Cookie string copied to clipboard!');
        }).catch(err => {
            console.log('⚠️ Could not copy to clipboard:', err);
        });
    }

    return {
        cookieString,
        cookieDict,
        cookies: cookiePairs
    };
})();
