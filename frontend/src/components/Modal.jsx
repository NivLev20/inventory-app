// Native <dialog>: opens on mount; Esc triggers onClose.
import { useEffect, useRef } from "react";

export default function Modal({ title, onClose, children }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);

  return (
    <dialog ref={ref} onCancel={onClose}>
      <h2>{title}</h2>
      {children}
    </dialog>
  );
}
