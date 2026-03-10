import { useState, useRef, useEffect } from "react";
import {
  formatTime,
  toUsdNumber,
  actorToAddress,
  short,
  inferWinnerRole,
  tierName,
  statusChipClass,
  formatUsdc,
  verdictOpinionText,
  formatOpinionHTML,
} from "../utils";
import OpinionModal from "./OpinionModal";

export default function ControlPanel(props) {
  const {
    runnerUrl,
    setRunnerUrl,
    isConnected,
    connectAndRefresh,
    explorerUrl,
    contractAddress,
    runs,
    verdicts,
    activeRunId,
    activeRunStatus,
    activeTimeline,
    logs,
    refreshRuns,
    refreshVerdicts,
    refreshReputation,
    appendLog,
  } = props;

  const [windowSec, setWindowSec] = useState(30);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState("");
  const logRef = useRef(null);

  const openVerdict = (disputeId) => {
    const v = verdicts.find((x) => x.disputeId === disputeId);
    if (!v) return;
    const rawOpinion = verdictOpinionText(v);
    setModalContent(formatOpinionHTML(rawOpinion));
    setModalOpen(true);
  };

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  const createRun = async (mode) => {
    try {
      const payload = {
        mode,
        startServices: true,
        keepServices: true,
        autoRun: true,
        agreementWindowSec: windowSec,
      };
      const res = await fetch(`${runnerUrl}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Run Creation Failed");
      const created = await res.json();
      appendLog(`Created run ${created.runId} (${mode})`);
      refreshRuns();
    } catch (err) {
      appendLog(`Error creating run: ${err.message}`);
    }
  };
  return (
    <div className="tab-pane active" id="tab-control">
      <div
        className="hero"
        style={{ alignItems: "center", padding: "20px 32px" }}
      >
        <div className="hero-left">
          <h1 style={{ fontSize: "24px" }}>Verdict Protocol Live Demo</h1>
          <p style={{ marginTop: "4px", fontSize: "13px" }}>
            Real-time demo runner for x402 payments, on-chain escrow/disputes on
            GOAT, evidence anchoring, judge decisions, and reputation updates.
          </p>
        </div>
        <div
          className="hero-right"
          style={{ flexDirection: "row", alignItems: "center", gap: "16px" }}
        >
          <div className="row" style={{ marginTop: 0 }}>
            <input
              id="runnerUrlInput"
              type="text"
              value={runnerUrl}
              onChange={(e) => setRunnerUrl(e.target.value)}
              className="grow mono"
              placeholder="Runner URL"
            />
            <button className="brand" onClick={connectAndRefresh}>
              Connect Server
            </button>
          </div>
          <div className="pill">
            <span
              className={`dot ${isConnected ? "ok" : "warn"}`}
              id="runnerDot"
            ></span>
            <span id="runnerLabel">
              runner: {isConnected ? "connected" : "not connected"}
            </span>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              gap: "4px",
              fontSize: "11px",
            }}
          >
            <div className="sub mono" id="contractLine" style={{ margin: 0 }}>
              contract: {contractAddress}
            </div>
            <a
              className="inline-link"
              href={explorerUrl}
              id="explorerLink"
              style={{ margin: 0 }}
              target="_blank"
              rel="noreferrer"
            >
              open GOAT explorer
            </a>
          </div>
        </div>
      </div>
      <div className="grid top" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="panel glass">
          <h2>Automated Autoplay</h2>
          <div className="sub">
            Full-flow execution of predefined scenarios.
          </div>
          <div className="sub">
            One click for Happy, Dispute, or Full autoplay.
          </div>
          <div className="row" style={{ marginTop: "10px" }}>
            <label className="sub" htmlFor="windowSec" style={{ margin: 0 }}>
              dispute window (sec)
            </label>
            <input
              id="windowSec"
              max="180"
              min="5"
              style={{ maxWidth: "100px" }}
              type="number"
              value={windowSec}
              onChange={(e) => setWindowSec(Number(e.target.value))}
            />
          </div>
          <div className="btn-group">
            <button className="brand" onClick={() => createRun("happy")}>
              Run Happy
            </button>
            <button
              className="brand secondary"
              onClick={() => createRun("dispute")}
            >
              Run Dispute
            </button>
            <button onClick={() => createRun("full")}>Run Full</button>
          </div>
          <div className="btn-group">
            <button onClick={() => refreshRuns()}>Refresh Runs</button>
            <button onClick={() => refreshVerdicts()}>Refresh Verdicts</button>
            <button onClick={() => refreshReputation()}>
              Refresh Reputation
            </button>
          </div>
          <div
            className="sub mono"
            id="activeRunText"
            style={{ marginTop: "8px" }}
          >
            active run:{" "}
            {activeRunId ? `${activeRunId} (${activeRunStatus})` : "none"}
          </div>
        </div>
        <div className="panel glass">
          <h2>Manual Execution Flow</h2>
          <div className="sub">Step-by-step transaction execution.</div>
          <div
            className="row"
            style={{ marginTop: "10px", marginBottom: "10px" }}
          >
            <input
              className="grow mono"
              id="manualAgentUrl"
              placeholder="Agent API Endpoint URL"
            />
          </div>
          <div className="sub">
            Push payment entry for dashboard visibility.
          </div>
          <div
            className="sub"
            style={{ marginTop: "12px", marginBottom: "4px" }}
          >
            Payment Configuration
          </div>
          <div className="row" style={{ marginTop: "10px" }}>
            <input
              className="grow mono"
              id="paymentRecipientInput"
              placeholder="recipient 0x..."
            />
            <input
              id="paymentAmountInput"
              style={{ maxWidth: "100px" }}
              defaultValue="0.0005"
            />
          </div>
          <div className="btn-group">
            <button id="paymentBtn">Run Payment</button>
          </div>
          <div
            className="status-banner"
            id="paymentStatus"
            style={{ marginTop: "10px" }}
          >
            No payment run yet.
          </div>
        </div>
      </div>
      <div className="grid main">
        <div className="stack">
          <div className="panel glass">
            <h2>Run Timeline</h2>
            <div className="chips">
              <span
                className={`chip ${activeRunStatus === "done" ? "ok" : "warn"}`}
                id="runStateChip"
              >
                {activeRunStatus || "idle"}
              </span>
            </div>
            <div className="timeline" id="timeline">
              {!activeTimeline.length ? (
                <div className="sub">No steps yet.</div>
              ) : (
                activeTimeline.map((s, idx) => (
                  <div key={idx} className={`step ${s.status || "running"}`}>
                    <div className="meta mono">{s.stepId || "-"}</div>
                    <div className="title">{s.label || s.stepId || "-"}</div>
                    <div className="sub">{s.message || ""}</div>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="panel glass">
            <h2>Live Log</h2>
            <div className="log" id="runLog" ref={logRef}>
              {logs.map((L, i) => (
                <div key={i} className="log-line">
                  {L.time} {L.message}
                </div>
              ))}
            </div>
          </div>
          <div className="panel glass">
            <h2>Recent Runs</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>run</th>
                    <th>mode</th>
                    <th>status</th>
                    <th>updated</th>
                  </tr>
                </thead>
                <tbody id="runsBody">
                  {!runs.length ? (
                    <tr>
                      <td colSpan="4">No runs.</td>
                    </tr>
                  ) : (
                    runs.map((r) => (
                      <tr key={r.runId}>
                        <td>
                          <button>open</button>{" "}
                          <span className="mono">{r.runId.slice(0, 8)}</span>
                        </td>
                        <td>{r.mode}</td>
                        <td>
                          <span
                            className={`chip ${["done", "complete"].includes(r.status) ? "ok" : "warn"}`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td>{formatTime(r.updateMs || r.createdAt)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div className="stack">
          <div className="panel glass">
            <h2>Recent Disputes</h2>
            <div className="sub">
              Live dispute outcomes with full judicial opinion and reasoning.
            </div>
            <div className="disputes-list" id="recentDisputes">
              {!verdicts.length ? (
                <div className="sub">No disputes yet.</div>
              ) : (
                [...verdicts]
                  .sort(
                    (a, b) =>
                      Number(b.disputeId || 0) - Number(a.disputeId || 0),
                  )
                  .map((v) => {
                    const role = inferWinnerRole(v);
                    const plaintiff = v.plaintiff || "-";
                    const defendant = v.defendant || "-";
                    const winnerAddress =
                      role === "plaintiff"
                        ? plaintiff
                        : role === "defendant"
                          ? defendant
                          : v.winner || "-";
                    const outcomeText =
                      role === "plaintiff"
                        ? "PLAINTIFF WINS"
                        : role === "defendant"
                          ? "DEFENDANT WINS"
                          : "JUDGMENT ISSUED";
                    const tier = tierName(v.courtTier || v.tier);
                    const statusText = String(
                      v.status || "unknown",
                    ).toUpperCase();
                    const txRef = v.transactionId
                      ? `TX #${v.transactionId}`
                      : "TX #-";
                    const opinion = verdictOpinionText(v);

                    return (
                      <div
                        key={v.disputeId}
                        className="dispute-card"
                        onClick={(e) => {
                          e.currentTarget
                            .querySelector(".dispute-details")
                            ?.classList.toggle("expanded");
                          openVerdict(v.disputeId);
                        }}
                      >
                        <div className="dispute-top">
                          <div>
                            <div className="dispute-id">
                              DISPUTE #{v.disputeId || "-"} &nbsp;&nbsp; {txRef}
                            </div>
                            <div className="dispute-party-line">
                              <div>
                                <div className="sub">PLAINTIFF</div>
                                <div className="dispute-party">
                                  {short(plaintiff, 6)}
                                </div>
                              </div>
                              <div className="dispute-vs">VS</div>
                              <div>
                                <div className="sub">DEFENDANT</div>
                                <div className="dispute-party">
                                  {short(defendant, 6)}
                                </div>
                              </div>
                            </div>
                          </div>
                          <div className="dispute-right">
                            <div className="dispute-amount">
                              {formatUsdc(v.stake || "0")}
                            </div>
                            <div
                              className="chips"
                              style={{
                                justifyContent: "flex-end",
                                marginTop: "6px",
                              }}
                            >
                              <span className="chip warn">{tier}</span>
                              <span
                                className={`chip ${statusChipClass(v.status || "unknown")}`}
                              >
                                {statusText}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="dispute-outcome">
                          <div
                            className={`winner ${role === "defendant" ? "defendant" : role === "plaintiff" ? "plaintiff" : ""}`}
                          >
                            {outcomeText}
                          </div>
                          <div className="meta">
                            - {tier} court - Winner: {short(winnerAddress, 8)}
                          </div>
                        </div>

                        <div className="dispute-details">
                          <div className="dispute-grid">
                            <div className="dispute-stat">
                              <div className="label">Plaintiff Evidence</div>
                              <div className="value">
                                {v.plaintiffEvidence || "0x0"}
                              </div>
                            </div>
                            <div className="dispute-stat">
                              <div className="label">Defendant Evidence</div>
                              <div className="value">
                                {v.defendantEvidence || "0x0"}
                              </div>
                            </div>
                            <div className="dispute-stat">
                              <div className="label">Stake</div>
                              <div className="value">
                                {formatUsdc(v.stake || "0")}
                              </div>
                            </div>
                            <div className="dispute-stat">
                              <div className="label">Judge Fee</div>
                              <div className="value">
                                {formatUsdc(v.judgeFee || "0")}
                              </div>
                            </div>
                          </div>

                          <div className="opinion-box">
                            <div className="opinion-head">
                              <div className="opinion-title">
                                Judicial Opinion
                              </div>
                              <div className="opinion-court">{tier} court</div>
                            </div>
                            <div
                              className="opinion-parsed"
                              style={{
                                marginTop: "24px",
                                padding: "24px",
                                background: "rgba(0,0,0,0.02)",
                                borderRadius: "12px",
                                border: "1px solid rgba(0,0,0,0.05)",
                              }}
                              dangerouslySetInnerHTML={{
                                __html: formatOpinionHTML(opinion),
                              }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    );
                  })
              )}
            </div>
          </div>
          <div className="panel glass">
            <h2>Verdicts</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>dispute</th>
                    <th>agreement</th>
                    <th>status</th>
                    <th>winner</th>
                    <th>confidence</th>
                  </tr>
                </thead>
                <tbody id="verdictsBody">
                  {!verdicts.length ? (
                    <tr>
                      <td colSpan="5">No verdicts.</td>
                    </tr>
                  ) : (
                    verdicts.map((v) => {
                      const status = v.status || "unknown";
                      const confidence =
                        typeof v.confidence === "number"
                          ? v.confidence.toFixed(2)
                          : v.confidence || "-";
                      return (
                        <tr key={v.disputeId}>
                          <td>
                            <button onClick={() => openVerdict(v.disputeId)}>
                              open
                            </button>{" "}
                            {v.disputeId}
                          </td>
                          <td className="mono">
                            {short(v.agreementId || "-", 14)}
                          </td>
                          <td>
                            <span className={`chip ${statusChipClass(status)}`}>
                              {status}
                            </span>
                          </td>
                          <td className="mono">{short(v.winner || "-", 12)}</td>
                          <td>{confidence}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
            <div
              className="status-banner"
              id="verdictDetail"
              style={{ marginTop: "10px" }}
            >
              No verdict selected.
            </div>
          </div>
        </div>
      </div>
      <OpinionModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        htmlContent={modalContent}
      />
    </div>
  );
}
