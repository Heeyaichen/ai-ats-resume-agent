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
import { Loader2, Send, RefreshCw, LogOut } from "lucide-react";

const Home: React.FC = () => {
  const { instance, accounts } = useMsal();
  const account = accounts[0];

  // ── Auth ──────────────────────────────────────────────────────
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
        // Fetch the final score from the API.
        if (jobId) {
          fetchScore(jobId)
            .then((payload) => {
              if (payload.score_data) {
                setScoreData(payload.score_data);
              }
            })
            .catch(() => {
              // Score fetch failure is non-critical here.
            });
        }
      } else if (evt.event_type === "error") {
        setErrorMsg(evt.message);
        setJobState("error");
      }
    },
    [jobId],
  );

  const { events: sseEvents } = useSSEStream(
    jobState === "agent_running" || jobState === "queued" ? jobId : null,
    handleSSEEvent,
  );

  // Derive agent_running from first tool_call event.
  React.useEffect(() => {
    if (
      jobState === "queued" &&
      sseEvents.some((e) => e.event_type === "tool_call")
    ) {
      setJobState("agent_running");
    }
  }, [sseEvents, jobState]);

  // Derive completion from last SSE event.
  React.useEffect(() => {
    const last = sseEvents[sseEvents.length - 1];
    if (last?.event_type === "complete") {
      setJobState(
        scoreData?.human_review_required
          ? "completed_with_review"
          : "completed",
      );
    }
  }, [sseEvents, scoreData]);

  // ── Upload handler ────────────────────────────────────────────
  const handleUpload = async () => {
    if (!file || !jd.trim()) return;

    setJobState("uploading");
    setErrorMsg(null);
    setScoreData(null);

    try {
      // Ensure we have a fresh token.
      const resp = await instance.acquireTokenSilent(loginRequest);
      setAuthToken(resp.accessToken);

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
  if (!account) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <button
          onClick={handleLogin}
          className="rounded-lg bg-blue-600 px-6 py-3 text-white font-medium hover:bg-blue-700 transition-colors"
        >
          Sign in with Microsoft
        </button>
      </div>
    );
  }

  const isBusy = jobState === "uploading" || jobState === "queued" || jobState === "agent_running";
  const showReport = isTerminalState(jobState) && scoreData;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">ATS Resume Screening Agent</h1>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>

      {/* Upload section */}
      {!isTerminalState(jobState) && (
        <div className="rounded-xl border bg-white p-6 space-y-5">
          <UploadPanel disabled={isBusy} onFileSelected={setFile} />
          <JobDescriptionPanel value={jd} onChange={setJd} disabled={isBusy} />

          <button
            onClick={handleUpload}
            disabled={isBusy || !file || !jd.trim() || jd.length > 50000}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-white font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {isBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {jobState === "idle" ? "Screen Resume" : "Processing..."}
          </button>
        </div>
      )}

      {/* Error */}
      {errorMsg && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {/* Agent trace */}
      {(jobState === "queued" || jobState === "agent_running") && (
        <div className="rounded-xl border bg-white p-6">
          <h2 className="text-lg font-semibold mb-3">Agent Progress</h2>
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

          {/* Score + breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border bg-white p-6 flex flex-col items-center">
              <h2 className="text-lg font-semibold mb-4 self-start">Score</h2>
              <ScoreGauge score={scoreData.score} />
            </div>
            <div className="rounded-xl border bg-white p-6">
              <h2 className="text-lg font-semibold mb-4">Breakdown</h2>
              <ScoreBreakdown
                breakdown={scoreData.breakdown}
                semanticSimilarity={scoreData.semantic_similarity}
              />
            </div>
          </div>

          {/* Keywords */}
          <div className="rounded-xl border bg-white p-6">
            <h2 className="text-lg font-semibold mb-3">Keywords</h2>
            <KeywordBadges
              matched={scoreData.matched_keywords}
              missing={scoreData.missing_keywords}
            />
          </div>

          {/* Fit summary */}
          {scoreData.fit_summary && (
            <div className="rounded-xl border bg-white p-6">
              <h2 className="text-lg font-semibold mb-2">Fit Summary</h2>
              <p className="text-sm text-gray-700 leading-relaxed">
                {scoreData.fit_summary}
              </p>
            </div>
          )}

          {/* Trace */}
          <div className="rounded-xl border bg-white p-6">
            <h2 className="text-lg font-semibold mb-3">Agent Trace</h2>
            <AgentTracePanel events={sseEvents} />
          </div>

          {/* Privacy badges (placeholder — real values from agent trace) */}
          <div className="rounded-xl border bg-white p-6">
            <h2 className="text-lg font-semibold mb-3">Privacy</h2>
            <PrivacyBadges piiRedacted={true} />
          </div>

          {/* Reset */}
          <button
            onClick={handleReset}
            className="flex items-center gap-2 rounded-lg border px-5 py-2.5 font-medium hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Screen Another Resume
          </button>
        </div>
      )}
    </div>
  );
};

export default Home;
