import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy - French Novel Tool',
  description: 'Privacy Policy for French Novel Tool',
  robots: { index: true, follow: true },
};

export default function PolicyPage() {
  return (
    <section style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ marginBottom: '1rem' }}>Security, Privacy & Terms of Use</h1>
      <p><em>Last updated: {new Date().toISOString().slice(0, 10)}</em></p>

      <h2>Security Policy</h2>
      <p><strong>Reporting a Vulnerability:</strong> If you discover a security issue, please email <a href="mailto:haytham.mkt@gmail.com">haytham.mkt@gmail.com</a> or open a private GitHub security advisory. We will respond as quickly as possible.</p>
      <p><strong>Data Handling:</strong> All uploaded PDFs are processed in-memory or stored temporarily for processing only. PDFs are not retained after processing is complete, except for minimal metadata (filename, processing status, and user association) in the database for history/audit purposes. Processed text and results are only stored as long as needed to complete the export to Google Sheets. No PDF content is shared with third parties except Google Gemini AI (for normalization) and Google Sheets (for export), using secure, authenticated API calls. User OAuth tokens are encrypted at rest and never shared.</p>
      <p><strong>Deletion Policy:</strong> PDFs and their extracted text are deleted from server storage immediately after processing/export. Users can delete their processing history at any time, which removes all associated metadata.</p>
      <p><strong>Infrastructure:</strong> All API endpoints are protected by JWT authentication and rate limiting. HTTPS is required in production deployments. Regular dependency updates and security reviews are performed.</p>

      <h2>Privacy Policy</h2>
      <p><strong>What Data Do We Collect?</strong> Your uploaded PDFs are used only for extracting and normalizing sentences. The files are not permanently stored. We store minimal metadata (filename, processing time, user ID) for your history and audit purposes. If you sign in, we store your email and Google OAuth tokens (encrypted) to enable export to your Google Sheets.</p>
      <p><strong>How Is Your Data Used?</strong> PDFs are processed in-memory or temporarily stored for extraction and normalization. Processed text is sent to Google Gemini AI for sentence normalization. Results are exported to your Google Sheets using your OAuth credentials. No PDF content or results are shared with third parties except Google Gemini and Google Sheets APIs.</p>
      <p><strong>Data Retention & Deletion:</strong> PDFs and extracted text are deleted immediately after processing/export. You can delete your processing history at any time from the app, which removes all associated metadata. OAuth tokens are deleted if you disconnect your account.</p>
      <p><strong>Security:</strong> All data is encrypted in transit (HTTPS) and at rest (where applicable). Access to your data is protected by authentication and rate limiting.</p>

      <h2>Terms of Use</h2>
      <p>You must have the rights to upload and process any PDF you submit. Do not upload illegal, copyrighted, or sensitive materials. The service is provided as-is, with no guarantee of availability or data recovery. Abuse or violation of these terms may result in account suspension.</p>

      <h2>Contact</h2>
      <p>For questions or data requests, contact: <a href="mailto:haytham.mkt@gmail.com">haytham.mkt@gmail.com</a></p>
    </section>
  );
}
