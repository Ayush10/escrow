import { useState, useEffect, useCallback, useRef } from "react";
import { defaultRunnerUrl, deriveDefaultServices } from "./utils";

export function useVerdictServices() {
    const [runnerUrl, setRunnerUrl] = useState(defaultRunnerUrl());
    const [services, setServices] = useState(deriveDefaultServices(runnerUrl));
    const [isConnected, setIsConnected] = useState(false);
    const [explorerUrl, setExplorerUrl] = useState(
        "https://explorer.testnet3.goat.network"
    );
    const [contractAddress, setContractAddress] = useState("-");
    const [health, setHealth] = useState({});

    // Core Data State
    const [runs, setRuns] = useState([]);
    const [verdicts, setVerdicts] = useState([]);
    const [reputation, setReputation] = useState([]);
    const [agreements, setAgreements] = useState([]);
    const [courtStats, setCourtStats] = useState({
        disputes: 0,
        resolved: 0,
        services: 0,
        transactions: 0,
        escrow: 0,
    });

    // Active Run State
    const [activeRunId, setActiveRunId] = useState(null);
    const [activeRunStatus, setActiveRunStatus] = useState("idle");
    const [activeTimeline, setActiveTimeline] = useState([]);
    const [logs, setLogs] = useState([]);
    const streamRef = useRef(null);

    const fetchJson = async (url, options) => {
        const res = await fetch(url, options);
        let body = null;
        try {
            body = await res.json();
        } catch {
            body = null;
        }
        if (!res.ok) {
            const detail =
                (body && (body.detail || body.message || body.error)) ||
                `HTTP ${res.status}`;
            throw new Error(detail);
        }
        return body;
    };

    const appendLog = useCallback((msg) => {
        setLogs((prev) => [
            ...prev,
            { time: new Date().toISOString(), message: msg },
        ]);
    }, []);

    const connectAndRefresh = useCallback(async () => {
        try {
            const url = runnerUrl.trim().replace(/\/+$/, "");
            if (!url) throw new Error("Runner URL is empty");

            window.localStorage.setItem("vp_runner_url", url);
            const newServices = deriveDefaultServices(url);
            setServices(newServices);

            const healthData = await fetchJson(`${url}/health`);
            const cfg = await fetchJson(`${url}/config`);

            if (cfg.services) setServices(cfg.services);
            setIsConnected(true);
            setExplorerUrl(
                cfg.explorerUrl || healthData.explorer || explorerUrl
            );
            setContractAddress(
                cfg.contractAddress || healthData.contractAddress || "-"
            );
            appendLog("Connected securely to Runner");

            await Promise.allSettled([
                refreshHealth(newServices),
                refreshRuns(url),
                refreshVerdicts(newServices),
                refreshReputation(newServices),
            ]);
        } catch (err) {
            appendLog(`Connection Failed: ${err.message}`);
            setIsConnected(false);
        }
    }, [runnerUrl]);

    const refreshHealth = async (svc) => {
        const newHealth = {};
        for (const [name, base] of Object.entries(svc || services)) {
            try {
                const payload = await fetchJson(`${base}/health`);
                const status = (payload?.status || "ok").toLowerCase();
                newHealth[name] = status === "degraded" || status === "warn" ? "warn" : "ok";
            } catch {
                newHealth[name] = "down";
            }
        }
        setHealth(newHealth);
    };

    const refreshRuns = async (base = runnerUrl) => {
        try {
            const data = await fetchJson(`${base}/runs`);
            setRuns(data.runs || []);
        } catch (err) {
            appendLog(`Failed to fetch runs: ${err.message}`);
        }
    };

    const refreshVerdicts = async (svc = services) => {
        try {
            const payload = await fetchJson(`${svc.judge}/verdicts`);
            const items = (payload.items || []).map((item) => {
                if (item && typeof item.payload === "object") {
                    return { ...item.payload, status: item.status || item.payload.status };
                }
                return item || {};
            });
            setVerdicts(items);
            refreshCourtDashboard(svc, { verdicts: items });
        } catch (err) {
            appendLog(`Failed to load verdicts: ${err.message}`);
        }
    };

    const refreshReputation = async (svc = services) => {
        try {
            const payload = await fetchJson(`${svc.reputation}/reputation`);
            const items = payload.items || [];
            setReputation(items);
            refreshCourtDashboard(svc, { reputation: items });
        } catch (err) {
            appendLog(`Failed to load reputation: ${err.message}`);
        }
    };

    const refreshCourtDashboard = async (svc, seed = {}) => {
        try {
            let ag = [];
            try {
                const payload = await fetchJson(`${svc.evidence}/agreements?limit=300`);
                ag = payload.items || [];
            } catch {
                ag = [];
            }
            setAgreements(ag);

            const v = seed.verdicts || verdicts;
            setCourtStats({
                disputes: v.length,
                resolved: v.filter(x => ["submitted", "resolved", "complete"].includes(String(x.status).toLowerCase())).length,
                services: ag.length,
                transactions: ag.reduce((sum, item) => sum + Number(item.requestCount || item.receiptCount || 0), 0),
                escrow: v.reduce((sum, item) => sum + Math.max(0, Number(item.stake || 0)), 0),
            });

        } catch (err) {
            console.error(err);
        }
    };

    return {
        runnerUrl,
        setRunnerUrl,
        isConnected,
        connectAndRefresh,
        explorerUrl,
        contractAddress,
        health,
        runs,
        verdicts,
        reputation,
        agreements,
        courtStats,
        logs,
        activeRunId,
        activeRunStatus,
        activeTimeline,
        refreshRuns,
        refreshVerdicts,
        refreshReputation,
        appendLog
    };
}
