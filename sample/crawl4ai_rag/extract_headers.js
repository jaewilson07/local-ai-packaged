/**
 * Browser Console Script to Extract Headers (for Cloudflare Access)
 *
 * Instructions:
 * 1. Navigate to https://datacrew.circle.so/ in your browser
 * 2. Make sure you're logged in
 * 3. Open Developer Tools (F12)
 * 4. Go to Network tab
 * 5. Refresh the page
 * 6. Click on any request
 * 7. Go to Console tab
 * 8. Run: extractHeaders()
 * 9. Copy the output
 */

function extractHeaders() {
    console.log('='.repeat(80));
    console.log('To extract headers:');
    console.log('1. Go to Network tab');
    console.log('2. Click on any request to datacrew.circle.so');
    console.log('3. Look at Request Headers section');
    console.log('4. Copy the following headers if present:');
    console.log('   - Cf-Access-Jwt-Assertion');
    console.log('   - CF-Access-Token');
    console.log('   - Authorization');
    console.log('   - Cookie');
    console.log('='.repeat(80));

    // Try to get headers from Performance API (limited)
    if (performance.getEntriesByType) {
        const entries = performance.getEntriesByType('resource');
        console.log('\nAvailable resources:');
        entries.forEach(entry => {
            if (entry.name.includes('datacrew.circle.so')) {
                console.log(`- ${entry.name}`);
            }
        });
    }

    return {
        note: 'Headers must be extracted manually from Network tab',
        importantHeaders: [
            'Cf-Access-Jwt-Assertion',
            'CF-Access-Token',
            'Authorization',
            'Cookie'
        ]
    };
}

// Auto-run
extractHeaders();
