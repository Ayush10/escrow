export const defaultRunnerUrl = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const fromQuery = urlParams.get("runner");
    if (fromQuery) return fromQuery;

    const host = window.location.hostname || "127.0.0.1";
    return `http://${host}:4004`;
};

export const deriveDefaultServices = (base) => {
    return {
        judge: `${base}/api/agent/judge`,
        buyer: `${base}/api/agent/buyer`,
        seller: `${base}/api/agent/seller`,
        escrow: `${base}/api/escrow`,
        reputation: `${base}/api/reputation`
    };
};

export const short = (v, n = 10) => {
    if (!v || typeof v !== "string") return "-";
    if (v.length <= n + 4) return v;
    return `${v.slice(0, n)}...${v.slice(-4)}`;
};

export const tierName = (input) => {
    if (typeof input === "string" && input.trim())
        return input.trim().toLowerCase();
    const n = Number(input);
    if (n === 1) return "appeals";
    if (n === 2) return "supreme";
    return "district";
};

export const inferWinnerRole = (v) => {
    const winner = String(v.winner || "").toLowerCase();
    const plaintiff = String(v.plaintiff || "").toLowerCase();
    const defendant = String(v.defendant || "").toLowerCase();
    if (winner === "plaintiff" || (plaintiff && winner === plaintiff))
        return "plaintiff";
    if (winner === "defendant" || (defendant && winner === defendant))
        return "defendant";
    return "unknown";
};

export const formatUsdc = (raw) => {
    if (raw === null || raw === undefined || raw === "") return "-";
    const s = String(raw).trim();
    if (!/^-?\d+$/.test(s)) {
        const asNum = Number(s);
        if (Number.isFinite(asNum)) return `${asNum.toFixed(4)} USDC`;
        return `${s} USDC`;
    }
    const neg = s.startsWith("-");
    const digits = neg ? s.slice(1) : s;
    const decimals = digits.length >= 13 ? 18 : 6;
    const padded = digits.padStart(decimals + 1, "0");
    const whole =
        padded.slice(0, -decimals).replace(/^0+(?=\d)/, "") || "0";
    const frac = padded.slice(-decimals).slice(0, 4);
    return `${neg ? "-" : ""}${whole}.${frac} USDC`;
};

export const statusChipClass = (status) => {
    if (status === "done" || status === "complete" || status === "submitted") return "ok";
    if (status === "error" || status === "failed") return "bad";
    return "warn";
};

export const verdictOpinionText = (v) => {
    if (v.fullOpinion && String(v.fullOpinion).trim()) {
        return String(v.fullOpinion);
    }
    const fallback = {
        winner: inferWinnerRole(v) === "unknown" ? v.winner || "-" : inferWinnerRole(v),
        reasoning: v.reasoning || "No long-form opinion available.",
        reasonCodes: v.reasonCodes || [],
        flags: v.flags || [],
    };
    return JSON.stringify(fallback, null, 2);
};

export const formatTime = (isoString) => {
    if (!isoString) return "-";
    try {
        const d = new Date(isoString);
        if (isNaN(d.getTime())) return isoString;
        return d.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    } catch (e) {
        return isoString;
    }
};

export const formatOpinionHTML = (text) => {
    if (!text) return "";

    // 1. Escape basic HTML to prevent arbitrary script injection
    let safeText = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // 2. Pre-process text to standardize line endings and decode escaped newlines
    safeText = safeText.replace(/\\n/g, "\n").replace(/\r\n/g, "\n");

    // 3. Extract JSON blocks to preserve them from formatting
    const jsonBlocks = [];
    safeText = safeText.replace(/```(?:json)?\n([\s\S]*?)```/g, (match, p1) => {
        jsonBlocks.push(p1);
        return `__JSON_BLOCK_${jsonBlocks.length - 1}__`;
    });

    // 4. Handle Court Heading & Lines explicitly with spacing
    safeText = safeText.replace(
        /AGENT COURT PROTOCOL — DISTRICT DIVISION/,
        "<h3 style='margin-bottom: 32px; font-weight: 700; letter-spacing: 0.1em; color: var(--brand-2);'>AGENT COURT PROTOCOL — DISTRICT DIVISION</h3>",
    );
    safeText = safeText.replace(
        /JUDICIAL OPINION/,
        "<h2 style='text-align: center; margin-top: 40px; margin-bottom: 40px; font-size: 24px; color: var(--brand); font-weight: 800; letter-spacing: 0.05em;'>JUDICIAL OPINION</h2>",
    );
    safeText = safeText.replace(
        /Case No\.\s*(\d+)/i,
        "<div style='font-weight: 700; margin-bottom: 16px; color: var(--text-muted); text-transform: uppercase;'>CASE NO. $1</div>",
    );

    // Address matching
    safeText = safeText.replace(
        /(0x[a-fA-F0-9]{40})/g,
        "<code style='background: rgba(19, 200, 236, 0.1); color: var(--text); padding: 4px 8px; border-radius: 6px; font-family: var(--mono);'>$1</code>",
    );

    // Format Plaintiff/Defendant lines cleanly
    safeText = safeText.replace(
        /<code[^>]*>(0x[a-fA-F0-9]{40})<\/code>\s*\(Plaintiff\)\s*v\.\s*/g,
        "<div style='margin-bottom: 4px;'><code>$1</code> <span style='font-weight: 600;'>(Plaintiff) v.</span></div>",
    );
    safeText = safeText.replace(
        /<code[^>]*>(0x[a-fA-F0-9]{40})<\/code>\s*\(Defendant\)/g,
        "<div style='margin-bottom: 32px;'><code>$1</code> <span style='font-weight: 600;'>(Defendant)</span></div>",
    );

    // Bold headings (e.g., "I. FINDINGS OF FACT:")
    safeText = safeText.replace(
        /^([XVI]+\.\s+[A-Z\s]+:?)$/gm,
        "<h3 style='margin-top: 32px; margin-bottom: 16px; font-weight: 700; color: var(--text); padding-bottom: 8px; border-bottom: 1px solid var(--line);'>$1</h3>",
    );

    // Split into paragraphs by double newlines, wrap in <p> if not already wrapped
    let paragraphs = safeText.split(/\n\s*\n/);
    paragraphs = paragraphs.map((p) => {
        let text = p.trim();
        if (!text) return "";
        if (text.startsWith("<h") || text.startsWith("<div")) {
            return text;
        }
        return `<p style='margin-bottom: 16px; line-height: 1.7;'>${text.replace(/\n/g, "<br>")}</p>`;
    });
    safeText = paragraphs.join("");

    // Style bulleted lists cleanly
    safeText = safeText.replace(
        /<p[^>]*>\s*-\s+(.*?)<\/p>/g,
        "<div style='margin-bottom: 8px; padding-left: 16px; text-indent: -16px; line-height: 1.6;'>- $1</div>",
    );

    // 5. Restore JSON blocks with proper styling
    safeText = safeText.replace(/__JSON_BLOCK_(\d+)__/g, (match, p1) => {
        const index = parseInt(p1, 10);
        return `<pre class="json-block"><code>${jsonBlocks[index]}</code></pre>`;
    });

    return safeText;
};
