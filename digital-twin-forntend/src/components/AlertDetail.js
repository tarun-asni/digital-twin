import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import '../AlertDetail.css';
import { fetchAlertDetails } from '../utils/appClient'
import { formatFriendlyTimestamp } from '../utils/Helpers';

function AlertDetail() {
  const { alertId } = useParams();
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAlert() {
      try {
        const data = await fetchAlertDetails(alertId);
        setAlert(data);
      } catch (err) {
        console.error('Failed to load alert:', err);
      } finally {
        setLoading(false);
      }
    }
    loadAlert();
  }, [alertId]);

  if (loading) return <p>Loading alert details...</p>;
  if (!alert) return <p>No alert found.</p>;

  return (
    <>
      <div className="top-nav-bar">
      </div>
      <div className="alert-detail-container">
        <h2>Alert Details</h2>
        <div className="alert-meta-summary">
          <span className="alert-pair">
            <span className="alert-label-inline" title={alert.id}>
              Alert Id:
            </span>
            <span className="alert-value" title={alert.id}>
              {alert.id.slice(0, 8)}—{formatFriendlyTimestamp(alert.start_time)}
            </span>
          </span>
        </div>
        <div className="alert-columns">
          <div className="alert-left">
            <div className="alert-row">
              <span className="alert-label">{alert.message}</span>
            </div>
            <div className="alert-row inline-row">
              <span className={`alert-pair severity-${alert.severity.toLowerCase()}`}>
                <span className="alert-label-inline">Severity:</span>
                <span className="alert-value">{alert.severity}</span>
              </span>
              <span className="alert-pair camera-pair">
                <span className="alert-label-inline">Camera:</span>
                <span className="alert-value">{alert.camera_name}</span>
              </span>
            </div>
            <div className="video-section">
              <video
                src={alert.video_url}
                controls
                className="alert-video-player"
              />
            </div>
          </div>
          <div className="alert-right">
            <h3>Insight</h3>

             <div className="insight-row">
              <span className="insight-label">Status</span>
              <span className="insight-value">{alert.alert_analysis}</span>
            </div>

            <div className="insight-row">
              <span className="insight-label">Inference Analysis</span>
              <span className="insight-value">{alert.llm_response}</span>
            </div>

            <div className="insight-row">
              <span className="insight-label">Detection</span>
              <span className="insight-value">{alert.detection_class?.replace('_', ' ')}</span>
            </div>

            <div className="insight-row">
              <span className="insight-label">Severity</span>
              <span className="insight-value">{alert.severity}</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
export default AlertDetail;