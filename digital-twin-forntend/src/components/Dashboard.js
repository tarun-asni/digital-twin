import React, { useEffect, useState } from "react";
import { usePagination } from "../Hooks/usePagination";
import CameraGridPage from "../components/CameraGridPage";
import { fetchLiveFeeds } from "../utils/appClient";
import enableImg from '../assets/enable.png';
import togglebutton from '../assets/toggle-button.png';
import arrowsImage from '../assets/grid.png';
import VoiceCommandPanel from './VoiceCommandPanel';
import { useNavigate } from 'react-router-dom';
import dashboardIcon from '../images/dashboard.svg';
import securityIcon from '../images/security-cameras.png';
import { hasRole, ROLES } from '../utils/Helpers';
import Sidebar from "../components/SideBar"
const FEEDS_PER_PAGE = 4;

function Dashboard() {
  const [streams, setStreams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enabled, setEnabled] = useState(false);
  const [showLeftMenu, setShowLeftMenu] = useState(false);
  const navigate = useNavigate();
  const username = localStorage.getItem("username");
  const role = localStorage.getItem("role");
  const hasRoleFn = (allowedRoles) => allowedRoles.includes(ROLES.ALL) || allowedRoles.includes(role);

  const handleSignOut = () => {
    localStorage.clear();
    navigate("/login");
  };

  useEffect(() => {
    fetchLiveFeeds()
      .then((data) => {
        const formatted = data.map((stream, index) => ({
          id: stream.camera_id || `cam${index + 1}`,
          url: stream.stream_url,
          type: stream.type || "image/jpeg",
          name: stream.name || `Camera ${index + 1}`,
        }));

        setStreams(formatted);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching feeds:", err);
        setLoading(false);
      });
  }, []);

  const {
    currentItems,
    page,
    pageCount,
    goToNext,
    goToPrev,
    goToPage
  } = usePagination(streams, FEEDS_PER_PAGE);
  const annotatedStreams = currentItems.map((stream) => ({
    ...stream,
    url: stream.url.includes('?')
      ? `${stream.url}&annotate=${enabled ? 'True' : 'False'}`
      : `${stream.url}?annotate=${enabled ? 'True' : 'False'}`
  }))

  if (loading) return <p style={{ color: "#fff", padding: "20px" }}>Loading live feeds…</p>;
  const handleEnableClick = async () => {
    setEnabled(prev => !prev);
    const newState = !enabled;
    setEnabled(newState);
    try {
      const data = await fetchLiveFeeds(newState);
      console.log('Annotated Feed:', data);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <>
      <div
        className="dashboard-wrapper"
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
          title="Dashboard"
          collapsed={!showLeftMenu}
        />

        <div
          className="main-content"
          style={{
            height: "100vh",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden"
          }}
        >



          <div className="dashboard-header">
            <div className="header-bar">
              <div className="header-section">
                <div className="live-feed-label d-flex align-items-center gap-2">
                  <button
                    className="btn btn-link text-white p-0 icon-only"
                    onClick={() => setShowLeftMenu(prev => !prev)}
                    data-bs-toggle="tooltip"
                    data-bs-placement="bottom"
                    title={showLeftMenu ? "Close Menu" : "Open Menu"}
                    aria-label="Toggle Sidebar"
                  >
                    <img
                      src={securityIcon}
                      alt="Dashboard Icon"
                      className="sidebar-toggle-icon"
                    />

                  </button>

                  <span className="text-white fw-semibold">Live Feed Monitoring</span>
                </div>

                {pageCount > 1 && (
                  <div
                    className="pagination-header"
                    style={{
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                      gap: "8px",
                      marginTop: "8px",
                      paddingBottom: "8px",
                      color: "#fff",
                      fontSize: "14px",
                    }}
                  >
                    <button
                      onClick={goToPrev}
                      disabled={page === 0}
                      style={{
                        backgroundColor: "#222",
                        color: "#fff",
                        border: "1px solid #555",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        cursor: page === 0 ? "not-allowed" : "pointer",
                      }}
                    >
                      ◀
                    </button>

                    {Array.from({ length: pageCount }, (_, i) => (
                      <button
                        key={i}
                        onClick={() => goToPage(i)}
                        style={{
                          backgroundColor: page === i ? "#007bff" : "#222",
                          color: "#fff",
                          border: "1px solid #555",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          cursor: "pointer",
                        }}
                      >
                        {i + 1}
                      </button>
                    ))}

                    <button
                      onClick={goToNext}
                      disabled={page === pageCount - 1}
                      style={{
                        backgroundColor: "#222",
                        color: "#fff",
                        border: "1px solid #555",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        cursor: page === pageCount - 1 ? "not-allowed" : "pointer",
                      }}
                    >
                      ▶
                    </button>
                  </div>
                )}
              </div>

              <div className="header-section">
              </div>

              <div className="header-controls">
                <div className="form-check form-switch">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    role="switch"
                    id="aiToggle"
                    checked={enabled}
                    onChange={handleEnableClick}
                  />
                  <label className="form-check-label text-white fw-semibold" htmlFor="aiToggle">
                    {enabled ? "AI Annotated" : "Live Feed"}
                  </label>
                </div>
              </div>

            </div>
          </div>
          <main style={{ flexGrow: 1, backgroundColor: "#fff", overflow: "hidden" }}>
            <CameraGridPage
              streams={annotatedStreams}
              showLeftMenu={showLeftMenu}
              columns={2}
              rows={2}
            />
          </main>
        </div>
      </div>
    </>
  );
}

export default Dashboard;