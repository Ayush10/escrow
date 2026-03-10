import { useMemo } from "react";
import {
  formatUsdc,
  short,
  actorToAddress,
  normalizedAddress,
  toUsdNumber,
  tierName,
} from "../utils";

export default function CourtDashboard(props) {
  const { courtStats, agreements, verdicts, reputation, explorerUrl } = props;

  const servicesList = useMemo(() => {
    if (!agreements || !agreements.length) return [];
    return [...agreements]
      .sort((a, b) => Number(b.createdAt || 0) - Number(a.createdAt || 0))
      .map((agreement) => {
        const related = (verdicts || []).filter(
          (v) => String(v.agreementId) === String(agreement.agreementId),
        );
        const providerFromVerdict = actorToAddress(related[0]?.defendant || "");
        const providerFromActors = (agreement.actors || [])
          .map(actorToAddress)
          .find((a) => /^0x[a-fA-F0-9]{40}$/.test(a));
        const provider = providerFromVerdict || providerFromActors || "-";

        return {
          id: agreement.agreementId,
          provider,
          calls: Number(agreement.requestCount || agreement.receiptCount || 0),
          disputes: related.length,
          bond: related.length
            ? formatUsdc(related[0].stake || "0")
            : "0.0010 USDC",
          status: "Active",
        };
      });
  }, [agreements, verdicts]);

  const agentsList = useMemo(() => {
    const actorSet = new Set();
    (reputation || []).forEach((item) => {
      const addr = actorToAddress(item.actorId);
      if (/^0x[a-fA-F0-9]{40}$/.test(addr)) actorSet.add(addr);
    });
    (verdicts || []).forEach((v) => {
      [v.plaintiff, v.defendant, v.winner, v.loser].forEach((entry) => {
        const addr = actorToAddress(entry);
        if (/^0x[a-fA-F0-9]{40}$/.test(addr)) actorSet.add(addr);
      });
    });
    (agreements || []).forEach((ag) => {
      (ag.actors || []).forEach((act) => {
        const addr = actorToAddress(act);
        if (/^0x[a-fA-F0-9]{40}$/.test(addr)) actorSet.add(addr);
      });
    });

    const addresses = Array.from(actorSet);

    return addresses
      .map((address) => {
        const lower = normalizedAddress(address);
        const repScore = 100; // Simplified for the synchronous render

        let wins = 0;
        let losses = 0;
        let txCount = 0;
        let balance = 0;
        let tier = "district";

        const involved = (verdicts || []).filter((v) => {
          const p = normalizedAddress(v.plaintiff);
          const d = normalizedAddress(v.defendant);
          const w = normalizedAddress(v.winner);
          const l = normalizedAddress(v.loser);
          return (
            lower && (lower === p || lower === d || lower === w || lower === l)
          );
        });

        involved.forEach((v) => {
          const w = normalizedAddress(v.winner);
          const l = normalizedAddress(v.loser);
          if (w === lower) wins++;
          if (l === lower) losses++;

          const stake = toUsdNumber(v.stake || 0);
          const fee = toUsdNumber(v.judgeFee || 0);

          if (w === lower) balance += stake;
          if (l === lower) balance -= stake + fee;

          const tRank = (t) => (t === "supreme" ? 3 : t === "appeals" ? 2 : 1);
          if (tRank(tierName(v.courtTier || v.tier)) > tRank(tier)) {
            tier = tierName(v.courtTier || v.tier);
          }
        });

        (agreements || []).forEach((ag) => {
          const hasAct = (ag.actors || [])
            .map(normalizedAddress)
            .includes(lower);
          if (hasAct) txCount += Number(ag.requestCount || 0);
        });

        const role =
          lower === "0x00289dbbb86b64881cea492d14178cf886b066be"
            ? "judge"
            : "agent";

        return {
          address,
          score: repScore,
          transactions: txCount,
          wins,
          losses,
          balance,
          role,
          tier,
        };
      })
      .sort((a, b) => b.balance - a.balance);
  }, [reputation, verdicts, agreements]);
  return (
    <div className="tab-pane" id="tab-court">
      <div className="court-dashboard">
        <div className="court-stats" id="courtStats">
          <div className="court-stat-card">
            <div className="court-stat-value brand">
              {courtStats.disputes || 0}
            </div>
            <div className="court-stat-label">Disputes</div>
          </div>
          <div className="court-stat-card">
            <div className="court-stat-value ok">
              {courtStats.resolved || 0}
            </div>
            <div className="court-stat-label">Resolved</div>
          </div>
          <div className="court-stat-card">
            <div className="court-stat-value warn">
              {courtStats.services || 0}
            </div>
            <div className="court-stat-label">Services</div>
          </div>
          <div className="court-stat-card">
            <div className="court-stat-value">
              {courtStats.transactions || 0}
            </div>
            <div className="court-stat-label">Transactions</div>
          </div>
          <div className="court-stat-card">
            <div className="court-stat-value ok">
              ${Number(courtStats.escrow || 0).toFixed(4)}
            </div>
            <div className="court-stat-label">USDC in Escrow</div>
          </div>
        </div>
        <div className="court-block">
          <h2 className="court-heading">Court System</h2>
          <div className="court-tier-grid">
            <div className="tier-card district">
              <div className="tier-name">District Court</div>
              <div className="tier-model mono">claude-haiku-4-5</div>
              <div className="tier-fee district">$0.0050</div>
              <div className="tier-rule">First Hearing</div>
            </div>
            <div className="tier-card appeals">
              <div className="tier-name">Appeals Court</div>
              <div className="tier-model mono">claude-sonnet-4-6</div>
              <div className="tier-fee appeals">$0.0100</div>
              <div className="tier-rule">1 Prior Loss</div>
            </div>
            <div className="tier-card supreme">
              <div className="tier-name">Supreme Court</div>
              <div className="tier-model mono">claude-opus-4-6</div>
              <div className="tier-fee supreme">$0.0200</div>
              <div className="tier-rule">Final Ruling</div>
            </div>
          </div>
        </div>
        <div className="court-block">
          <div className="section-head-row">
            <h2 className="court-heading">Registered Services</h2>
            <span className="section-pill" id="servicesCountPill">
              {servicesList.length}
            </span>
          </div>
          <div className="service-list" id="registeredServices">
            {!servicesList.length ? (
              <div className="sub">No services yet.</div>
            ) : (
              servicesList.map((svc, idx) => (
                <div key={idx} className="service-card">
                  <div className="top">
                    <div>
                      <div className="service-id">Service #{idx}</div>
                      <div className="service-provider">
                        Provider: {short(svc.provider, 6)}
                      </div>
                      <div className="service-meta">
                        Calls: {svc.calls} &nbsp;&nbsp; Disputes: {svc.disputes}{" "}
                        &nbsp;&nbsp; Bond: {svc.bond} &nbsp;&nbsp; Status:{" "}
                        {svc.status}
                      </div>
                    </div>
                    <div className="service-price">0.0050 USDC</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        <div className="court-block">
          <h2 className="court-heading">Registered Agents</h2>
          <div className="agent-list" id="registeredAgents">
            {!agentsList.length ? (
              <div className="sub">No agents yet.</div>
            ) : (
              agentsList.map((row) => (
                <div key={row.address} className="agent-card">
                  <div className="top">
                    <div>
                      <div className="agent-address">{row.address}</div>
                      <a
                        className="agent-explorer"
                        href={`${explorerUrl}/address/${row.address}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View on Explorer ↗
                      </a>
                    </div>
                    <div className="agent-tags">
                      <span className={`agent-tag ${row.role}`}>
                        {row.role.toUpperCase()}
                      </span>
                      <span className={`agent-tag ${row.tier}`}>
                        {row.tier.toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className="agent-grid">
                    <div className="agent-stat">
                      <div className="value warn">
                        {Math.abs(Number(row.balance || 0)).toFixed(4)}
                      </div>
                      <div className="label">Court Balance (USDC)</div>
                    </div>
                    <div className="agent-stat">
                      <div className="value">{row.transactions}</div>
                      <div className="label">Transactions</div>
                    </div>
                    <div className="agent-stat">
                      <div className="value ok">{row.wins}</div>
                      <div className="label">Disputes Won</div>
                    </div>
                    <div className="agent-stat">
                      <div className="value bad">{row.losses}</div>
                      <div className="label">Disputes Lost</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
