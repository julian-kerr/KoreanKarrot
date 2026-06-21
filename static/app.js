let items = [];
let idx = -1;

const q = document.getElementById("q");
const btn = document.getElementById("btn");
const resultsEl = document.getElementById("results");
const yt = document.getElementById("yt");
const nowPlaying = document.getElementById("nowPlaying");
const prevBtn = document.getElementById("prev");
const nextBtn = document.getElementById("next");
const dictionaryEl = document.getElementById("dictionary");


function ytUrl(youtubeId, startSeconds) {
  const s = Math.max(0, Math.floor(startSeconds));
  return `https://www.youtube.com/embed/${youtubeId}?start=${s}&autoplay=1`;
}

function highlight(text, query) {
  if (!query) return escapeHtml(text);
  const safe = escapeHtml(text);
  const qSafe = escapeHtml(query);
  return safe.replaceAll(qSafe, `<mark>${qSafe}</mark>`);
}

async function showDictionary(query) {
  dictionaryEl.classList.remove("hidden");
  dictionaryEl.innerHTML = "Loading dictionary...";

  const res = await fetch(`/dictionary?word=${encodeURIComponent(query)}`);
  const data = await res.json();

  if (!data.found) {
    dictionaryEl.innerHTML = `<strong>${escapeHtml(query)}</strong><br>No dictionary entry found.`;
    return;
  }

  const e = data.entry;

  dictionaryEl.innerHTML = `
    <div class="dictLabel">Dictionary</div>
    <div class="dictWord">${escapeHtml(e.word || query)}</div>
    <div class="dictInfo">
      ${e.pronunciation ? `Pronunciation: ${escapeHtml(e.pronunciation)}` : ""}
      ${e.pos ? ` · ${escapeHtml(e.pos)}` : ""}
      ${e.level ? ` · Level: ${escapeHtml(e.level)}` : ""}
      <button id="saveWordBtn">⭐ Save Word</button>
    </div>
    <div class="dictMeaning">${escapeHtml(e.definition || "No definition available.")}</div>
  `;
}

const saveBtn = document.getElementById("saveWordBtn");
if (saveBtn) {
  saveBtn.onclick = async () => {
    const res = await fetch("/save-word", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: `word=${encodedURIComponent(word)}`
    });

    const data = await res.json();

    if (data.ok) {
      saveBtn.textContent = "✅ Saved";
    }
    else{
      alert(data.error || "Failed to save word")
    }
  };
}

function translatePos(pos) {
  const map = {
    "명사": "Noun",
    "동사": "Verb",
    "형용사": "Adjective",
    "부사": "Adverb",
    "감탄사": "Interjection",
    "조사": "Particle",
    "대명사": "Pronoun",
    "수사": "Numeral",
    "관형사": "Determiner"
  };

  return map[pos] || pos;
}

function translateLevel(level) {
  const map = {
    "초급": "Beginner",
    "중급": "Intermediate",
    "고급": "Advanced"
  };

  return map[level] || level;
}

function translateDefinition(word, koreanDefinition) {
  const map = {
    "진짜": "real; genuine; true. Also commonly used as 'really?' or 'seriously?' in conversation.",
    "오늘": "today",
    "먹다": "to eat",
    "먹": "eat / eating form root",
    "가다": "to go",
    "오다": "to come",
    "좋다": "to be good",
    "아니다": "to not be; to be not"
  };

  return map[word] || koreanDefinition || "No English definition available yet.";
}

async function loadDictionary(word) {
  const box = document.getElementById("dictionaryBox");

  box.innerHTML = "Loading dictionary...";

  try {
    const res = await fetch(`/dictionary?word=${encodeURIComponent(word)}`);
    const data = await res.json();

    console.log("Dictionary response:", data);

    if (!data.found) {
      box.innerHTML = `
        <h3>Dictionary</h3>
        <p>No dictionary entry found for "${word}"</p>
      `;
      return;
    }

    const e = data.entry;

    box.innerHTML = `
      <h3>📖 Dictionary</h3>

      <p><strong>${e.word || word}</strong></p>

      ${e.pronunciation ? `<p>Pronunciation: ${e.pronunciation}</p>` : ""}

      ${e.romanization ? `<p>Romanization: ${e.romanization}</p>` : ""}

      ${e.pos ? `<p>Part of Speech: ${translatePos(e.pos)}</p>` : ""}

      ${e.level ? `<p>Level: ${translateLevel(e.level)}</p>` : ""}

      ${e.meaning ? `<p><strong>Meaning:</strong> ${e.meaning}</p>` : ""}

      <p>${e.definition || "No definition available."}</p>

      <button id="saveWordBtn">⭐ Save Word</button>
    `;

    const saveBtn = document.getElementById("saveWordBtn");

    if (saveBtn) {
      saveBtn.onclick = async () => {
        const res = await fetch("/save-word", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded"
          },
          body: `word=${encodeURIComponent(word)}`
        });

        const data = await res.json();

        if (data.ok) {
          saveBtn.textContent = "✅ Saved";
        } else {
          alert(data.error || "Failed to save word");
        }
      };
    }

  } catch (err) {
    console.error(err);
    box.innerHTML = "Dictionary lookup failed.";
  }
}

