import React, { useEffect, useState } from "react";
import AlertDetailPage from "./AlertDetailPage";
import { useSearchParams } from 'react-router-dom';
import { fetchAlertDetails,fetchSensorAlertDetails } from '../utils/appClient';

function AlertDetailWrapper() {
  const [searchParams] = useSearchParams();
  const alertId = searchParams.get('alertId');
  const alertType = searchParams.get('type');
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (alertId) {
        try {
           const data =
            alertType === "sensor"
              ? await fetchSensorAlertDetails(alertId)
              : await fetchAlertDetails(alertId);
          if (mounted) setAlert(data);
        } catch (e) {
          console.error('Failed to fetch alert details in wrapper:', e);
        }
        }

      if (mounted) setLoading(false);
    }

      load();

    return () => { mounted = false; };
  }, [alertId]);

  if (loading) return <div style={{ padding: 24 }}>Loading alert...</div>;

  return <AlertDetailPage alert={alert} onClose={() => window.close()} />;
}

export default AlertDetailWrapper;