import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { fetchCameraDetails } from '../utils/appClient';
import '../CameraDetail.css';
import { formatFriendlyTimestamp } from '../utils/Helpers';
import { useLocation } from 'react-router-dom';
import MJPEGCanvas from "./MJPEGCanvas";
import { useNavigate } from 'react-router-dom';

function CameraDetail() {
  const { id } = useParams();
  const [camera, setCamera] = useState(null);
  const location = useLocation();
  const BASE_URL = process.env.REACT_APP_API_BASE_URL;
  const { url } = location.state || {};
  const [viewMode, setViewMode] = useState('live');
  const today = new Date().toISOString().split('T')[0];
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(today);
  const isStartDateValid = new Date(startDate) <= new Date(today);
  const isEndDateValid = new Date(endDate) >= new Date(today);
  const isDateRangeValid = new Date(startDate) <= new Date(endDate);
  const [activeTab, setActiveTab] = useState('cameras');
  const navigate = useNavigate();
  const filteredAlerts = camera?.alerts?.filter((alert) => {
    const alertDate = new Date(alert.start_time).toISOString().split('T')[0];
    return (
      (!startDate || alertDate >= startDate) &&
      (!endDate || alertDate <= endDate)
    );
  }) || [];
  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchCameraDetails(id);
        setCamera(data);
      } catch (err) {
        console.error('Camera fetch failed:', err);
      }
    }

    loadData();
  }, [id], [url]);

  if (!camera) return <p>Loading camera feed...</p>;

  const {
    name,
    camera_type,
    is_active,
    edge_url,
    alerts = [],
  } = camera;

  const getStreamUrl = () => {
    const annotate = viewMode === 'annotated' ? 'True' : 'False';
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}annotate=${annotate}&t=${Date.now()}`;
  };
  const handleClick = (alertId) => {
    window.open(`/alerts/${alertId}`, '_self', 'noopener,noreferrer');
  };

  return (
    <>
      <div className="camera-grid-wrapper">
        <div className="top-nav-bar-camera">
          <div className="nav-right">
            <button className="dashboard-button" onClick={() => navigate('/dashboard')}>
              Dashboard
            </button>
          </div>
        </div>
      </div>
      <div className="camera-detail-layout">
        <div className="camera-left-panel">
          <h2>{name} <span className="camera-type">({camera_type})</span></h2>
          <p>Status: <strong className={is_active ? 'status-active' : 'status-inactive'}>
            {is_active ? 'Active' : 'Inactive'}
          </strong></p>
          <div className="view-mode-toggle">
            <button
              className={viewMode === 'live' ? 'active' : ''}
              onClick={() => setViewMode('live')}
            >
              Live
            </button>
            <button
              className={viewMode === 'annotated' ? 'active' : ''}
              onClick={() => setViewMode('annotated')}
            >
              Ano
            </button>
          </div>
          <img
            src={getStreamUrl()}
            alt="MJPEG Stream"
            className="stream-image"
          />
        </div>
        <aside className="camera-right-panel">
          <div className="alerts-sorting">
            <div className="sort-group">
              <label>Date Range</label>
              <div className="date-range-row">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
                <span style={{ margin: '0 8px' }}>to</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  min={startDate === today ? today : startDate}
                  disabled={!startDate}
                />
              </div>
              {!isDateRangeValid && (
                <p className="date-warning">Start date should not be after end date.</p>
              )}
            </div>
          </div>

          <ul className="alert-list">
            {filteredAlerts.length === 0 ? (
              <p className="no-alerts-message">No alerts available for the selected date.</p>
            ) : (
              filteredAlerts.map((alert) => (
                <li key={alert.id} className={`alert-card severity-${alert.severity.toLowerCase()}`}>
                  <video
                    src={alert.video_url ? `${BASE_URL}${alert.video_url}` : alert.video_url}
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="alert-thumbnails"
                    onClick={() => handleClick(alert.id)}
                    style={{ cursor: 'pointer' }}
                  />
                  <div className="alert-meta">
                    <div className="alert-id" title={alert.id}>
                      {alert.id.slice(0, 15) + '...'}
                    </div>

                    <div className="alert-status">
                      <strong>Status:</strong> {alert.alert_analysis}
                    </div>

                    <div
                      className="alert-message"
                      title={alert.message}
                      onClick={() => handleClick(alert.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      {alert.message.split(' ').slice(0, 4).join(' ') + '...'}
                    </div>

                    <div className="alert-severity-block">
                      <div className="alert-severity">{alert.severity.toUpperCase()}</div>
                      <div className="alert-time">{formatFriendlyTimestamp(alert.start_time)}</div>
                    </div>
                  </div>
                </li>
              ))
            )}
          </ul>
        </aside>
      </div>
    </>
  );
}
export default CameraDetail;