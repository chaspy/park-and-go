const API_BASE = "http://127.0.0.1:8787";
const WEB_UI_BASE = "http://127.0.0.1:3000";

const VERDICT_LABELS = {
  onsite: "専用駐車場あり",
  partner: "提携駐車場",
  nearby_only: "近隣パーキング",
  unknown: "不明",
  avoid: "駐車困難",
};

let currentPlaceInfo = null;

async function init() {
  const statusEl = document.getElementById("status");
  const analyzeBtn = document.getElementById("analyze-btn");
  const placeInfoEl = document.getElementById("place-info");

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab?.url?.includes("google.com/maps")) {
      statusEl.textContent = "Google Mapsのページで使用してください";
      return;
    }

    // Try to get info from content script
    let info = null;
    try {
      info = await chrome.tabs.sendMessage(tab.id, { type: "GET_PLACE_INFO" });
    } catch {
      // Content script may not be loaded; fall back to URL only
      info = { url: tab.url, name: null, address: null, lat: null, lng: null };
    }

    currentPlaceInfo = info;

    if (info.name) {
      placeInfoEl.innerHTML = `<strong>${info.name}</strong>`;
      if (info.address) {
        placeInfoEl.innerHTML += `<br><span style="color:#666">${info.address}</span>`;
      }
      statusEl.textContent = "情報を取得しました";
    } else {
      statusEl.textContent = "URL情報のみ取得 (店名は自動抽出できませんでした)";
    }

    analyzeBtn.style.display = "block";
    analyzeBtn.addEventListener("click", () => runAnalysis(false));
  } catch (err) {
    statusEl.textContent = "情報の取得に失敗しました";
    console.error(err);
  }
}

async function runAnalysis(forceRefresh) {
  const analyzeBtn = document.getElementById("analyze-btn");
  const errorEl = document.getElementById("error");
  const resultEl = document.getElementById("result");

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "解析中...";
  errorEl.style.display = "none";
  resultEl.style.display = "none";

  const body = {
    google_maps_url: currentPlaceInfo?.url || undefined,
    name: currentPlaceInfo?.name || undefined,
    address: currentPlaceInfo?.address || undefined,
    lat: currentPlaceInfo?.lat || undefined,
    lng: currentPlaceInfo?.lng || undefined,
    force_refresh: forceRefresh,
  };

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Analysis failed");
    }

    const data = await res.json();
    renderResult(data);
  } catch (err) {
    errorEl.textContent = `エラー: ${err.message}`;
    errorEl.style.display = "block";
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "駐車場を判定";
  }
}

function renderResult(data) {
  const resultEl = document.getElementById("result");
  resultEl.style.display = "block";

  let html = `
    <div class="result-header">
      <h2>${data.place_name}</h2>
      <span class="badge badge-${data.verdict}">
        ${VERDICT_LABELS[data.verdict] || data.verdict}
      </span>
    </div>
    <div style="color:#888;font-size:12px">信頼度: ${Math.round(data.confidence * 100)}%</div>
    <p class="summary">${data.summary}</p>
  `;

  if (data.evidence.length > 0) {
    html += `<div class="section-title">根拠</div><ul>`;
    for (const ev of data.evidence) {
      html += `<li><span class="evidence-source">[${ev.source}]</span> ${ev.text}</li>`;
    }
    html += `</ul>`;
  }

  if (data.nearby_parking.length > 0) {
    html += `<div class="section-title">近隣駐車場</div><ul>`;
    for (const p of data.nearby_parking) {
      html += `<li class="parking-item"><span>${p.name}</span><span class="parking-dist">${p.distance_m}m (徒歩${p.walking_minutes}分)</span></li>`;
    }
    html += `</ul>`;
  }

  html += `
    <div class="actions">
      <button onclick="runAnalysis(true)">再判定</button>
      <a href="${WEB_UI_BASE}" target="_blank">Web UIで開く</a>
    </div>
  `;

  resultEl.innerHTML = html;
}

init();
