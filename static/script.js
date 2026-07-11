const resultArea = document.getElementById("resultArea");

document.querySelectorAll(".tabBtn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabBtn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tabPane").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

function setStatus(id, msg, loading) {
  const el = document.getElementById(id);
  el.textContent = msg || "";
  el.classList.toggle("loading", !!loading);
}

async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "요청에 실패했습니다.");
  return data;
}

// Hymn
document.getElementById("hymnGoBtn").addEventListener("click", async () => {
  const number = document.getElementById("hymnNumber").value;
  if (!number) return setStatus("hymnStatus", "장 번호를 입력해주세요.");
  setStatus("hymnStatus", "가져오는 중... (AI 편집에는 몇 초 걸릴 수 있습니다)", true);
  resultArea.value = "";
  try {
    const data = await postJSON("/api/hymn", { number });
    resultArea.value = data.result;
    const note = data.mode === "rule" ? " (⚠ API 키 없어 규칙 기반으로 생성됨, 부정확할 수 있음)" : "";
    setStatus("hymnStatus", `완료: ${data.title}${note}`);
  } catch (e) {
    setStatus("hymnStatus", e.message);
  }
});

// CCM
document.getElementById("ccmSearchBtn").addEventListener("click", async () => {
  const query = document.getElementById("ccmQuery").value.trim();
  if (!query) return setStatus("ccmStatus", "검색어를 입력해주세요.");
  setStatus("ccmStatus", "검색 중...", true);
  document.getElementById("ccmResults").innerHTML = "";
  try {
    const data = await postJSON("/api/ccm/search", { query });
    setStatus("ccmStatus", data.results.length ? "곡을 선택하세요." : "검색 결과가 없습니다.");
    const box = document.getElementById("ccmResults");
    data.results.forEach(r => {
      const div = document.createElement("div");
      div.className = "resultItem";
      div.innerHTML = `<div class="t"></div><div class="a"></div>`;
      div.querySelector(".t").textContent = r.title;
      div.querySelector(".a").textContent = r.artist;
      div.addEventListener("click", () => loadCcmLyrics(r.trackId));
      box.appendChild(div);
    });
  } catch (e) {
    setStatus("ccmStatus", e.message);
  }
});

async function loadCcmLyrics(trackId) {
  setStatus("ccmStatus", "가사 가져오는 중... (AI 편집에는 몇 초 걸릴 수 있습니다)", true);
  resultArea.value = "";
  try {
    const data = await postJSON("/api/ccm/lyrics", { trackId });
    resultArea.value = data.result;
    const note = data.mode === "rule" ? " (⚠ API 키 없어 규칙 기반으로 생성됨, 부정확할 수 있음)" : "";
    setStatus("ccmStatus", `완료: ${data.title}${note}`);
  } catch (e) {
    setStatus("ccmStatus", e.message);
  }
}

// Bible
const bookSelect = document.getElementById("bibleBook");
window.BOOKS.forEach(name => {
  const opt = document.createElement("option");
  opt.value = name;
  opt.textContent = name;
  bookSelect.appendChild(opt);
});

document.getElementById("bibleGoBtn").addEventListener("click", async () => {
  const book = bookSelect.value;
  const chapter = document.getElementById("bibleChapter").value;
  const start = document.getElementById("bibleStart").value;
  const end = document.getElementById("bibleEnd").value || start;
  if (!chapter || !start) return setStatus("bibleStatus", "장과 시작절을 입력해주세요.");
  setStatus("bibleStatus", "가져오는 중...", true);
  resultArea.value = "";
  try {
    const data = await postJSON("/api/bible", { book, chapter, start, end });
    resultArea.value = data.result;
    setStatus("bibleStatus", "완료");
  } catch (e) {
    setStatus("bibleStatus", e.message);
  }
});

// Ad (announcement image -> text)
let adImage = null; // { base64, mediaType }

function loadAdImageFromFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  const reader = new FileReader();
  reader.onload = () => {
    const dataUrl = reader.result;
    adImage = { base64: dataUrl.split(",")[1], mediaType: file.type };
    const preview = document.getElementById("adPreview");
    preview.src = dataUrl;
    preview.style.display = "block";
    document.getElementById("adDropHint").style.display = "none";
    setStatus("adStatus", "");
  };
  reader.readAsDataURL(file);
}

const adDropZone = document.getElementById("adDropZone");
const adFileInput = document.getElementById("adFileInput");

document.getElementById("adFilePickLink").addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();
  adFileInput.click();
});

adFileInput.addEventListener("change", () => {
  if (adFileInput.files[0]) loadAdImageFromFile(adFileInput.files[0]);
});

adDropZone.addEventListener("paste", (e) => {
  const item = [...e.clipboardData.items].find(i => i.type.startsWith("image/"));
  if (item) loadAdImageFromFile(item.getAsFile());
});

adDropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  adDropZone.classList.add("dragOver");
});
adDropZone.addEventListener("dragleave", () => adDropZone.classList.remove("dragOver"));
adDropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  adDropZone.classList.remove("dragOver");
  if (e.dataTransfer.files[0]) loadAdImageFromFile(e.dataTransfer.files[0]);
});

document.getElementById("adGoBtn").addEventListener("click", async () => {
  if (!adImage) return setStatus("adStatus", "이미지를 먼저 붙여넣거나 선택해주세요.");
  setStatus("adStatus", "변환 중...", true);
  resultArea.value = "";
  try {
    const data = await postJSON("/api/ad", {
      image: adImage.base64, mediaType: adImage.mediaType,
    });
    resultArea.value = data.result;
    setStatus("adStatus", "완료");
  } catch (e) {
    setStatus("adStatus", e.message);
  }
});

// Copy
document.getElementById("copyBtn").addEventListener("click", () => {
  if (!resultArea.value) return;
  navigator.clipboard.writeText(resultArea.value).then(() => {
    const btn = document.getElementById("copyBtn");
    const orig = btn.textContent;
    btn.textContent = "복사됨!";
    setTimeout(() => (btn.textContent = orig), 1200);
  });
});
