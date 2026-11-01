/* Komunikace se serverem ovladače. Načítá se jako první – definuje API_BASE_URL a api*. */

/** Adresa API odvozená z adresy stránky (funguje na localhostu i z mobilu v LAN). */
const API_BASE_URL = `${location.origin}/api`;

/**
 * Převede chybovou odpověď FastAPI na čitelnou zprávu.
 * `detail` je text (HTTPException) nebo seznam chyb validace (422).
 */
function apiErrorMessage(body, status) {
  const detail = body && body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg.replace(/^Value error, /, "")).join("; ");
  return `Chyba serveru (${status})`;
}

/** Provede požadavek na API a vrátí JSON; při chybě vyhodí Error s českou zprávou. */
async function apiRequest(path, options = {}) {
  let resp;
  try {
    resp = await fetch(`${API_BASE_URL}${path}`, options);
  } catch {
    throw new Error("Server ovladače neodpovídá");
  }
  const body = await resp.json().catch(() => null);
  if (!resp.ok) throw new Error(apiErrorMessage(body, resp.status));
  return body;
}

/** GET na API. */
function apiGet(path) {
  return apiRequest(path);
}

/** POST s JSON tělem. */
function apiPost(path, data) {
  return apiRequest(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
}
