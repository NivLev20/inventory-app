// Small message at the bottom of the screen ("Product added", errors...).
export default function Toast({ message }) {
  return (
    <div className={message ? "toast show" : "toast"} role="status">
      {message}
    </div>
  );
}