async function lookupDictionary(query) {
  dictionaryEl.classList.remove("hidden");
  dictionaryEl.innerHTML = "Looking up dictionary...";

  const res = await fetch(`/dictionary?word=${encodeURIComponent(query)}`);
  const data = await res.json();

  if (!data.found) {
    dictionaryEl.innerHTML = "No dictionary entry found.";
    return;
  }

  const e = data.entry;

  dictionaryEl.innerHTML = `
    <div class="dictWord">${e.word || query}</div>
    <div class="dictMeta">
      ${e.pronunciation ? `Pronunciation: ${e.pronunciation}` : ""}
      ${e.pos ? ` · ${e.pos}` : ""}
      ${e.level ? ` · ${e.level}` : ""}
    </div>
    <div class="dictDefinition">${e.definition || "No definition shown."}</div>
    ${e.link ? `<a href="${e.link}" target="_blank">Open dictionary page</a>` : ""}
  `;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderResults(openTitle = null) {
  resultsEl.innerHTML = "";

  const grouped = {};

  items.forEach((it, i) => {
    if (!grouped[it.title]) {
      grouped[it.title] = [];
    }
    grouped[it.title].push({ ...it, originalIndex: i });
  });

  Object.keys(grouped).forEach((title) => {
    const groupDiv = document.createElement("div");
    groupDiv.className = "videoGroup";

    const header = document.createElement("div");
    header.className = "videoHeader";

    const titleDiv = document.createElement("div");
    titleDiv.className = "videoTitle";
    titleDiv.textContent = title;

    const countDiv = document.createElement("div");
    countDiv.className = "videoCount";
    countDiv.textContent = `${grouped[title].length} results`;

    header.appendChild(titleDiv);
    header.appendChild(countDiv);

    const body = document.createElement("div");
    body.className = openTitle === title ? "videoResults" : "videoResults hidden";

    if (openTitle === title) {
      groupDiv.classList.add("expanded");
    }

    grouped[title].forEach((it) => {
      const div = document.createElement("div");
      div.className = "result" + (it.originalIndex === idx ? " active" : "");
      div.innerHTML = `
        <div class="line">${highlight(it.text, q.value.trim())}</div>
        <div class="meta">${Math.floor(it.start)}s</div>
      `;
      div.onclick = () => playIndex(it.originalIndex);
      body.appendChild(div);
    });

    header.onclick = () => {
      body.classList.toggle("hidden");
      groupDiv.classList.toggle("expanded");
    };

    groupDiv.appendChild(header);
    groupDiv.appendChild(body);
    resultsEl.appendChild(groupDiv);
  });
}

function playIndex(i) {
  if (i < 0 || i >= items.length) return;
  idx = i;
  const it = items[idx];
  nowPlaying.textContent = `${it.title} — ${it.text}`;
  yt.src = ytUrl(it.youtube_id, it.start);
  renderResults(it.title);
}

async function doSearch() {
  const query = q.value.trim();
  if (!query) return;
  loadDictionary(query);
  

  resultsEl.innerHTML = "Searching...";
  const res = await fetch(`/search?q=${encodeURIComponent(query)}`);
  items = await res.json();
  idx = items.length ? 0 : -1;

  if (!items.length) {
    resultsEl.innerHTML = "No results. Try another word.";
    yt.src = "";
    nowPlaying.textContent = "No clip selected.";
    return;
  }

  renderResults();
  playIndex(0);
}

btn.onclick = doSearch;
q.addEventListener("keydown", (e) => {
  if (e.key === "Enter") doSearch();
});


document.querySelectorAll(".sampleWord").forEach(btn => {
  btn.addEventListener("click", () => {
    const word = btn.dataset.word;

    document.getElementById("q").value = word;

    doSearch(); 
  });
});

prevBtn.onclick = () => playIndex(idx - 1);
nextBtn.onclick = () => playIndex(idx + 1);