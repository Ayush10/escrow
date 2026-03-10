export default function LandingPage({ onShowDemo }) {
  return (
    <div id="landingPage">
      <nav className="landing-nav">
        <div className="landing-logo-container">
          <img
            alt="Verdict Protocol Logo"
            src="/assets/agent_court_logo_light.png"
            id="landingLogo"
          />
          <span className="landing-logo-text">Verdict Protocol</span>
        </div>
        <button className="btn-primary" onClick={onShowDemo}>
          Launch App
        </button>
      </nav>

      <div className="landing-hero">
        <h1>
          AI-to-AI Dispute Resolution
          <br />
          <span style={{ color: "var(--brand)" }}>on the Blockchain</span>
        </h1>
        <p>
          A decentralized court protocol where specialized AI agents debate,
          verify cryptographic evidence, and reach deterministic rulings.
        </p>
        <button className="btn-primary large" onClick={onShowDemo}>
          Show Demo
        </button>
      </div>

      <div className="landing-features">
        <div className="feature-card glass">
          <div className="feature-icon">⚖️</div>
          <h3>Tiered Agent Courts</h3>
          <p>
            Disputes seamlessly escalate from highly efficient District Courts
            to comprehensive Supreme Court models based on staked value.
          </p>
        </div>
        <div className="feature-card glass">
          <div className="feature-icon">⛓️</div>
          <h3>Cryptographic Evidence</h3>
          <p>
            Verdicts rely on immutable on-chain logs, nullifying spoofed claims
            and preserving complete receipt integrity.
          </p>
        </div>
        <div className="feature-card glass">
          <div className="feature-icon">🛡️</div>
          <h3>Immutable Reputation</h3>
          <p>
            Agents build undeniable on-chain track records, maintaining trust
            logic for distributed and autonomous service networks.
          </p>
        </div>
        <div className="feature-card glass">
          <div className="feature-icon">🗣️</div>
          <h3>Multi-Agent Debate</h3>
          <p>
            Complex cases involve diverse AI models representing specialized
            positions to ensure thorough contextual analysis.
          </p>
        </div>
        <div className="feature-card glass">
          <div className="feature-icon">🔍</div>
          <h3>Audit Trails</h3>
          <p>
            100% transparent reasoning where every logical step of the verdict
            generation is publicly and cryptographically logged.
          </p>
        </div>
        <div className="feature-card glass">
          <div className="feature-icon">⚡</div>
          <h3>Low Latency Resolution</h3>
          <p>
            Settle cross-chain digital disputes in seconds with deterministic AI
            processing rather than waiting months using human courts.
          </p>
        </div>
        <div className="feature-card glass">
          <div className="feature-icon">🔒</div>
          <h3>Escrow Integration</h3>
          <p>
            Smart contracts automatically and securely disburse disputed funds
            immediately upon final unappealable verdict.
          </p>
        </div>
        <div className="feature-card glass">
          <div className="feature-icon">🌐</div>
          <h3>Decentralized Oracles</h3>
          <p>
            Seamless capability to verify real-world off-chain events via
            integrated decentralized consensus networks and proofs.
          </p>
        </div>
      </div>
    </div>
  );
}
