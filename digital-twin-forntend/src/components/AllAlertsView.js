import React, { useMemo, useState, useEffect } from "react";
import "../AllAlertsView.css";
import { getDroneStatus } from "../utils/Helpers";
function AllAlertsView({ alerts = [], expandedAlertId, setExpandedAlertId, setSelectedAlert, setShowDeviceModal, renderPagination }) {
  const [filterId, setFilterId] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("All");
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [alertsPerPage, setAlertsPerPage] = useState(10);

  const today = new Date();
  const startDate = filterStartDate ? new Date(`${filterStartDate}T00:00:00`) : null;
  const endDate = filterEndDate ? new Date(`${filterEndDate}T23:59:59.999`) : null;

  const isInvalidDateRange =
    startDate && endDate && startDate > endDate;

  const filteredAlerts = useMemo(() => {
    if (isInvalidDateRange) return [];
    const result = alerts.filter((alert) => {
      const matchesId = !filterId || alert.id.includes(filterId);
      const matchesSeverity =
        filterSeverity === "All" ||
        (alert.severity &&
          alert.severity.toLowerCase() === filterSeverity.toLowerCase());
      const alertDate = new Date(alert.start_time);
      const matchesStart = !startDate || alertDate >= startDate;
      const matchesEnd = !endDate || alertDate <= endDate;

      return matchesId && matchesSeverity && matchesStart && matchesEnd;
    });
    return result.sort(
      (a, b) => new Date(b.start_time) - new Date(a.start_time)
    );
  }, [alerts, filterId, filterSeverity, filterStartDate, filterEndDate, isInvalidDateRange]);

  const pagedAlerts = useMemo(() => {
    const start = (currentPage - 1) * alertsPerPage;
    return filteredAlerts.slice(start, start + alertsPerPage);
  }, [filteredAlerts, currentPage, alertsPerPage]);

  const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / alertsPerPage));
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [totalPages]);

  const goToPage = (page) => {
    const p = Math.max(1, Math.min(totalPages, page));
    setCurrentPage(p);
    const start = (p - 1) * alertsPerPage;
    const end = start + alertsPerPage;
    const visibleIds = (alerts || []).slice(start, end).map(a => a.id);
    if (!visibleIds.includes(expandedAlertId)) {
      setExpandedAlertId(null);
    }
  };
  const formatDateTime = (isoString) => {
    const date = new Date(isoString);
    const dd = String(date.getDate()).padStart(2, '0');
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const yyyy = date.getFullYear();
    let hh = date.getHours();
    const min = String(date.getMinutes()).padStart(2, '0');
    const ss = String(date.getSeconds()).padStart(2, '0');
    const ampm = hh >= 12 ? 'PM' : 'AM';
    hh = hh % 12 || 12;
    return `${dd}-${mm}-${yyyy} ${String(hh).padStart(2, '0')}:${min}:${ss} ${ampm}`;
  };
  return (
    <div className="alertuser-list">
      <div className="alert-filter-grid">
        <input
          type="text"
          placeholder="Search by Alert ID"
          value={filterId}
          onChange={(e) => setFilterId(e.target.value)}
          className="form-control form-control-sm"
        />

        <input
          type="date"
          value={filterStartDate}
          onChange={(e) => setFilterStartDate(e.target.value)}
          className="form-control form-control-sm"
        />

        <input
          type="date"
          value={filterEndDate}
          onChange={(e) => setFilterEndDate(e.target.value)}
          className="form-control form-control-sm"
        />

        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="form-select"
        >
          <option value="All">All Severities</option>
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
        </select>

        <div className="reset-button-wrapper">
          <button
            className="btn btn-sm btn-outline-danger"
            onClick={() => {
              setFilterId("");
              setFilterStartDate("");
              setFilterEndDate("");
              setFilterSeverity("All");
            }}
          >
            Reset Filters
          </button>
        </div>
      </div>
      <hr className="mb-3" style={{ borderColor: "#444" }} />
      {isInvalidDateRange && (
        <div className="text-danger mb-3">Invalid date range selected</div>
      )}
      {!isInvalidDateRange && filteredAlerts.length === 0 && (
        <div className="no-records-message">No records found</div>
      )}
      {!isInvalidDateRange && filteredAlerts.length > 0 && (
        <table className="alertuser-table">
          <thead>
            <tr>
              <th>Alert ID</th>
              <th>Timestamp</th>
              <th>Severity</th>
              <th>Description</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pagedAlerts.map(alert => {
              return (
                <React.Fragment key={alert.id}>
                  <tr>
                    <td>
                      {alert?.id ? (
                        <a
                          className="link-button"
                          href={`/alert-details?alertId=${encodeURIComponent(alert.id)}&type=${alert.type || "camera"}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={() => {
                            try {
                              localStorage.setItem("selectedAlert", JSON.stringify(alert));
                            } catch (e) {
                              console.warn("Failed to store selectedAlert", e);
                            }
                          }}
                        >
                          {alert.id}
                        </a>
                      ) : (
                        <span>Unknown ID</span>
                      )}
                    </td>
                          <td>{alert?.start_time ? formatDateTime(alert.start_time) : "N/A"}</td>
                    <td>{alert?.severity || "N/A"}</td>
                    <td>{alert?.message || "No description"}</td>
                    <td>{alert?.alert_analysis || "N/A"}</td>
                    <td>
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ whiteSpace: 'nowrap' }}
                        onClick={() =>
                          setExpandedAlertId(expandedAlertId === alert?.id ? null : alert?.id)
                        }
                      >
                        {expandedAlertId === alert?.id ? "Hide Devices" : "View Devices"}
                      </button>
                    </td>
                  </tr>

                  {expandedAlertId === alert?.id && (
                    <tr className="device-row">
                      <td colSpan="6">
                        <table className="device-table">
                          <thead>
                            <tr>
                              <th>Device Name</th>
                              <th>Type</th>
                              <th>Timestamp</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {alert?.drone ? (
                             console.debug('Rendering devices for drone alert:', alert.drone),
                              (alert?.devices || []).map((device, index) => (
                                <tr key={index}>
                                  <td>{device?.device_name}</td>
                                  <td>{device?.primary_device }</td>
                                  <td>
                                    {device?.recording_start
                                      ? new Date(device.recording_start).toLocaleString()
                                      : "N/A"}
                                  </td>
                                  <td>{device?.status}</td>
                                </tr>
                              ))
                            ) : (
                              (alert?.devices || []).map((device, index) => (
                                <tr key={index}>
                                  <td>{device?.camera_name || "Unknown"}</td>
                                  <td>{device?.camera?.camera_type || "N/A"}</td>
                                  <td>
                                    {device?.recorded_at
                                      ? new Date(device.recorded_at).toLocaleTimeString()
                                      : "N/A"}
                                  </td>
                                  <td>{device?.status || "N/A"}</td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>)}
      {renderPagination ? (
        renderPagination()
      ) : (
        <div
          className="pagination"
          style={{
            marginTop: 12,
            display: alerts.length ? 'flex' : 'none',
            alignItems: 'center',
            gap: '0.75rem',
            flexWrap: 'wrap',
          }}
        >
          <label htmlFor="page-size-select">Rows per page:</label>
          <select
            id="page-size-select"
            value={alertsPerPage}
            onChange={(e) => {
              setAlertsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="page-dropdown"
          >
            {[10, 20, 30, 40].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>

          <span style={{ fontSize: '0.9rem' }}>
            {`${(currentPage - 1) * alertsPerPage + 1}–${Math.min(currentPage * alertsPerPage, filteredAlerts.length)} of ${filteredAlerts.length}`}
          </span>

          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            className="pagination-arrow"
          >
            ◄
          </button>
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="pagination-arrow"
          >
            ►
          </button>
        </div>
      )}
    </div>
  );
}

export default AllAlertsView;