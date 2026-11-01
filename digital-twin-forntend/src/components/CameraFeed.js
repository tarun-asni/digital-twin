import React, { useState, useEffect } from "react";
import cameraoffIcon from '../images/cameraoff.png';

function CameraFeed({ url, name }) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
  }, [url]);

  return (
    <div className="video-container">
      {isLoading && !hasError && (
        <div className="loader-spinner"></div>
      )}

      {!hasError && (
        <img
          src={url}
          className="video-frame"
          alt={name}
          style={{ display: isLoading ? "none" : "block" }}
          onLoad={() => setIsLoading(false)}
          onError={() => {
            setIsLoading(false);
            setHasError(true);
          }}
        />
      )}

      {hasError && (
        <div className="error-message text-center">
          <img
            src={cameraoffIcon}
            alt="Video Off Icon"
            className="error-icon"
          />
          <div className="mt-2 text-danger">Failed to stream {name}</div>
        </div>
      )}

    </div>
  );
}

export default CameraFeed;