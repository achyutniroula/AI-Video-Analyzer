const font = "'Manrope', sans-serif";

export default function Footer() {
  return (
    <footer style={{
      padding: '1.5rem 3rem',
      borderTop: '1px solid var(--outline-faint)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '0.5rem',
      marginTop: 'auto',
    }}>
      <p style={{
        color: 'var(--on-muted)',
        fontSize: '0.72rem',
        fontWeight: 300,
        letterSpacing: '0.12em',
        fontFamily: font,
      }}>
        Developed by Achyut and Shoaib
      </p>
      <p style={{
        color: 'var(--outline)',
        fontSize: '0.68rem',
        fontWeight: 300,
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        fontFamily: font,
      }}>
        COSC 4896
      </p>
    </footer>
  );
}
