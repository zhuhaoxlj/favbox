// Test sync API
const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzY0Njk5NTg1fQ.o7V6Z0OwZyqVcgEhSqX2tyrCbZZUQjnS1sOjtocdCAg";

async function testSync() {
  try {
    // Test with sample bookmark data
    const sampleBookmark = {
      browser_id: "test-123",
      url: "https://example.com",
      title: "Test Bookmark",
      description: null,
      domain: "example.com",
      favicon: null,
      image: null,
      tags: [],
      keywords: [],
      notes: null,
      folder_name: null,
      folder_id: null,
      pinned: 0,
      http_status: null,
      date_added: Date.now(),
      updated_at: null,
      deleted: false
    };

    const response = await fetch('http://localhost:8000/api/bookmarks/sync', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${TOKEN}`
      },
      body: JSON.stringify({
        bookmarks: [sampleBookmark],
        client_timestamp: new Date().toISOString()
      })
    });

    console.log('Status:', response.status);
    console.log('Status Text:', response.statusText);

    const text = await response.text();
    console.log('Response:', text);

    if (response.ok) {
      const data = JSON.parse(text);
      console.log('Success! Synced bookmarks:', data.bookmarks.length);
    } else {
      console.error('Error response:', text);
    }
  } catch (error) {
    console.error('Request failed:', error);
  }
}

testSync();
