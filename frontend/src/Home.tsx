/** Home page — orchestrates upload, SSE, trace panel, and report dashboard. */

import React, { useCallback, useState } from "react";
import { useMsal } from "@azure/msal-react";
import { loginRequest } from "./authConfig";
import { setAuthToken, uploadResume, fetchScore } from "./api";
import { useSSEStream } from "./useSSEStream";
import {
  JobState,
  UploadResponse,
  ScoreData,
  SSEEvent,
  isTerminalState,
} from "./types";
import UploadPanel from "./components/UploadPanel";
import JobDescriptionPanel from "./components/JobDescriptionPanel";
import AgentTracePanel from "./components/AgentTracePanel";
import ScoreGauge from "./components/ScoreGauge";
import ScoreBreakdown from "./components/ScoreBreakdown";
import KeywordBadges from "./components/KeywordBadges";
import HumanReviewBanner from "./components/HumanReviewBanner";
import PrivacyBadges from "./components/PrivacyBadges";
import { Loader2, ArrowRight, ArrowLeft, LogOut } from "lucide-react";

const Home: React.FC = () => {
  const { instance, accounts } = useMsal();
  const account = accounts[0];

  // ── Auth ──────────────────────────────────────────────────────
  const isAuthConfigured = !!import.meta.env.VITE_AZURE_CLIENT_ID;
  const isLocalDev = import.meta.env.DEV;
  const handleLogin = useCallback(async () => {
    const resp = await instance.loginPopup(loginRequest);
    setAuthToken(resp.accessToken);
  }, [instance]);

  const handleLogout = useCallback(() => {
    instance.logoutPopup();
  }, [instance]);

  // ── Form state ────────────────────────────────────────────────
  const [file, setFile] = useState<File | null>(null);
  const [jd, setJd] = useState("");
  const [jobState, setJobState] = useState<JobState>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [scoreData, setScoreData] = useState<ScoreData | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ── SSE ───────────────────────────────────────────────────────
  const handleSSEEvent = useCallback(
    (evt: SSEEvent) => {
      if (evt.event_type === "complete") {
        setScoreData(evt.result);
      } else if (evt.event_type === "error") {
        setErrorMsg(evt.message);
        setJobState("error");
      }
    },
    [],
  );

  const { events: sseEvents } = useSSEStream(
    jobState === "agent_running" || jobState === "queued" ? jobId : null,
    handleSSEEvent,
  );

  React.useEffect(() => {
    if (
      jobState === "queued" &&
      sseEvents.some((e) => e.event_type === "tool_call")
    ) {
      setJobState("agent_running");
    }
  }, [sseEvents, jobState]);

  React.useEffect(() => {
    const last = sseEvents[sseEvents.length - 1];
    if (last?.event_type === "complete") {
      setJobState(
        last.result?.human_review_required
          ? "completed_with_review"
          : "completed",
      );
    }
  }, [sseEvents]);

  // ── Score polling fallback ──────────────────────────────────
  React.useEffect(() => {
    if (!jobId || isTerminalState(jobState)) return;
    const id = setInterval(async () => {
      try {
        const payload = await fetchScore(jobId);
        if (payload.score_data) {
          setScoreData(payload.score_data);
        }
        if (
          payload.status === "completed" ||
          payload.status === "completed_with_review" ||
          payload.status === "failed_review_required"
        ) {
          setJobState(payload.status as JobState);
        }
      } catch {
        // Polling failure is non-fatal; SSE may still deliver.
      }
    }, 5000);
    return () => clearInterval(id);
  }, [jobId, jobState]);

  // ── Upload handler ────────────────────────────────────────────
  const handleUpload = async () => {
    if (!file || !jd.trim()) return;

    setJobState("uploading");
    setErrorMsg(null);
    setScoreData(null);

    try {
      if (isAuthConfigured && account) {
        const resp = await instance.acquireTokenSilent(loginRequest);
        setAuthToken(resp.accessToken);
      }

      const result: UploadResponse = await uploadResume(file, jd);
      setJobId(result.job_id);
      setJobState("queued");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Upload failed.");
      setJobState("error");
    }
  };

  // ── Reset handler ─────────────────────────────────────────────
  const handleReset = () => {
    setFile(null);
    setJd("");
    setJobState("idle");
    setJobId(null);
    setScoreData(null);
    setErrorMsg(null);
  };

  // ── Render ────────────────────────────────────────────────────
  if (!isAuthConfigured && !isLocalDev) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <p className="text-sm text-[#ff3b30]">
          Authentication is not configured. Contact your administrator.
        </p>
      </div>
    );
  }

  if (isAuthConfigured && !account) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-6">
        <h1 className="text-2xl font-semibold tracking-tight text-label">
          Resume Screen
        </h1>
        <button
          onClick={handleLogin}
          className="rounded-lg bg-accent px-8 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
        >
          Sign in with Microsoft
        </button>
      </div>
    );
  }

  const isBusy = jobState === "uploading" || jobState === "queued" || jobState === "agent_running";
  const isTerminal = isTerminalState(jobState);
  const showReport = isTerminal && scoreData;
  const showReviewOnly = isTerminal && !scoreData;

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      {/* Header */}
      <header className="flex items-center justify-between pb-10">
        <h1 className="text-2xl font-semibold tracking-tight text-label">
          Resume Screen
        </h1>
        {isAuthConfigured && (
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-sm text-secondary transition-colors hover:text-label"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        )}
      </header>

      {/* Upload section */}
      {!isTerminalState(jobState) && (
        <div className="rounded-lg border border-separator bg-white p-8 space-y-6">
          <UploadPanel disabled={isBusy} onFileSelected={setFile} />
          <JobDescriptionPanel value={jd} onChange={setJd} disabled={isBusy} />

          <button
            onClick={handleUpload}
            disabled={isBusy || !file || !jd.trim() || jd.length > 50000}
            className="flex items-center justify-center gap-2 rounded-lg bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:pointer-events-none disabled:opacity-40"
          >
            {isBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
            {jobState === "idle" ? "Screen Resume" : "Processing"}
          </button>
        </div>
      )}

      {/* Error */}
      {errorMsg && (
        <div className="mt-6 rounded-lg border border-[#ff3b30]/20 bg-[#ff3b30]/[0.04] px-4 py-3 text-sm text-[#ff3b30]">
          {errorMsg}
        </div>
      )}

      {/* Agent trace during processing */}
      {(jobState === "queued" || jobState === "agent_running") && (
        <div className="mt-6 rounded-lg border border-separator bg-white p-8">
          <h2 className="text-xs font-medium uppercase tracking-wide text-secondary mb-4">
            Screening Progress
          </h2>
          <AgentTracePanel events={sseEvents} />
        </div>
      )}

      {/* Report dashboard */}
      {showReport && scoreData && (
        <div className="space-y-6">
          {/* Human review banner */}
          {scoreData.human_review_required && (
            <HumanReviewBanner reason={scoreData.human_review_reason} />
          )}

          {/* Score + Breakdown */}
          <div className="rounded-lg border border-separator bg-white overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-separator">
              <div className="p-8 flex flex-col items-center">
                <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-6 self-start">
                  Score
                </p>
                <ScoreGauge score={scoreData.score} />
              </div>
              <div className="p-8">
                <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-6">
                  Breakdown
                </p>
                <ScoreBreakdown
                  breakdown={scoreData.breakdown}
                  semanticSimilarity={scoreData.semantic_similarity}
                />
              </div>
            </div>
          </div>

          {/* Keywords + Fit Summary */}
          <div className="rounded-lg border border-separator bg-white overflow-hidden">
            <div className="p-8 space-y-8">
              {/* Keywords */}
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-4">
                  Keywords
                </p>
                <KeywordBadges
                  matched={scoreData.matched_keywords}
                  missing={scoreData.missing_keywords}
                />
              </div>

              {/* Fit summary */}
              {scoreData.fit_summary && (
                <>
                  <div className="border-t border-separator" />
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-3">
                      Fit Summary
                    </p>
                    <p className="text-sm text-label leading-relaxed">
                      {scoreData.fit_summary}
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Agent Trace */}
          <div className="rounded-lg border border-separator bg-white p-8">
            <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-4">
              Agent Trace
            </p>
            <AgentTracePanel events={sseEvents} />
          </div>

          {/* Privacy */}
          <div className="rounded-lg border border-separator bg-white p-8">
            <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-4">
              Privacy
            </p>
            <PrivacyBadges piiRedacted={true} />
          </div>

          {/* Reset */}
          <div className="pb-8">
            <button
              onClick={handleReset}
              className="flex items-center gap-2 rounded-lg border border-separator px-6 py-3 text-sm font-medium text-label transition-colors hover:bg-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Screen Another Resume
            </button>
          </div>
        </div>
      )}

      {/* Terminal without score */}
      {showReviewOnly && (
        <div className="space-y-6">
          <HumanReviewBanner
            reason={
              jobState === "failed_review_required"
                ? "The agent was unable to fully process this resume. Manual review is required."
                : "The resume was flagged for human review. No automated score was produced."
            }
          />

          <div className="rounded-lg border border-separator bg-white p-8">
            <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-4">
              Agent Trace
            </p>
            <AgentTracePanel events={sseEvents} />
          </div>

          <div className="pb-8">
            <button
              onClick={handleReset}
              className="flex items-center gap-2 rounded-lg border border-separator px-6 py-3 text-sm font-medium text-label transition-colors hover:bg-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Screen Another Resume
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
