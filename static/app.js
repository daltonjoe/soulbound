const API_BASE = window.location.origin;

const SIGN_EMOJI = {
    "Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
    "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
    "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓",
    "Koç": "♈", "Boğa": "♉", "İkizler": "♊", "Yengeç": "♋",
    "Aslan": "♌", "Başak": "♍", "Terazi": "♎", "Akrep": "♏",
    "Yay": "♐", "Oğlak": "♑", "Kova": "♒", "Balık": "♓"
};

const PLANET_EMOJI = {
    "Sun": "☀️", "Moon": "🌙", "Mercury": "☿️", "Venus": "♀️",
    "Mars": "♂️", "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅",
    "Neptune": "♆", "Pluto": "♇"
};

const ASPECT_EMOJI = {
    "conjunction": "☌", "opposition": "☍", "trine": "△",
    "square": "□", "sextile": "⚹"
};

let appToken = null;

async function getAppToken() {
    if (appToken) return appToken;
    try {
        const res = await fetch(`${API_BASE}/app-token`);
        const data = await res.json();
        appToken = data.token;
        return appToken;
    } catch (e) {
        return null;
    }
}

function signEmoji(sign) {
    return SIGN_EMOJI[sign] || "";
}

function planetEmoji(planet) {
    return PLANET_EMOJI[planet] || "🪐";
}

function aspectEmoji(type) {
    const t = (type || "").toLowerCase();
    return ASPECT_EMOJI[t] || "◇";
}

function showSection(id) {
    document.getElementById("form-section").classList.add("hidden");
    document.getElementById("loading-section").classList.add("hidden");
    document.getElementById("result-section").classList.add("hidden");
    document.getElementById(id).classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function setLoading(text) {
    document.getElementById("loading-text").textContent = text;
}

function renderSummary(data) {
    const input = data.input || {};
    const location = data.location || {};
    const summary = data.summary || {};

    const items = [
        { label: "Doğum Tarihi", value: input.birth_date },
        { label: "Yerel Saat", value: input.birth_time_local },
        { label: "UTC Saat", value: new Date(input.birth_time_utc).toLocaleString("tr-TR") },
        { label: "Doğum Yeri", value: location.city_resolved },
        { label: "Enlem / Boylam", value: `${location.latitude}, ${location.longitude}` },
        { label: "Saat Dilimi", value: `${location.timezone} (${location.utc_offset})` },
        summary.sun_sign ? { label: "Güneş Burcu", value: `${signEmoji(summary.sun_sign)} ${summary.sun_sign}` } : null,
        summary.moon_sign ? { label: "Ay Burcu", value: `${signEmoji(summary.moon_sign)} ${summary.moon_sign}` } : null,
        summary.ascendant ? { label: "Yükselen", value: `${signEmoji(summary.ascendant)} ${summary.ascendant}` } : null
    ].filter(Boolean);

    return items.map(item => `
        <div class="summary-item">
            <span class="summary-label">${item.label}</span>
            <span class="summary-value">${item.value || "—"}</span>
        </div>
    `).join("");
}

function renderPlanets(planets) {
    if (!planets || !Array.isArray(planets)) return "";
    return planets.map(p => `
        <div class="planet-card">
            <div class="planet-name">${planetEmoji(p.name)} ${p.name}</div>
            <div class="planet-sign">${signEmoji(p.sign)} ${p.sign}</div>
            <div class="planet-degree">${p.degree ?? ""}° ${p.minute ?? ""}'</div>
            ${p.house ? `<div class="planet-house">Ev ${p.house}</div>` : ""}
        </div>
    `).join("");
}

function renderAspects(aspects) {
    if (!aspects || !Array.isArray(aspects)) return "";
    return aspects.slice(0, 30).map(a => `
        <div class="aspect-item">
            <span class="aspect-planets">
                ${planetEmoji(a.planet1)} ${a.planet1} ${aspectEmoji(a.type)} ${planetEmoji(a.planet2)} ${a.planet2}
            </span>
            <span class="aspect-type">${a.type || ""} ${a.orb ? `(${a.orb}°)` : ""}</span>
        </div>
    `).join("");
}

function renderAngles(angles) {
    if (!angles) return "";
    const cards = [];
    for (const [key, val] of Object.entries(angles)) {
        if (val && typeof val === "object") {
            cards.push(`
                <div class="angle-card">
                    <div class="angle-label">${key}</div>
                    <div class="angle-sign">${signEmoji(val.sign || "")} ${val.sign || ""}</div>
                    <div class="angle-degree">${val.degree ?? ""}°</div>
                </div>
            `);
        }
    }
    return cards.join("");
}

function showError(message, suggestion = "") {
    showSection("result-section");
    document.getElementById("error-card").classList.remove("hidden");
    document.getElementById("error-message").textContent = message;
    document.getElementById("error-suggestion").textContent = suggestion || "";
    document.getElementById("summary").parentElement.classList.add("hidden");
    document.querySelectorAll("#result-section .card:not(#error-card)").forEach(el => el.classList.add("hidden"));
}

function showResult(data) {
    showSection("result-section");
    document.getElementById("error-card").classList.add("hidden");
    document.getElementById("summary").parentElement.classList.remove("hidden");
    document.querySelectorAll("#result-section .card:not(#error-card)").forEach(el => el.classList.remove("hidden"));

    document.getElementById("summary").innerHTML = renderSummary(data);
    document.getElementById("planets").innerHTML = renderPlanets(data.planets);
    document.getElementById("aspects").innerHTML = renderAspects(data.aspects);
    document.getElementById("angles").innerHTML = renderAngles(data.angles);

    const reportCard = document.getElementById("report-card");
    const aiReport = document.getElementById("ai_report");
    if (data.ai_report) {
        reportCard.classList.remove("hidden");
        aiReport.textContent = data.ai_report;
    } else {
        reportCard.classList.add("hidden");
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

document.getElementById("chart-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
        birth_date: document.getElementById("birth_date").value,
        birth_time: document.getElementById("birth_time").value,
        city: document.getElementById("city").value,
        locale: document.getElementById("locale").value,
        include_report: document.getElementById("include_report").checked
    };

    const submitBtn = document.getElementById("submit-btn");
    submitBtn.disabled = true;
    showSection("loading-section");
    setLoading("Haritan hazırlanıyor...");

    try {
        const token = await getAppToken();

        if (payload.include_report) {
            setTimeout(() => setLoading("AI raporu hazırlanıyor, lütfen bekle..."), 3000);
        }

        const res = await fetch(`${API_BASE}/generateNatalChart`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { "Authorization": `Bearer ${token}` } : {})
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (data.status === "error") {
            showError(data.message || "Bir hata oluştu", data.suggestion || "");
        } else {
            showResult(data);
        }
    } catch (err) {
        showError("Bağlantı hatası: " + err.message, "Lütfen internet bağlantını kontrol et.");
    } finally {
        submitBtn.disabled = false;
    }
});

document.getElementById("new-chart-btn").addEventListener("click", () => {
    document.getElementById("chart-form").reset();
    showSection("form-section");
});

(function setDefaultDate() {
    const today = new Date();
    const defaultDate = new Date(today.getFullYear() - 30, 5, 15);
    const yyyy = defaultDate.getFullYear();
    const mm = String(defaultDate.getMonth() + 1).padStart(2, "0");
    const dd = String(defaultDate.getDate()).padStart(2, "0");
    document.getElementById("birth_date").max = `${yyyy}-${mm}-${dd}`;
    document.getElementById("birth_date").value = `${yyyy}-${mm}-${dd}`;
    document.getElementById("birth_time").value = "12:00";
})();
