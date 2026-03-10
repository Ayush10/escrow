export default function OpinionModal({ isOpen, onClose, htmlContent }) {
  if (!isOpen) return null;

  return (
    <div
      className={`modal-overlay ${isOpen ? "open" : ""}`}
      id="verdictModal"
      onClick={(e) => {
        if (e.target.classList.contains("modal-overlay")) {
          onClose();
        }
      }}
    >
      <div className="modal-content glass">
        <button className="modal-close" onClick={onClose}>
          ✕
        </button>
        <div
          className="opinion-parsed"
          id="modalBody"
          dangerouslySetInnerHTML={{ __html: htmlContent }}
        ></div>
      </div>
    </div>
  );
}
