import React, { useState } from "react";
import VoiceCommandPanel from "./VoiceCommandPanel";
import Sidebar from "../components/SideBar";
import securityIcon from "../images/security-cameras.png";
import { hasRole, ROLES } from "../utils/Helpers";
import "../VoicePrompt.css";
import { formatFriendlyTimestamp } from '../utils/Helpers';

const VoicePrompt = () => {
  const [voiceResponse, setVoiceResponse] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const alertsPerPage = 10;
  const BASE_URL = process.env.REACT_APP_API_BASE_URL;
  const [sortField, setSortField] = useState('start_time');
  const [sortOrder, setSortOrder] = useState('desc');
  const [showLeftMenu, setShowLeftMenu] = useState(false);
  const username = localStorage.getItem("username");

  const handleSignOut = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  const hasRoleFn = (allowedRoles) => {
    const role = localStorage.getItem("role");
    return allowedRoles.includes(ROLES.ALL) || allowedRoles.includes(role);
  };

  const handleVoiceResponse = (response) => {
    setVoiceResponse(response.command);
    setAlerts(response.alerts || []);
    setCurrentPage(1);
  };

  const sortedAlerts = [...alerts].sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];

    if (sortField === 'start_time') {
      valA = new Date(valA).getTime();
      valB = new Date(valB).getTime();
    }

    if (sortField === 'severity') {
      const severityRank = { low: 1, medium: 2, high: 3 };
      valA = severityRank[a.severity.toLowerCase()] || 0;
      valB = severityRank[b.severity.toLowerCase()] || 0;
    }

    return sortOrder === 'asc' ? valA - valB : valB - valA;
  });

  const paginatedAlerts = sortedAlerts.slice(
    (currentPage - 1) * alertsPerPage,
    currentPage * alertsPerPage
  );
  const toggleSort = (field) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };
  const totalPages = Math.ceil(alerts.length / alertsPerPage);
  return (
    <>
      <div
        className="voice-wrapper"
        style={{
          display: "grid",
          gridTemplateColumns: showLeftMenu ? "240px 1fr" : "0px 1fr",
          transition: "grid-template-columns 0.3s ease",
          height: "100vh",
          overflow: "hidden"
        }}
      >
        <Sidebar
          username={username}
          handleSignOut={handleSignOut}
          hasRole={hasRoleFn}
          title=""
          collapsed={!showLeftMenu}
        />
        <div
          className="main-content"
          style={{
            flexGrow: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden"
          }}

        >
          {/* Header */}
          <div className="top-nav-bar d-flex align-items-center px-3 py-2 gap-2">
            <button
              className="btn btn-link text-white p-0 icon-only"
              onClick={() => setShowLeftMenu(prev => !prev)}
              title={showLeftMenu ? "Close Menu" : "Open Menu"}
              aria-label="Toggle Sidebar"
            >
              <img src={securityIcon} alt="Toggle Sidebar" className="sidebar-toggle-icon" />
            </button>
            <span className="text-white fw-semibold voice-header-title">Voice Alerts</span>
          </div>

          <div className="voice-prompt-container" style={{ flexGrow: 1, overflowY: "auto", }}>
            {!voiceResponse ? (
              <div className="center-panel">
                <VoiceCommandPanel onResponse={handleVoiceResponse} />
              </div>
            ) : (
              <>
                <div className="status-box">
                  <strong>Status:</strong> Say <code>'hello applied'</code> to activate...
                </div>

                <div className="heard-box">
                  <strong>Command:</strong> {voiceResponse.replace(/hello applied/i, '').trim()}
                </div>

                <h3 className="alerts-title">Alerts</h3>
                <table className="alerts-table">
                  <thead>
                    <tr>
                      <th>Video</th>
                      <th>Message</th>
                      <th onClick={() => toggleSort('severity')} style={{ cursor: 'pointer' }}>
                        Severity {sortField === 'severity' && (sortOrder === 'asc' ? '▲' : '▼')}
                      </th>
                      <th onClick={() => toggleSort('start_time')} style={{ cursor: 'pointer' }}>
                        Date {sortField === 'start_time' && (sortOrder === 'asc' ? '▲' : '▼')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedAlerts.map((alert) => (
                      <tr key={alert.id}>
                        <td>
                          {alert.video_url ? (
                            <video
                              src={`${BASE_URL}${alert.video_url}`}
                              autoPlay
                              loop
                              muted
                              playsInline
                              className="alert-thumbnail"
                            />
                          ) : (
                            <div className="no-video">No video available</div>
                          )}
                        </td>
                        <td>{alert.message}</td>
                        <td className={`severity-${alert.severity.toLowerCase()}`}>{alert.severity}</td>
                        <td><span>{formatFriendlyTimestamp(alert.start_time)}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="pagination">
                  {Array.from({ length: totalPages }, (_, i) => (
                    <button
                      key={i}
                      className={`page-btn ${currentPage === i + 1 ? "active" : ""}`}
                      onClick={() => setCurrentPage(i + 1)}
                    >
                      {i + 1}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

    </>
  );
};
export default VoicePrompt;