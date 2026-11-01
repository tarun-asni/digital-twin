import React, { useState } from "react";
import CameraFeed from "./CameraFeed";
import { useNavigate } from 'react-router-dom';

function CameraGridPage({ streams, showLeftMenu }) {
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(0);

  const getLayoutConfig = () => {
    const total = streams.length;
    if (total === 1) return { perPage: 1, columns: 1, rows: 1 };
    if (total === 2) return { perPage: 2, columns: 2, rows: 1 };
    if (total <= 4) return { perPage: total, columns: 2, rows: 2 };
    if (total <= 6) return { perPage: 6, columns: 3, rows: 2 };
    if (total <= 9) return { perPage: 9, columns: 3, rows: 3 };
    return { perPage: 9, columns: 3, rows: 3 };
  };

  const { perPage, columns, rows } = getLayoutConfig();
  const totalPages = Math.ceil(streams.length / perPage);
  const paginatedStreams = streams.slice(currentPage * perPage, (currentPage + 1) * perPage);

  const handleClick = (id, url, name) => {
    navigate(`/camera/${id}`, {
      state: { url, name }
    });
  };

  const getContainerStyle = () => {
    const count = paginatedStreams.length;

    if (count === 1) {
      return {
        width: "100%",
        height: "100%",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#fff",
        overflow: "hidden",
        boxSizing: "border-box"
      };
    }

    if (count === 2) {
      return {
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gridTemplateRows: "1fr",
        gap: "16px",
        padding: "50px 20px 8px 20px",
        maxWidth: "960px",
        margin: "0 auto",
        height: "100%",
        boxSizing: "border-box",
        backgroundColor: "#fff",
        overflow: "hidden"
      };
    }

    return {
      width: "100%",
      height: "100%",
      display: "grid",
      gridTemplateColumns: `repeat(${columns}, 1fr)`,
      gridTemplateRows: `repeat(${rows}, 1fr)`,
      gap: "8px",
      padding: "50px 20px 8px 20px",
      boxSizing: "border-box",
      overflow: "auto",
      backgroundColor: "#fff"
    };
  };

  const getItemStyle = () => {
    const length = paginatedStreams.length;

    let width = "100%";
    let height = "100%";

    if (length === 1) {
      width = "680px";
      height = "480px";
    } else if (length === 2) {
      width = "100%";
      height = "480px";
    }

    return {
      width,
      height,
      backgroundColor: "#fff",
      overflow: "hidden",
      cursor: length > 1 ? "pointer" : "default",
      borderRadius: "6px"
    };
  };

  return (
    <>
      <div style={getContainerStyle()}>
        {paginatedStreams.map(({ id, url, name }) => (
          <div
            key={id}
            style={getItemStyle()}
            onClick={() => handleClick(id, url, name)}
          >
            <CameraFeed id={id} url={url} name={name} />
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div style={{ textAlign: "center", marginTop: "8px", color: "#fff" }}>
          <button
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 0))}
            disabled={currentPage === 0}
          >
            Prev
          </button>
          <span style={{ margin: "0 12px" }}>
            Page {currentPage + 1} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages - 1))}
            disabled={currentPage === totalPages - 1}
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}

export default CameraGridPage;