const websites = [
  { name: "Pemerintah Kabupaten Lamongan", url: "lamongankab.go.id" },
  { name: "DPRD Kabupaten Lamongan", url: "dprd.lamongankab.go.id" },
  { name: "Dinas Pendidikan", url: "disdik.lamongankab.go.id" },
  { name: "Dinas Kesehatan", url: "dinkes.lamongankab.go.id" },
  { name: "Dinas Pekerjaan Umum", url: "dpubm.lamongankab.go.id" },
  { name: "Bappeda Lamongan", url: "bappeda.lamongankab.go.id" },
  { name: "Dinas Sosial", url: "dinsos.lamongankab.go.id" },
  { name: "BPBD Lamongan", url: "bpbd.lamongankab.go.id" },
  { name: "Dinas Kominfo", url: "diskominfo.lamongankab.go.id" },
  { name: "Badan Kepegawaian Daerah", url: "bkd.lamongankab.go.id" },
  { name: "Dinas Pertanian", url: "distan.lamongankab.go.id" },
  { name: "Dinas Ketahanan Pangan", url: "dinkpp.lamongankab.go.id" },
  { name: "RSUD Dr. Soegiri", url: "rsud-soegiri.lamongankab.go.id" },
  { name: "RSUD Ngimbang", url: "rsud-ngimbang.lamongankab.go.id" },
  { name: "Dinas Kependudukan dan Catatan Sipil", url: "dispendukcapil.lamongankab.go.id" },
  { name: "Dinas Pariwisata dan Kebudayaan", url: "disparbud.lamongankab.go.id" }
];

let checkResults = {};
let checkedCount = 0;

function normalizeUrl(url) {
  let normalized = url.trim();
  if (!normalized.startsWith("http://") && !normalized.startsWith("https://")) {
    normalized = "https://" + normalized;
  }
  return normalized;
}

document.addEventListener("DOMContentLoaded", () => {
  renderGrid();
  checkAllWebsites();
  setInterval(checkAllWebsites, 300000); // 5 mins
});

function renderGrid() {
  const grid = document.getElementById("govGrid");
  grid.innerHTML = websites.map((site, index) => {
    const res = checkResults[site.url];
    let dotClass = "dot-yellow";
    let statusText = "Sedang memeriksa...";

    if (res) {
      if (res.status === "UP") {
        dotClass = "dot-green";
        statusText = `Server aktif, ${res.response_time} ms, baru saja`;
      } else {
        dotClass = "dot-red";
        statusText = "Server tidak aktif";
      }
    }

    return `
      <div class="item">
        <div><span class="dot ${dotClass}"></span><strong>${site.name}</strong></div>
        <div style="font-size:11px; color:#666; margin-top:4px;">${statusText}</div>
      </div>
    `;
  }).join('');
}

async function checkAllWebsites() {
  checkedCount = 0;
  checkResults = {};
  renderGrid();
  
  websites.forEach(async (site) => {
    try {
        const response = await fetch("/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: normalizeUrl(site.url) })
      });
      const data = await response.json();
      checkResults[site.url] = data;
    } catch(e) {
      checkResults[site.url] = { status: "DOWN" };
    } finally {
      checkedCount++;
      document.getElementById("checkCounter").innerText = `${checkedCount}/${websites.length}`;
      renderGrid();
      updateRightColumn();
    }
  });

  document.getElementById("lastUpdated").innerText = `Terakhir diperbarui: ${new Date().toLocaleTimeString()}`;
}

function updateRightColumn() {
  const downList = document.getElementById("downList");
  const onlineList = document.getElementById("onlineList");

  const downs = websites.filter(site => checkResults[site.url] && checkResults[site.url].status !== "UP");
  const ons = websites.filter(site => checkResults[site.url] && checkResults[site.url].status === "UP");

  downList.innerHTML = downs.length ? downs.map(site => `<div>${site.name} <span class="badge down">DOWN</span></div>`).join('') : "Semua website dapat diakses";
  onlineList.innerHTML = ons.length ? ons.map(site => `<div>${site.name} - ${checkResults[site.url].response_time}ms <span class="badge up">UP</span></div>`).join('') : "Sedang memeriksa...";
}

document.getElementById("checkBtn").addEventListener("click", async () => {
  const input = document.getElementById("urlInput");
  const resDiv = document.getElementById("result");
  const url = normalizeUrl(input.value);

  resDiv.style.display = "block";
  resDiv.innerText = "Memeriksa...";
  resDiv.style.background = "#eee";

  try {
        const response = await fetch("/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url })
    });
    const data = await response.json();
    if (data.status === "UP") {
      resDiv.style.background = "#D4EDDA";
      resDiv.innerText = `Aktif - ${data.response_time}ms (Status: ${data.status_code})`;
    } else {
      resDiv.style.background = "#F8D7DA";
      resDiv.innerText = `Tidak Aktif - ${data.error || 'Error'}`;
    }
  } catch(e) {
    resDiv.style.background = "#FFF3CD";
    resDiv.innerText = "Peringatan: Backend belum berjalan";
  }
});
