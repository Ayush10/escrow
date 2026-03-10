import { useState } from "react";
import { formatTime, short } from "../utils";

export default function NetworkExplorer(props) {
  const { reputation, explorerUrl, services } = props;
  const [agreementId, setAgreementId] = useState("");
  const [agreementDetailHtml, setAgreementDetailHtml] = useState(
    "No agreement loaded.",
  );
  const [actorDetailHtml, setActorDetailHtml] = useState("No actor selected.");

  const loadAgreement = async () => {
    if (!agreementId.trim()) return;
    try {
      const res = await fetch(
        `${services.evidence}/agreements/${encodeURIComponent(agreementId.trim())}`,
      );
      if (!res.ok) throw new Error("fetch failed");
      const payload = await res.json();

      const chainStatus = payload.receiptChain?.valid ? "valid" : "invalid";
      const rootStatus =
        payload.root?.matched === true
          ? "matched"
          : payload.root?.matched === false
            ? "mismatch"
            : "unknown";
      const tx = payload.anchor?.txHash;
      const txLink = tx ? `${explorerUrl}/tx/${tx}` : null;
      let html = `agreement: <span class="mono">${payload.agreementId || "-"}</span><br/>
receipts: ${payload.receiptCount || 0}<br/>
chain: <span class="chip ${chainStatus === "valid" ? "ok" : "bad"}">${chainStatus}</span><br/>
root: ${payload.root?.anchored || "-"} (${rootStatus})`;

      if (txLink) {
        html += `<br/>anchor tx: <a class="inline-link mono" href="${txLink}" target="_blank" rel="noreferrer">${short(tx, 14)}</a>`;
      }
      setAgreementDetailHtml(html);
    } catch (err) {
      setAgreementDetailHtml(`Error: ${err.message}`);
    }
  };

  const openActor = async (actorId) => {
    try {
      const res = await fetch(
        `${services.reputation}/reputation/${encodeURIComponent(actorId)}`,
      );
      if (!res.ok) throw new Error("fetch failed");
      const payload = await res.json();
      const events = payload.history || payload.events || [];
      if (!events.length) {
        setActorDetailHtml(
          `actor <span class="mono">${actorId}</span>: no history`,
        );
        return;
      }
      const lines = events
        .slice(0, 8)
        .map((e) => {
          const ts = e.atMs || (e.createdAt ? Number(e.createdAt) * 1000 : 0);
          const label = e.reason || e.action || "-";
          const detail = e.detail || JSON.stringify(e.payload || {});
          return `${label} @ ${formatTime(ts)} (${detail})`;
        })
        .join("<br/>");
      setActorDetailHtml(
        `actor <span class="mono">${actorId}</span><br/>${lines}`,
      );
    } catch (err) {
      setActorDetailHtml(`Error: ${err.message}`);
    }
  };
  return (
    <div className="tab-pane active" id="tab-network">
      <div className="grid main">
        <div className="stack">
          <div className="panel glass">
            <h2>Service Health</h2>
            <div className="health-grid" id="healthGrid">
              {Object.entries(services || {}).map(([name, url]) => (
                <div key={name} className="health-card">
                  <div className="health-title">{name}</div>
                  <div className="health-url">{short(url, 20)}</div>
                  <div className="health-status ok">ONLINE</div>
                </div>
              ))}
            </div>
          </div>
          <div className="panel glass">
            <h2>Agreement Explorer</h2>
            <div className="row" style={{ marginTop: "10px" }}>
              <input
                className="grow mono"
                value={agreementId}
                onChange={(e) => setAgreementId(e.target.value)}
                placeholder="agreementId"
              />
              <button onClick={loadAgreement}>Load</button>
            </div>
            <div
              className="status-banner"
              style={{ marginTop: "10px" }}
              dangerouslySetInnerHTML={{ __html: agreementDetailHtml }}
            />
          </div>
        </div>
        <div className="stack">
          <div className="panel glass">
            <h2>Reputation</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>actor</th>
                    <th>score</th>
                    <th>events</th>
                    <th>updated</th>
                  </tr>
                </thead>
                <tbody id="reputationBody">
                  {!reputation.length ? (
                    <tr>
                      <td colSpan="4">No reputation rows.</td>
                    </tr>
                  ) : (
                    [...reputation]
                      .sort(
                        (a, b) => Number(b.score || 0) - Number(a.score || 0),
                      )
                      .map((a) => (
                        <tr key={a.actorId}>
                          <td>
                            <button onClick={() => openActor(a.actorId)}>
                              open
                            </button>{" "}
                            <span className="mono">{short(a.actorId, 12)}</span>
                          </td>
                          <td>{a.score ?? "-"}</td>
                          <td>{(a.events || []).length}</td>
                          <td>{formatTime(a.updatedAtMs || a.updatedAt)}</td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            </div>
            <div
              className="status-banner"
              style={{ marginTop: "10px" }}
              dangerouslySetInnerHTML={{ __html: actorDetailHtml }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
