/**
 * Content script for Google Maps place pages.
 * Extracts store info and sends to the extension popup via chrome.runtime messages.
 *
 * Note: Google Maps DOM is fragile. This script isolates extraction logic
 * and falls back to URL-only mode when DOM extraction fails.
 */

function extractPlaceInfoFromDOM() {
  const info = {
    name: null,
    address: null,
    url: window.location.href,
    lat: null,
    lng: null,
    phone: null,
    website: null,
  };

  // Try to extract name from the heading
  const headingEl =
    document.querySelector('h1[data-attrid]') ||
    document.querySelector('h1') ||
    document.querySelector('[role="main"] h1');
  if (headingEl) {
    info.name = headingEl.textContent?.trim() || null;
  }

  // Try to extract address
  const addressEl = document.querySelector('[data-item-id="address"]');
  if (addressEl) {
    info.address = addressEl.textContent?.trim() || null;
  }

  // Try to extract phone
  const phoneEl = document.querySelector('[data-item-id^="phone"]');
  if (phoneEl) {
    info.phone = phoneEl.textContent?.trim() || null;
  }

  // Try to extract website
  const websiteEl = document.querySelector('[data-item-id="authority"]');
  if (websiteEl) {
    const link = websiteEl.querySelector('a');
    if (link) {
      info.website = link.href || null;
    }
  }

  // Extract coordinates from URL
  const coordMatch = window.location.href.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
  if (coordMatch) {
    info.lat = parseFloat(coordMatch[1]);
    info.lng = parseFloat(coordMatch[2]);
  }

  return info;
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.type === "GET_PLACE_INFO") {
    const info = extractPlaceInfoFromDOM();
    sendResponse(info);
  }
  return true;
});
