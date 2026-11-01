import React, { useRef, useEffect, useState } from "react";

const MJPEGCanvasPlayer = ({ feedUrl, timestamp }) => {
  const canvasRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(true);

  const togglePlay = () => setIsPlaying(prev => !prev);
  useEffect(() => {
    let interval;
    if (isPlaying) {
      interval = setInterval(() => {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.src = `${feedUrl}?t=${Date.now()}`;
        img.onload = () => {
          if (canvasRef.current) {
            const ctx = canvasRef.current.getContext("2d");
            ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
            ctx.drawImage(img, 0, 0, canvasRef.current.width, canvasRef.current.height);
          }
        };
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isPlaying, feedUrl]);
  return (
    <div className="canvas-container">
      <canvas
        ref={canvasRef}
        width={640}
        height={480}
        className="canvas-display"
      />
      <div className="canvas-footer">
        <button onClick={togglePlay} className="play-toggle">
          {isPlaying ? "⏸" : "▶️"}
        </button>

        <span className="timestamp-label">
          🕒 {timestamp}
        </span>

        <button disabled className="loop-button">
          🔁 Loop
        </button>
      </div>
    </div>
  );
};
export default MJPEGCanvasPlayer;