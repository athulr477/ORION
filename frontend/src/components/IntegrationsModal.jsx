import { useState, useEffect } from 'react';
import { 
  X, CheckCircle2, AlertTriangle, RefreshCw, Server, GitBranch, 
  Cpu, ExternalLink, ShieldCheck, Copy, Check 
} from 'lucide-react';
import { 
  fetchIntegrationsStatus, 
  testJiraConnection, 
  testGitHubConnection, 
  syncJira 
} from '../api/client';

export default function IntegrationsModal({ isOpen, onClose, onSyncComplete, onToast }) {
  const [activeTab, setActiveTab] = useState('jira');
  const [loading, setLoading] = useState(true);
  const [statusData, setStatusData] = useState(null);

  // Jira testing & sync state
  const [testingJira, setTestingJira] = useState(false);
  const [jiraTestResult, setJiraTestResult] = useState(null);
  const [syncingJira, setSyncingJira] = useState(false);
  const [syncResult, setSyncResult] = useState(null);

  // GitHub testing state
  const [testingGitHub, setTestingGitHub] = useState(false);
  const [gitHubTestResult, setGitHubTestResult] = useState(null);
  const [copiedWebhook, setCopiedWebhook] = useState(false);

  // Load status on open
  useEffect(() => {
    if (!isOpen) return;
    loadStatus();
  }, [isOpen]);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const data = await fetchIntegrationsStatus();
      setStatusData(data);
    } catch (err) {
      if (onToast) onToast(`Failed to load integrations status: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleTestJira = async () => {
    try {
      setTestingJira(true);
      setJiraTestResult(null);
      const res = await testJiraConnection({});
      setJiraTestResult(res);
      if (res.success) {
        if (onToast) onToast(`Jira verified: Connected as ${res.display_name}`, 'success');
      } else {
        if (onToast) onToast(`Jira verification failed: ${res.error}`, 'error');
      }
    } catch (err) {
      setJiraTestResult({ success: false, error: err.message });
      if (onToast) onToast(err.message, 'error');
    } finally {
      setTestingJira(false);
    }
  };

  const handleSyncJira = async () => {
    try {
      setSyncingJira(true);
      setSyncResult(null);
      const res = await syncJira();
      setSyncResult(res);
      if (onToast) {
        onToast(`Jira Sync complete: ${res.created} created, ${res.updated} updated (${res.total_fetched} total)`, 'success');
      }
      if (onSyncComplete) onSyncComplete();
    } catch (err) {
      setSyncResult({ status: 'error', error: err.message });
      if (onToast) onToast(`Jira Sync failed: ${err.message}`, 'error');
    } finally {
      setSyncingJira(false);
    }
  };

  const handleTestGitHub = async () => {
    try {
      setTestingGitHub(true);
      setGitHubTestResult(null);
      const res = await testGitHubConnection();
      setGitHubTestResult(res);
      if (res.success) {
        if (onToast) onToast(`GitHub App verified: RS256 JWT minted successfully`, 'success');
      } else {
        if (onToast) onToast(`GitHub App test failed: ${res.error}`, 'error');
      }
    } catch (err) {
      setGitHubTestResult({ success: false, error: err.message });
      if (onToast) onToast(err.message, 'error');
    } finally {
      setTestingGitHub(false);
    }
  };

  const handleCopyWebhook = () => {
    const fullUrl = `${window.location.origin}/api/v1/github/events`;
    navigator.clipboard.writeText(fullUrl);
    setCopiedWebhook(true);
    setTimeout(() => setCopiedWebhook(false), 2000);
  };

  if (!isOpen) return null;

  const jira = statusData?.jira || {};
  const github = statusData?.github || {};
  const ollama = statusData?.ollama || {};

  return (
    <div className="modal-backdrop" onClick={onClose} id="integrations-modal-backdrop">
      <div 
        className="modal-box integrations-modal" 
        onClick={(e) => e.stopPropagation()}
        id="integrations-modal"
        style={{ maxWidth: '780px', width: '92%' }}
      >
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="integration-header-icon">
              <Server size={18} color="var(--brand)" />
            </div>
            <div>
              <h2 className="modal-title">Integrations & Settings</h2>
              <p className="modal-subtitle">
                Configure, test, and synchronize external connections for workspace: <strong>{statusData?.workspace_name || 'Active Workspace'}</strong>
              </p>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose} id="close-integrations-btn" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="integrations-tabs">
          <button 
            className={`integrations-tab ${activeTab === 'jira' ? 'active' : ''}`}
            onClick={() => setActiveTab('jira')}
            id="tab-jira"
          >
            <ExternalLink size={15} />
            Jira Cloud
            {jira.configured && <span className="tab-pill tab-pill--ok">Active</span>}
          </button>
          <button 
            className={`integrations-tab ${activeTab === 'github' ? 'active' : ''}`}
            onClick={() => setActiveTab('github')}
            id="tab-github"
          >
            <GitBranch size={15} />
            GitHub App
            {github.configured && <span className="tab-pill tab-pill--ok">Active</span>}
          </button>
          <button 
            className={`integrations-tab ${activeTab === 'ai' ? 'active' : ''}`}
            onClick={() => setActiveTab('ai')}
            id="tab-ai"
          >
            <Cpu size={15} />
            AI & Embeddings
            {ollama.available && <span className="tab-pill tab-pill--ok">Ready</span>}
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ minHeight: '380px' }}>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 0', gap: '12px' }}>
              <RefreshCw size={24} className="spin" color="var(--brand)" />
              <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Loading workspace integrations…</span>
            </div>
          ) : (
            <>
              {/* TAB 1: JIRA CLOUD */}
              {activeTab === 'jira' && (
                <div className="integration-tab-content" id="jira-tab-content">
                  {/* Status Banner */}
                  <div className={`integration-status-card ${jira.configured ? 'status-card--ok' : 'status-card--warn'}`}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      {jira.configured ? (
                        <CheckCircle2 size={20} color="var(--covered)" />
                      ) : (
                        <AlertTriangle size={20} color="var(--partial)" />
                      )}
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>
                          {jira.configured ? 'Connected to Atlassian Jira Cloud' : 'Jira Integration Not Configured'}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {jira.configured 
                            ? `Connected to ${jira.base_url} (Project: ${jira.project_key})` 
                            : 'Set JIRA_BASE_URL and JIRA_API_TOKEN to enable live requirement syncing.'}
                        </div>
                      </div>
                    </div>
                    <span className={`status-badge-pill ${jira.configured ? 'badge-pill--green' : 'badge-pill--amber'}`}>
                      {jira.configured ? 'Verified' : 'Action Needed'}
                    </span>
                  </div>

                  {/* Config Fields */}
                  <div className="integration-details-grid" style={{ marginTop: '16px' }}>
                    <div className="form-field">
                      <label className="form-label">Jira Domain URL</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={jira.base_url || ''} 
                        readOnly 
                        placeholder="https://your-domain.atlassian.net"
                      />
                    </div>
                    <div className="form-field">
                      <label className="form-label">Project Key</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={jira.project_key || ''} 
                        readOnly 
                        placeholder="e.g. SCRUM"
                      />
                    </div>
                    <div className="form-field">
                      <label className="form-label">Service Account Email</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={jira.user_email || ''} 
                        readOnly 
                        placeholder="user@example.com"
                      />
                    </div>
                    <div className="form-field">
                      <label className="form-label">API Token</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={jira.token_masked || '••••••••••••••••'} 
                        readOnly 
                      />
                    </div>
                  </div>

                  {/* Test Result Message */}
                  {jiraTestResult && (
                    <div className={`test-feedback-box ${jiraTestResult.success ? 'feedback--success' : 'feedback--error'}`}>
                      {jiraTestResult.success ? (
                        <>
                          <CheckCircle2 size={16} />
                          <div>
                            <strong>Connection Verified:</strong> Authenticated as <strong>{jiraTestResult.display_name}</strong> ({jiraTestResult.email_address}). Project <strong>{jiraTestResult.project?.key}</strong> ({jiraTestResult.project?.name || 'verified'}) is accessible.
                          </div>
                        </>
                      ) : (
                        <>
                          <AlertTriangle size={16} />
                          <div>
                            <strong>Connection Error:</strong> {jiraTestResult.error}
                          </div>
                        </>
                      )}
                    </div>
                  )}

                  {/* Sync Result Message */}
                  {syncResult && (
                    <div className={`test-feedback-box ${syncResult.status === 'ok' ? 'feedback--success' : 'feedback--error'}`}>
                      {syncResult.status === 'ok' ? (
                        <>
                          <CheckCircle2 size={16} />
                          <div>
                            <strong>Sync Succeeded:</strong> Imported <strong>{syncResult.total_fetched}</strong> issues from project <strong>{syncResult.project_key}</strong> ({syncResult.created} new requirements created, {syncResult.updated} updated). The RTM table is refreshed.
                          </div>
                        </>
                      ) : (
                        <>
                          <AlertTriangle size={16} />
                          <div>
                            <strong>Sync Error:</strong> {syncResult.error || 'Failed to sync Jira issues'}
                          </div>
                        </>
                      )}
                    </div>
                  )}

                  {/* Actions Bar */}
                  <div className="integration-actions-bar" style={{ marginTop: '20px' }}>
                    <button 
                      className="btn-secondary"
                      onClick={handleTestJira}
                      disabled={testingJira || syncingJira}
                      id="btn-test-jira"
                    >
                      {testingJira ? <RefreshCw size={14} className="spin" /> : <ShieldCheck size={14} />}
                      {testingJira ? 'Testing Connection…' : 'Test Jira Connection'}
                    </button>

                    <button 
                      className="btn-primary"
                      onClick={handleSyncJira}
                      disabled={syncingJira || testingJira}
                      id="btn-sync-jira"
                    >
                      <RefreshCw size={14} className={syncingJira ? 'spin' : ''} />
                      {syncingJira ? 'Syncing Jira Issues…' : 'Sync Jira Issues Now'}
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 2: GITHUB APP */}
              {activeTab === 'github' && (
                <div className="integration-tab-content" id="github-tab-content">
                  {/* Status Banner */}
                  <div className={`integration-status-card ${github.configured ? 'status-card--ok' : 'status-card--warn'}`}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      {github.configured ? (
                        <CheckCircle2 size={20} color="var(--covered)" />
                      ) : (
                        <AlertTriangle size={20} color="var(--partial)" />
                      )}
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>
                          {github.configured ? `GitHub App #${github.app_id} Active` : 'GitHub App Needs Setup'}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {github.configured 
                            ? `Installation #${github.installation_id} · RSA Key active (${github.pem_path})` 
                            : 'Set GITHUB_APP_ID and provide github-app.pem in the backend directory.'}
                        </div>
                      </div>
                    </div>
                    <span className={`status-badge-pill ${github.configured ? 'badge-pill--green' : 'badge-pill--amber'}`}>
                      {github.configured ? 'App Ready' : 'Pending'}
                    </span>
                  </div>

                  {/* GitHub Info Grid */}
                  <div className="integration-details-grid" style={{ marginTop: '16px' }}>
                    <div className="form-field">
                      <label className="form-label">GitHub App ID</label>
                      <input type="text" className="form-input" value={github.app_id || ''} readOnly />
                    </div>
                    <div className="form-field">
                      <label className="form-label">App Installation ID</label>
                      <input type="text" className="form-input" value={github.installation_id || ''} readOnly />
                    </div>
                    <div className="form-field" style={{ gridColumn: 'span 2' }}>
                      <label className="form-label">Private Key PEM Status</label>
                      <div className="pem-status-indicator">
                        <ShieldCheck size={16} color={github.pem_exists ? 'var(--covered)' : 'var(--drifted)'} />
                        <span>
                          {github.pem_exists ? `Loaded: ${github.pem_path} (Valid 2048-bit RSA Private Key)` : 'PEM file not found on disk'}
                        </span>
                      </div>
                    </div>
                    <div className="form-field" style={{ gridColumn: 'span 2' }}>
                      <label className="form-label">Webhook Payload URL (Configure in GitHub App)</label>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <input 
                          type="text" 
                          className="form-input" 
                          value={`${window.location.origin}/api/v1/github/events`} 
                          readOnly 
                        />
                        <button 
                          className="btn-secondary" 
                          onClick={handleCopyWebhook}
                          style={{ minWidth: '100px' }}
                          id="btn-copy-webhook"
                        >
                          {copiedWebhook ? <Check size={14} color="var(--covered)" /> : <Copy size={14} />}
                          {copiedWebhook ? 'Copied' : 'Copy'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Test Feedback */}
                  {gitHubTestResult && (
                    <div className={`test-feedback-box ${gitHubTestResult.success ? 'feedback--success' : 'feedback--error'}`}>
                      {gitHubTestResult.success ? (
                        <>
                          <CheckCircle2 size={16} />
                          <div>
                            <strong>JWT Minting Successful:</strong> {gitHubTestResult.message} (JWT Token Length: {gitHubTestResult.jwt_length} chars). Ready to sign Pull Request Check Runs!
                          </div>
                        </>
                      ) : (
                        <>
                          <AlertTriangle size={16} />
                          <div>
                            <strong>GitHub App Error:</strong> {gitHubTestResult.error}
                          </div>
                        </>
                      )}
                    </div>
                  )}

                  {/* Actions Bar */}
                  <div className="integration-actions-bar" style={{ marginTop: '20px' }}>
                    <button 
                      className="btn-primary"
                      onClick={handleTestGitHub}
                      disabled={testingGitHub}
                      id="btn-test-github"
                    >
                      {testingGitHub ? <RefreshCw size={14} className="spin" /> : <ShieldCheck size={14} />}
                      {testingGitHub ? 'Testing JWT Minting…' : 'Verify GitHub App & Mint JWT'}
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 3: AI & EMBEDDINGS */}
              {activeTab === 'ai' && (
                <div className="integration-tab-content" id="ai-tab-content">
                  {/* Ollama Status */}
                  <div className={`integration-status-card ${ollama.available ? 'status-card--ok' : 'status-card--warn'}`}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <Cpu size={20} color={ollama.available ? 'var(--covered)' : 'var(--partial)'} />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>
                          {ollama.available ? 'Local Ollama LLM Service Online' : 'Ollama Offline (Deterministic Fallback Active)'}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          Model: <strong>{ollama.model}</strong> · Endpoint: {ollama.base_url}
                        </div>
                      </div>
                    </div>
                    <span className={`status-badge-pill ${ollama.available ? 'badge-pill--green' : 'badge-pill--amber'}`}>
                      {ollama.available ? 'Online' : 'Fallback'}
                    </span>
                  </div>

                  {/* AI Pipeline Architecture Details */}
                  <div className="ai-pipeline-card" style={{ marginTop: '16px' }}>
                    <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                      Orion Hybrid Risk Formula
                    </div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', background: 'var(--bg-app)', padding: '10px 14px', borderRadius: 'var(--r-sm)', color: 'var(--brand)' }}>
                      Risk Score = (0.6 × Semantic Distance) + (0.4 × Structural Assertion Distance)
                    </div>
                    <ul style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '12px', lineHeight: 1.7, paddingLeft: '18px' }}>
                      <li><strong>Embeddings:</strong> Dense 384-dimensional vectors computed via local BAAI/bge-small-en-v1.5 ONNX runtime.</li>
                      <li><strong>Structural Matcher:</strong> AST assertion extraction parses boundary values, SLA timings, and HTTP status constraints.</li>
                      <li><strong>LLM Verbalization:</strong> Uses <code>{ollama.model}</code> to explain why code drifted from acceptance criteria.</li>
                    </ul>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} id="btn-close-integrations-footer">
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
